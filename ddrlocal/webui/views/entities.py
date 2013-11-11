import json
import logging
logger = logging.getLogger(__name__)
import os

from bs4 import BeautifulSoup
import requests

from django.conf import settings
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.files import File
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from DDR import commands

from ddrlocal.models.entity import ENTITY_FIELDS

from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui import api
from webui.decorators import ddrview
from webui.forms import DDRForm
from webui.forms.entities import NewEntityForm, JSONForm, UpdateForm
from webui.mets import NAMESPACES, NAMESPACES_XPATH
from webui.mets import METS_FIELDS, MetsForm
from webui.models import Collection, Entity
from webui.views.decorators import login_required
from xmlforms.models import XMLModel



# views ----------------------------------------------------------------

@storage_required
def detail( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    epath = Entity.entity_path(request,repo,org,cid,eid)
    entity = Entity.from_json(epath)
    tasks = request.session.get('celery-tasks', [])
    return render_to_response(
        'webui/entities/detail.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,
         'tasks': tasks,
         'unlock_task_id': entity.locked(),},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def addfile_log( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    return render_to_response(
        'webui/entities/addfiles-log.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def changelog( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    return render_to_response(
        'webui/entities/changelog.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def entity_json( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    with open(entity.json_path, 'r') as f:
        json = f.read()
    return HttpResponse(json, mimetype="application/json")

@storage_required
def mets_xml( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    soup = BeautifulSoup(entity.mets().xml, 'xml')
    return HttpResponse(soup.prettify(), mimetype="application/xml")

@storage_required
def files( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    return render_to_response(
        'webui/entities/files.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def new( request, repo, org, cid ):
    """Gets new EID from workbench, creates new entity record.
    
    If it messes up, goes back to collection.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not (git_name and git_mail):
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
    collection.repo_fetch()
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
    # get new entity ID
    eid = None
    eids = api.entities_next(request, repo, org, cid, 1)
    if eids:
        eid = int(eids[-1].split('-')[3])
    if eid:
        # create new entity
        entity_uid = '{}-{}-{}-{}'.format(repo,org,cid,eid)
        entity_path = Entity.entity_path(request, repo, org, cid, eid)
        # entity.json template
        Entity(entity_path).dump_json(path=settings.TEMPLATE_EJSON,
                                      template=True)
        exit,status = commands.entity_create(git_name, git_mail,
                                             collection.path, entity_uid,
                                             [collection.json_path_rel, collection.ead_path_rel],
                                             [settings.TEMPLATE_EJSON, settings.TEMPLATE_METS])
        collection.cache_delete()
        if exit:
            logger.error(exit)
            logger.error(status)
            messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
        else:
            return HttpResponseRedirect(reverse('webui-entity-edit', args=[repo,org,cid,eid]))
    else:
        logger.error('Could not get new ID from workbench!')
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_ERR_NO_IDS'])
    # something happened...
    logger.error('Could not create new entity!')
    messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_ERR_CREATE'])
    return HttpResponseRedirect(reverse('webui-collection', args=[repo,org,cid]))

@ddrview
@login_required
@storage_required
def edit( request, repo, org, cid, eid ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    collection.repo_fetch()
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    #
    if request.method == 'POST':
        form = DDRForm(request.POST, fields=ENTITY_FIELDS)
        if form.is_valid():
            entity.form_post(form)
            entity.dump_json()
            entity.dump_mets()
            updated_files = [entity.json_path, entity.mets_path,]
            success_msg = WEBUI_MESSAGES['VIEWS_ENT_UPDATED']
            
            # if inheritable fields selected, propagate changes to child objects
            inheritables = entity.selected_inheritables(form.cleaned_data)
            modified_ids,modified_files = entity.update_inheritables(inheritables, form.cleaned_data)
            if modified_files:
                updated_files = updated_files + modified_files
            if modified_ids:
                success_msg = 'Object updated. ' \
                              'The value(s) for <b>%s</b> were applied to <b>%s</b>' % (
                                  ', '.join(inheritables), ', '.join(modified_ids))
            
            exit,status = commands.entity_update(git_name, git_mail,
                                                 entity.parent_path, entity.id,
                                                 updated_files)
            collection.cache_delete()
            if exit:
                messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
            else:
                messages.success(request, success_msg)
                return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    else:
        form = DDRForm(entity.form_prep(), fields=ENTITY_FIELDS)
    return render_to_response(
        'webui/entities/edit-json.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,
         'form': form,
         },
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def edit_json( request, repo, org, cid, eid ):
    """
    NOTE: will permit editing even if entity is locked!
    (which you need to do sometimes).
    """
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    #if collection.locked():
    #    messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
    #    return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    #collection.repo_fetch()
    #if collection.repo_behind():
    #    messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
    #    return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    #if entity.locked():
    #    messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
    #    return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    #
    if request.method == 'POST':
        form = JSONForm(request.POST)
        if form.is_valid():
            git_name = request.session.get('git_name')
            git_mail = request.session.get('git_mail')
            if git_name and git_mail:
                json = form.cleaned_data['json']
                # TODO validate XML
                with open(entity.json_path, 'w') as f:
                    f.write(json)
                
                exit,status = commands.entity_update(
                    git_name, git_mail,
                    entity.parent_path, entity.id,
                    [entity.json_path])
                
                collection.cache_delete()
                if exit:
                    messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
                else:
                    messages.success(request, WEBUI_MESSAGES['VIEWS_ENT_UPDATED'])
                    return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
            else:
                messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    else:
        with open(entity.json_path, 'r') as f:
            json = f.read()
        form = JSONForm({'json': json,})
    return render_to_response(
        'webui/entities/edit-raw.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': entity.parent_uid,
         'entity': entity,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def edit_mets_xml( request, repo, org, cid, eid ):
    """
    on GET
    - reads contents of EAD.xml
    - puts in form, in textarea
    - user edits XML
    on POST
    - write contents of field to EAD.xml
    - commands.update
    """
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    collection.repo_fetch()
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    #
    if request.method == 'POST':
        form = UpdateForm(request.POST)
        if form.is_valid():
            git_name = request.session.get('git_name')
            git_mail = request.session.get('git_mail')
            if git_name and git_mail:
                xml = form.cleaned_data['xml']
                # TODO validate XML
                with open(entity.mets_path, 'w') as f:
                    f.write(xml)
                
                exit,status = commands.entity_update(
                    git_name, git_mail,
                    entity.parent_path, entity.id,
                    [entity.mets_path])
                
                collection.cache_delete()
                if exit:
                    messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
                else:
                    messages.success(request, WEBUI_MESSAGES['VIEWS_ENT_UPDATED'])
                    return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
            else:
                messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    else:
        form = UpdateForm({'xml': entity.mets().xml,})
    return render_to_response(
        'webui/entities/edit-mets.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': entity.parent_uid,
         'entity': entity,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def edit_xml( request, repo, org, cid, eid, slug, Form, FIELDS, namespaces=None ):
    """Edit the contents of <archdesc>.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection_uid = '{}-{}-{}'.format(repo, org, cid)
    entity_uid     = '{}-{}-{}-{}'.format(repo, org, cid, eid)
    collection_abs = os.path.join(settings.MEDIA_BASE, collection_uid)
    entity_abs     = os.path.join(collection_abs,'files',entity_uid)
    entity_rel     = os.path.join('files',entity_uid)
    xml_path_rel   = 'mets.xml'
    xml_path_abs   = os.path.join(entity_abs, xml_path_rel)
    with open(xml_path_abs, 'r') as f:
        xml = f.read()
    fields = Form.prep_fields(FIELDS, xml, namespaces=namespaces)
    #
    if request.method == 'POST':
        form = Form(request.POST, fields=fields, namespaces=namespaces)
        if form.is_valid():
            form_fields = form.fields
            cleaned_data = form.cleaned_data
            xml_new = Form.process(xml, fields, form, namespaces=namespaces)
            # TODO validate XML
            with open(xml_path_abs, 'w') as fnew:
                fnew.write(xml_new)
            # TODO validate XML
            exit,status = commands.entity_update(git_name, git_mail, collection_abs, entity_uid, [xml_path_rel])
            if exit:
                messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
            else:
                messages.success(request, '<{}> updated'.format(slug))
                return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    else:
        form = Form(fields=fields, namespaces=namespaces)
    # template
    try:
        tf = 'webui/collections/edit-{}.html'.format(slug)
        t = get_template(tf)
        template_filename = tf
    except:
        template_filename = 'webui/entities/edit-xml.html'
    return render_to_response(
        template_filename,
        {'repo': repo,
         'org': org,
         'cid': cid,
         'eid': eid,
         'collection_uid': collection_uid,
         'entity_uid': entity_uid,
         'slug': slug,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

def edit_mets( request, repo, org, cid, eid ):
    return edit_xml(request, repo, org, cid, eid,
                    slug='mets',
                    Form=MetsForm, FIELDS=METS_FIELDS,
                    namespaces=NAMESPACES,)

@ddrview
@login_required
@storage_required
def unlock( request, repo, org, cid, eid, task_id ):
    """Provides a way to remove entity lockfile through the web UI.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    if task_id and entity.locked() and (task_id == entity.locked()):
        entity.unlock(task_id)
        messages.success(request, 'Object <b>%s</b> unlocked.' % entity.id)
    return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
