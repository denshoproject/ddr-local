import json
import logging
logger = logging.getLogger(__name__)
import os
import re
import sys

from bs4 import BeautifulSoup
from elasticsearch.exceptions import ConnectionError

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.template.context_processors import csrf
from django.core.files import File
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, render

from DDR import commands
from DDR import converters
from DDR import fileio
from DDR import idservice
from DDR import vocab

from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui import docstore
from webui.decorators import ddrview
from webui.forms import DDRForm
from webui.forms import ObjectIDForm
from webui.forms.entities import JSONForm, UpdateForm, DeleteEntityForm, RmDuplicatesForm
from webui.gitstatus import repository, annex_info
from webui.identifier import Identifier
from webui.models import Stub, Collection, Entity
from webui.tasks import entity as entity_tasks
from webui.tasks import dvcs as dvcs_tasks
from webui.views.decorators import login_required



# helpers --------------------------------------------------------------

def vocab_terms( fieldname ):
    """Loads and caches list of topics from vocab API.
    
    TODO This should probably be somewhere else
    
    Works with JSON file generated by DDR.vocab.Index.dump_terms_json().
    """
    return vocab.get_vocabs(settings.VOCABS_URL)[fieldname]

def tagmanager_terms( fieldname ):
    key = 'vocab:%s:tagmanager' % fieldname
    timeout = 60*60*1  # 1 hour
    data = cache.get(key)
    if not data:
        data = []
        vocab = vocab_terms(fieldname)
        for term in vocab['terms']:
            if term.get('path', None):
                text = '%s [%s]' % (term['path'], term['id'])
            else:
                text = '%s [%s]' % (term['title'], term['id'])
            data.append(text)
        #cache.set(key, data, timeout)
    return data
    
def tagmanager_prefilled_terms( entity_terms, all_terms ):
    """Preps list of entity's selected terms for TagManager widget.
    
    TODO This should probably be somewhere else
    
    Topics used in DDR thus far may have different text than new topics,
    though they should have same IDs.
    This function takes 
    
    >>> entity.topics = ['a topic [10]']
    >>> terms = ['A Topic [10]', 'Life The Universe and Everything [42]', ...]
    >>> entity.prefilled_topics(terms)
    ['A Topic [10]']
    
    @param all_terms: list of topics terms
    @param entity_terms: list of terms
    @returns: list of terms for the term IDs
    """
    regex = re.compile('([\d]+)')
    entity_term_ids = []
    for term in entity_terms:
        match = regex.search(term)
        if match:
            for tid in match.groups():
                entity_term_ids.append(tid)
    selected_terms = []
    for term in all_terms:
        match = regex.search(term)
        if match:
            for tid in match.groups():
                if tid in entity_term_ids:
                    selected_terms.append(str(term))
    return selected_terms

def tagmanager_legacy_terms( entity_terms, all_terms ):
    """Returns list of entity terms that do not appear in all_terms.
    
    TODO is "legacy" the right word to use for these?
    
    @param all_terms: list of topics terms
    @param entity_terms: list of terms
    @returns: list of terms
    """
    regex = re.compile('([\d]+)')
    legacy_terms = []
    for term in entity_terms:
        match = regex.search(term)
        if not match:
            legacy_terms.append(str(term))
    return legacy_terms

#def tagmanager_prefilled_terms( entity_terms, all_terms ):
#    """Preps list of selected entity.topics for TagManager widget.
#    
#    TODO This should probably be somewhere else
#    
#    Terms containing IDs will be replaced with canonical term descriptions
#    from the official project controlled vocabulary service.
#    This is because terms used in DDR thus far may have different text
#    than new terms, though they should have same IDs.
#    IMPORTANT: Terms with no ID should be displayed as-is.
#    
#    >>> entity.topics = ['a topic [10]', 'freetext term']
#    >>> terms = ['A Topic [10]', 'freetext term']
#    >>> entity.tagmanager_prefilled_terms(terms)
#    ['A Topic [10]', 'freetext term']
#    
#    @param all_terms: list of terms for FIELD
#    @param entity_terms: list of terms from entity
#    @returns: list of terms for the term IDs
#    """
#    regex = re.compile('([\d]+)')
#    # separate into ID'd and freetext lists.
#    # Add indexs to all_terms as placeholders.
#    terms = []
#    entity_term_ids = {}
#    freetext_terms = {}
#    for n,term in enumerate(entity_terms):
#        terms.append(n)
#        match = regex.search(term)
#        if match:
#            for tid in match.groups():
#                entity_term_ids[n] = tid
#        else:
#            freetext_terms[n] = term
#    # replace placeholders for ID'd terms with canonical term descriptions from all_terms
#    for n,tid in entity_term_ids.iteritems():
#        for term in all_terms:
#            if tid in term:
#                terms[n] = term
#    # replace placeholders for freetext terms
#    for n,term in freetext_terms.iteritems():
#        terms[n] = term
#    # convert unicode terms to str
#    return [str(term) for term in terms]

def tagmanager_process_tags( form_terms ):
    """Formats TagManager tags in format expected by Entity.topics.
    
    TagManager separates tags by commas, by DDR expects semicolons
    TODO This should probably be somewhere else
    
    >>> hidden_terms = u'Topic 1 [94],Topic 2: Subtopic 2 [95]'
    >>> process_cleaned_terms(hidden_terms, all_terms)
    u'Topic 1 [94]; Topic 2: Subtopic 2 [95]'
    """
    form_terms = form_terms.replace('],', '];')
    cleaned = form_terms.split(';')
    return '; '.join(cleaned)

def enforce_git_credentials(request):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    return git_name,git_mail

def check_object(entity, check_locks=True):
    if not entity:
        raise Http404
    if check_locks and entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect(entity.absolute_url())

def check_parent(collection, check_locks=True, fetch=True):
    if not collection:
        raise Exception('No parent collection!')
    if check_locks and collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect(collection.absolute_url())
    if fetch:
        collection.repo_fetch()
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect(collection.absolute_url())


# views ----------------------------------------------------------------

@storage_required
def detail( request, eid ):
    entity = Entity.from_identifier(Identifier(eid))
    check_object(entity, check_locks=False)
    collection = entity.collection()
    entity.model_def_commits()
    entity.model_def_fields()
    tasks = request.session.get('celery-tasks', [])
    return render(request, 'webui/entities/detail.html', {
        'collection': collection,
        'entity': entity,
        'children_urls': entity.children_urls(),
        'tasks': tasks,
        'entity_unlock_url': entity.unlock_url(entity.locked()),
        # cache this for later
        'annex_info': annex_info(repository(collection.path_abs)),
    })

@storage_required
def children(request, eid):
    entity = Entity.from_identifier(Identifier(eid))
    check_object(entity, check_locks=False)
    collection = entity.collection()
    
    # models that are under entity but are not nodes (i.e. files)
    from DDR.identifier import CHILDREN, NODES, MODELS_IDPARTS
    children_models = [
        m for m in CHILDREN['entity'] if m not in NODES
    ]
    
    # paginate
    children_meta = sorted(
        entity.children_meta,
        key=lambda entity: (
            int(entity.get('sort',1000000)),
            entity['id']
        )
    )
    children = [
        Entity.from_identifier(Identifier(item['id']))
        for item in children_meta
    ]
    thispage = request.GET.get('page', 1)
    paginator = Paginator(
        children,
        settings.RESULTS_PER_PAGE
    )
    page = paginator.page(thispage)
    return render(request, 'webui/entities/children.html', {
        'collection': collection,
        'entity': entity,
        'children_models': children_models,
        'children_urls': entity.children_urls(active='children'),
        'paginator': paginator,
        'page': page,
        'thispage': thispage,
    })

@storage_required
def file_role( request, rid ):
    file_role = Stub.from_identifier(Identifier(rid))
    role = file_role.identifier.parts['role']
    entity = file_role.parent(stubs=True)
    check_object(entity, check_locks=False)
    collection = entity.collection()
    duplicates = entity.detect_file_duplicates(role)
    if duplicates:
        url = reverse('webui-entity-files-dedupe', args=[entity.id])
        messages.error(request, 'Duplicate files detected. <a href="%s">More info</a>' % url)
    files = entity.children(role)
    # paginate
    thispage = request.GET.get('page', 1)
    paginator = Paginator(files, settings.RESULTS_PER_PAGE)
    page = paginator.page(thispage)
    return render(request, 'webui/entities/files.html', {
        'collection': collection,
        'entity': entity,
        'children_urls': entity.children_urls(active=role),
        'browse_url': entity.file_browse_url(role),
        'external_url': entity.file_external_url(role),
        'batch_url': entity.file_browse_url(role),
        'paginator': paginator,
        'page': page,
        'thispage': thispage,
    })

@storage_required
def addfile_log( request, eid ):
    entity = Entity.from_identifier(Identifier(eid))
    check_object(entity, check_locks=False)
    collection = entity.collection()
    return render(request, 'webui/entities/addfiles-log.html', {
        'collection': collection,
        'entity': entity,
    })

@storage_required
def changelog( request, eid ):
    entity = Entity.from_identifier(Identifier(eid))
    check_object(entity, check_locks=False)
    collection = entity.collection()
    return render(request, 'webui/entities/changelog.html', {
        'collection': collection,
        'entity': entity,
    })

@ddrview
@login_required
@storage_required
def new( request, oid ):
    """Redirect to new_idservice or new_manual.
    """
    model = request.GET.get('model', 'entity')
    if settings.IDSERVICE_API_BASE:
        # include model in URL
        url = '%s?model=%s' % (
            reverse('webui-entity-newidservice', args=[oid]),
            model
        )
        return HttpResponseRedirect(url)
    # pass ID template in request.GET
    url = reverse('webui-entity-newmanual', args=[oid]) + '?model=%s' % model
    return HttpResponseRedirect(url)

def _create_entity(request, eidentifier, collection, git_name, git_mail):
    """used by both new_idservice and new_manual
    """
    # load Entity object, inherit values from parent, write back to file
    exit,status = Entity.new(eidentifier, git_name, git_mail, agent=settings.AGENT)
    entity = Entity.from_identifier(eidentifier)
    
    collection.cache_delete()
    if exit:
        logger.error(exit)
        logger.error(status)
        messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
    else:
        # update search index
        try:
            entity.post_json()
        except ConnectionError:
            logger.error('Could not post to Elasticsearch.')
        dvcs_tasks.gitstatus_update.apply_async(
            (collection.path,),
            countdown=2
        )
    return entity

@ddrview
@login_required
@storage_required
def new_idservice( request, oid ):
    """Gets new EID from idservice, creates new entity record.
    
    If it messes up, goes back to collection.
    """
    git_name,git_mail = enforce_git_credentials(request)
    # note: oid could be either a Collection or an Entity
    collection = Collection.from_identifier(
        Identifier(oid).collection()
    )
    check_parent(collection)
    
    ic = idservice.IDServiceClient()
    # resume session
    auth_status,auth_reason = ic.resume(request.session['idservice_token'])
    if auth_status != 200:
        request.session['idservice_username'] = None
        request.session['idservice_token'] = None
        messages.warning(
            request,
            'Session resume failed: %s %s (%s)' % (
                auth_status,auth_reason,settings.IDSERVICE_API_BASE
            )
        )
        return HttpResponseRedirect(collection.absolute_url())
    
    # get new entity ID
    new_object_parent = Identifier(oid)
    model = request.GET.get('model', 'entity')
    ENTITY_MODELS = ['entity', 'segment']
    if model not in ENTITY_MODELS:
        raise Exception('Model "%s% not an entity model.' % model)
    http_status,http_reason,new_entity_id = ic.next_object_id(
        new_object_parent,
        model,
        register=True,
    )
    
    # abort!
    if http_status not in [200,201]:
        err = '%s %s' % (http_status, http_reason)
        msg = WEBUI_MESSAGES['VIEWS_ENT_ERR_NO_IDS'] % (settings.IDSERVICE_API_BASE, err)
        logger.error(msg)
        messages.error(request, msg)
        return HttpResponseRedirect(collection.absolute_url())
    
    # Create entity and redirect to edit page
    eidentifier = Identifier(id=new_entity_id)
    entity = _create_entity(request, eidentifier, collection, git_name, git_mail)
    if entity:
        return HttpResponseRedirect(reverse('webui-entity-edit', args=[entity.id]))
    
    # something happened...
    logger.error('Could not create new entity!')
    messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_ERR_CREATE'])
    return HttpResponseRedirect(collection.absolute_url())

@ddrview
@login_required
@storage_required
def new_manual( request, oid ):
    """Ask for Entity ID, then create new Entity.
    """
    git_name,git_mail = enforce_git_credentials(request)
    # note: oid could be either a Collection or an Entity
    parent = Identifier(oid).object()
    collection = Collection.from_identifier(
        Identifier(oid).collection()
    )
    check_parent(collection)

    oidentifier = Identifier(oid)
    model = request.GET.get('model', 'entity')
    
    if request.method == 'POST':
        form = ObjectIDForm(request.POST)
        if form.is_valid():

            eid = form.cleaned_data['object_id']
            eidentifier = Identifier(id=eid)
            # Create entity and redirect to edit page
            entity = _create_entity(
                request,
                eidentifier, collection,
                git_name, git_mail
            )
            if entity:
                messages.warning(request, 'IMPORTANT: Register this ID with the ID service as soon as possible!')
                return HttpResponseRedirect(
                    reverse('webui-entity-edit', args=[entity.id])
                )
            
    else:
        form = ObjectIDForm(initial={
            'model': model,
            'parent_id': oidentifier.id,
        })

    if isinstance(parent, Collection):
        existing_ids = sorted([entity.id for entity in parent.children(quick=True)])
    elif isinstance(parent, Entity):
        existing_ids = sorted([e['id'] for e in parent.children_meta])
    existing_ids.reverse()
    
    return render(request, 'webui/entities/new-manual.html', {
        'collection': collection,
        'parent': parent,
        'model': model,
        'form': form,
        'existing_ids': existing_ids,
    })
    
@ddrview
@login_required
@storage_required
def edit( request, eid ):
    """
    UI for Entity topics uses TagManager to represent topics as tags,
    and typeahead.js so users only have to type part of a topic.
    """
    git_name,git_mail = enforce_git_credentials(request)
    entity = Entity.from_identifier(Identifier(eid))
    check_object(entity)
    module = entity.identifier.fields_module()
    collection = entity.collection()
    check_parent(collection)
    
    # load topics choices data
    # TODO This should be baked into models somehow.
    topics_terms = tagmanager_terms('topics')
    facility_terms = tagmanager_terms('facility')
    entity.model_def_commits()
    entity.model_def_fields()
    if request.method == 'POST':
        form = DDRForm(request.POST, fields=module.FIELDS)
        if form.is_valid():
            
            # clean up after TagManager
            hidden_topics = request.POST.get('hidden-topics', None)
            hidden_facility = request.POST.get('hidden-facility', None)
            if hidden_topics:
                form.cleaned_data['topics'] = tagmanager_process_tags(hidden_topics)
            if hidden_facility:
                form.cleaned_data['facility'] = tagmanager_process_tags(hidden_facility)

            entity.form_post(form.cleaned_data)
            # write these so we see a change on refresh
            # will be rewritten in entity.save()
            entity.write_json()
            
            # do the rest in the background:
            # update inheriable fields, commit files, delete cache,
            # update search index, update git status
            entity_tasks.edit(
                request,
                collection, entity, form.cleaned_data,
                git_name, git_mail, settings.AGENT
            )
            
            return HttpResponseRedirect(entity.absolute_url())
    else:
        form = DDRForm(entity.form_prep(), fields=module.FIELDS)

    # coerce term:id dicts into old-style "term [id]" strings
    entity_topics = [
        converters.dict_to_textbracketid(item, ['term','id'])
        for item in entity.topics
    ]
    entity_facility = [
        converters.dict_to_textbracketid(item, ['term','id'])
        for item in entity.facility
    ]

    topics_prefilled = tagmanager_prefilled_terms(entity_topics, topics_terms)
    facility_prefilled = tagmanager_prefilled_terms(entity_facility, facility_terms)
    # selected terms that don't appear in field_terms
    topics_legacy = tagmanager_legacy_terms(entity_topics, topics_terms)
    facility_legacy = tagmanager_legacy_terms(entity_facility, facility_terms)
    return render(request, 'webui/entities/edit-json.html', {
        'collection': collection,
        'entity': entity,
        'form': form,
        # data for TagManager
        'topics_terms': topics_terms,
        'facility_terms': facility_terms,
        'topics_prefilled': topics_prefilled,
        'facility_prefilled': facility_prefilled,
    })


def edit_vocab_terms( request, field ):
    terms = []
    for term in vocab_terms(field)['terms']:
        if term.get('path',None):
            t = '%s [%s]' % (term['path'], term['id'])
        else:
            t = '%s [%s]' % (term['title'], term['id'])
        terms.append(t)
    return render(request, 'webui/entities/vocab.html', {
        'terms': terms,
    })

@ddrview
@login_required
@storage_required
def delete( request, eid, confirm=False ):
    """Delete the requested entity from the collection.
    """
    git_name,git_mail = enforce_git_credentials(request)
    entity = Entity.from_identifier(Identifier(eid))
    check_object(entity)
    collection = entity.collection()
    check_parent(collection)
    
    if request.method == 'POST':
        form = DeleteEntityForm(request.POST)
        if form.is_valid() and form.cleaned_data['confirmed']:
            entity_tasks.delete(
                request,
                git_name, git_mail,
                collection, entity,
                settings.AGENT
            )
            return HttpResponseRedirect(collection.absolute_url())
    else:
        form = DeleteEntityForm()
    return render(request, 'webui/entities/delete.html', {
        'entity': entity,
        'form': form,
    })

@login_required
@storage_required
def files_reload( request, eid ):
    """Regenerates list of file info dicts with list of File objects
    """
    git_name,git_mail = enforce_git_credentials(request)
    entity = Entity.from_identifier(Identifier(eid))
    check_object(entity)
    collection = entity.collection()
    check_parent(collection)
    
    entity_tasks.reload_files(
        request,
        collection, entity,
        git_name, git_mail, settings.AGENT
    )
    
    messages.success(
        request,
        'Regenerating files list for <a href="%s">%s</a>.' % (
            entity.absolute_url(), entity.id
        )
    )
    return HttpResponseRedirect(entity.absolute_url())

@login_required
@storage_required
def files_dedupe( request, eid ):
    git_name,git_mail = enforce_git_credentials(request)
    entity = Entity.from_identifier(Identifier(eid))
    check_object(entity)
    collection = entity.collection()
    check_parent(collection)
    
    duplicate_masters = entity.detect_file_duplicates('master')
    duplicate_mezzanines = entity.detect_file_duplicates('mezzanine')
    duplicates = duplicate_masters + duplicate_mezzanines
    
    if request.method == 'POST':
        form = RmDuplicatesForm(request.POST)
        if form.is_valid() and form.cleaned_data.get('confirmed',None) \
                and (form.cleaned_data['confirmed'] == True):
            # remove duplicates
            entity.rm_file_duplicates()
            # update metadata files
            entity.write_json()
            entity.write_mets()
            updated_files = [entity.json_path, entity.mets_path,]
            success_msg = WEBUI_MESSAGES['VIEWS_ENT_UPDATED']
            exit,status = commands.entity_update(
                git_name, git_mail,
                collection, entity,
                updated_files,
                agent=settings.AGENT
            )
            collection.cache_delete()
            if exit:
                messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
            else:
                # update search index
                try:
                    entity.post_json()
                except ConnectionError:
                    logger.error('Could not post to Elasticsearch.')
                dvcs_tasks.gitstatus_update.apply_async(
                    (collection.path,),
                    countdown=2
                )
                # positive feedback
                messages.success(request, success_msg)
                return HttpResponseRedirect(entity.absolute_url())
    else:
        data = {}
        form = RmDuplicatesForm()
    return render(request, 'webui/entities/files-dedupe.html', {
        'collection': collection,
        'entity': entity,
        'duplicates': duplicates,
        'form': form,
    })

@ddrview
@login_required
@storage_required
def unlock( request, eid, task_id ):
    """Provides a way to remove entity lockfile through the web UI.
    """
    git_name,git_mail = enforce_git_credentials(request)
    entity = Entity.from_identifier(Identifier(eid))
    check_object(entity)
    collection = entity.collection()
    
    if task_id and entity.locked() and (task_id == entity.locked()):
        entity.unlock(task_id)
        messages.success(request, 'Object <b>%s</b> unlocked.' % entity.id)
    return HttpResponseRedirect(entity.absolute_url())
