from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os

from bs4 import BeautifulSoup

from django.conf import settings
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.files import File
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import get_template

from DDR import commands

from ddrlocal.models.collection import COLLECTION_FIELDS

from search import add_update
from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui import get_repos_orgs
from webui import api
from webui.decorators import ddrview
from webui.forms import DDRForm
from webui.forms.collections import NewCollectionForm, UpdateForm
from webui.models import Collection
from webui.tasks import collection_sync
from webui.views.decorators import login_required
from xmlforms.models import XMLModel


# helpers --------------------------------------------------------------

def _uid_path(request, repo, org, cid):
    uid = '{}-{}-{}'.format(repo, org, cid)
    path = os.path.join(settings.MEDIA_BASE, uid)
    return uid,path

def alert_if_conflicted(request, collection):
    if collection.repo_conflicted():
        url = reverse('webui-merge', args=[collection.repo,collection.org,collection.cid])
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_CONFLICTED'].format(collection.id, url))



# views ----------------------------------------------------------------

@storage_required
def collections( request ):
    collections = []
    for o in get_repos_orgs():
        repo,org = o.split('-')
        colls = []
        for coll in commands.collections_local(settings.MEDIA_BASE, repo, org):
            if coll:
                coll = os.path.basename(coll)
                c = coll.split('-')
                repo,org,cid = c[0],c[1],c[2]
                collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
                colls.append(collection)
        collections.append( (o,repo,org,colls) )
    return render_to_response(
        'webui/collections/index.html',
        {'collections': collections,},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def detail( request, repo, org, cid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    alert_if_conflicted(request, collection)
    entities = sorted(collection.entities(), key=lambda e: e.id, reverse=True)
    return render_to_response(
        'webui/collections/detail.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'collection': collection,
         'entities': entities,
         'unlock_task_id': collection.locked(),},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def entities( request, repo, org, cid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    alert_if_conflicted(request, collection)
    collection_uid,collection_path = _uid_path(request, repo, org, cid)
    ead_path_rel = 'ead.xml'
    ead_path_abs = os.path.join(collection_path, ead_path_rel)
    ead = open( os.path.join(collection_path, 'ead.xml'), 'r').read()
    ead_soup = BeautifulSoup(ead, 'xml')
    entities = collection_entities(ead_soup)
    return render_to_response(
        'webui/collections/entities.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'entities': entities,
         },
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def changelog( request, repo, org, cid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    alert_if_conflicted(request, collection)
    return render_to_response(
        'webui/collections/changelog.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'collection': collection,},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def collection_json( request, repo, org, cid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    alert_if_conflicted(request, collection)
    return HttpResponse(json.dumps(collection.json().data), mimetype="application/json")

@ddrview
@storage_required
def git_status( request, repo, org, cid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    alert_if_conflicted(request, collection)
    status = commands.status(collection.path)
    astatus = commands.annex_status(collection.path)
    return render_to_response(
        'webui/collections/git-status.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'collection': collection,
         'status': status,
         'astatus': astatus,
         },
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def ead_xml( request, repo, org, cid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    alert_if_conflicted(request, collection)
    soup = BeautifulSoup(collection.ead().xml, 'xml')
    return HttpResponse(soup.prettify(), mimetype="application/xml")

@ddrview
@login_required
@storage_required
def sync( request, repo, org, cid ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    alert_if_conflicted(request, collection)
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
    if request.method == 'POST':
        result = collection_sync.apply_async( (git_name,git_mail,collection.path), countdown=2)
        lockstatus = collection.lock(result.task_id)
        # add celery task_id to session
        celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
        # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
        task = {'task_id': result.task_id,
                'action': 'webui-collection-sync',
                'collection_id': collection.id,
                'collection_url': collection.url(),
                'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
        celery_tasks[result.task_id] = task
        request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
    
    return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )

@ddrview
@login_required
@storage_required
def new( request, repo, org ):
    """Gets new CID from workbench, creates new collection record.
    
    If it messes up, goes back to collection list.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not (git_name and git_mail):
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    # get new collection ID
    cid = None
    cids = api.collections_next(request, repo, org, 1)
    if cids:
        cid = int(cids[-1].split('-')[2])
    if cid:
        # create the new collection repo
        collection_uid,collection_path = _uid_path(request, repo, org, cid)
        # collection.json template
        Collection(collection_path).dump_json(path=settings.TEMPLATE_CJSON,
                                              template=True)
        exit,status = commands.create(git_name, git_mail,
                                      collection_path,
                                      [settings.TEMPLATE_CJSON, settings.TEMPLATE_EAD],
                                      agent=settings.AGENT)
        if exit:
            logger.error(exit)
            logger.error(status)
            messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
        else:
            # update search index
            json_path = os.path.join(collection_path, 'collection.json')
            add_update('ddr', 'collection', json_path)
            # positive feedback
            return HttpResponseRedirect( reverse('webui-collection-edit', args=[repo,org,cid]) )
    else:
        logger.error('Could not get new ID from workbench!')
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_ERR_NO_IDS'])
    # something happened...
    logger.error('Could not create new collecion!')
    messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_ERR_CREATE'])
    return HttpResponseRedirect(reverse('webui-collections'))

@ddrview
@login_required
@storage_required
def edit( request, repo, org, cid ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
    collection.repo_fetch()
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
    if request.method == 'POST':
        form = DDRForm(request.POST, fields=COLLECTION_FIELDS)
        if form.is_valid():
            collection.form_post(form)
            collection.dump_json()
            collection.dump_ead()
            updated_files = [collection.json_path, collection.ead_path,]
            success_msg = WEBUI_MESSAGES['VIEWS_COLL_UPDATED']
            
            # if inheritable fields selected, propagate changes to child objects
            inheritables = collection.selected_inheritables(form.cleaned_data)
            modified_ids,modified_files = collection.update_inheritables(inheritables, form.cleaned_data)
            if modified_files:
                updated_files = updated_files + modified_files
            if modified_ids:
                success_msg = 'Collection updated. ' \
                              'The value(s) for <b>%s</b> were applied to <b>%s</b>' % (
                                  ', '.join(inheritables), ', '.join(modified_ids))
            
            exit,status = commands.update(git_name, git_mail,
                                          collection.path, updated_files,
                                          agent=settings.AGENT)
            collection.cache_delete()
            if exit:
                messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
            else:
                # update search index
                add_update('ddr', 'collection', collection.json_path)
                # positive feedback
                messages.success(request, success_msg)
                return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
    else:
        form = DDRForm(collection.form_prep(), fields=COLLECTION_FIELDS)
    return render_to_response(
        'webui/collections/edit-json.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'collection': collection,
         'form': form,
         },
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def edit_ead( request, repo, org, cid ):
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
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
    ead_path_rel = 'ead.xml'
    ead_path_abs = os.path.join(collection.path, ead_path_rel)
    #
    if request.method == 'POST':
        form = UpdateForm(request.POST)
        if form.is_valid():
            git_name = request.session.get('git_name')
            git_mail = request.session.get('git_mail')
            if git_name and git_mail:
                xml = form.cleaned_data['xml']
                # TODO validate XML
                with open(ead_path_abs, 'w') as f:
                    f.write(xml)
                
                exit,status = commands.update(git_name, git_mail,
                                              collection.path, [ead_path_rel],
                                              agent=settings.AGENT)
                
                if exit:
                    messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
                else:
                    messages.success(request, 'Collection metadata updated')
                    return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
            else:
                messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    else:
        with open(ead_path_abs, 'r') as f:
            xml = f.read()
        form = UpdateForm({'xml':xml,})
    return render_to_response(
        'webui/collections/edit-ead.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'collection_uid': collection.id,
         'collection': collection,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

@login_required
@storage_required
def edit_xml( request, repo, org, cid, slug, Form, FIELDS ):
    """Edit the contents of <archdesc>.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection_uid,collection_path = _uid_path(request, repo, org, cid)
    ead_path_rel = 'ead.xml'
    ead_path_abs = os.path.join(collection_path, ead_path_rel)
    with open(ead_path_abs, 'r') as f:
        xml = f.read()
    fields = Form.prep_fields(FIELDS, xml)
    #
    if request.method == 'POST':
        form = Form(request.POST, fields=fields)
        if form.is_valid():
            form_fields = form.fields
            cleaned_data = form.cleaned_data
            xml_new = Form.process(xml, fields, form)
            # TODO validate XML
            with open(ead_path_abs, 'w') as fnew:
                fnew.write(xml_new)
            # TODO validate XML
            exit,status = commands.update(git_name, git_mail,
                                          collection_path, [ead_path_rel],
                                          agent=settings.AGENT)
            if exit:
                messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
            else:
                messages.success(request, '<{}> updated'.format(slug))
                return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
    else:
        form = Form(fields=fields)
    # template
    try:
        tf = 'webui/collections/edit-{}.html'.format(slug)
        t = get_template(tf)
        template_filename = tf
    except:
        template_filename = 'webui/collections/edit-xml.html'
    return render_to_response(
        template_filename,
        {'repo': repo,
         'org': org,
         'cid': cid,
         'collection_uid': collection_uid,
         'slug': slug,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

def edit_overview( request, repo, org, cid ):
    return edit_xml(request, repo, org, cid,
                    slug='overview', Form=CollectionOverviewForm, FIELDS=COLLECTION_OVERVIEW_FIELDS)

def edit_admininfo( request, repo, org, cid ):
    return edit_xml(request, repo, org, cid,
                    slug='admininfo', Form=AdminInfoForm, FIELDS=ADMIN_INFO_FIELDS)

def edit_bioghist( request, repo, org, cid ):
    return edit_xml(request, repo, org, cid,
                    slug='bioghist', Form=BiogHistForm, FIELDS=BIOG_HIST_FIELDS)

def edit_scopecontent( request, repo, org, cid ):
    return edit_xml(request, repo, org, cid,
                    slug='scopecontent', Form=ScopeContentForm, FIELDS=SCOPE_CONTENT_FIELDS)

def edit_adjunctdesc( request, repo, org, cid ):
    return edit_xml(request, repo, org, cid,
                    slug='descgrp', Form=AdjunctDescriptiveForm, FIELDS=ADJUNCT_DESCRIPTIVE_FIELDS)

@ddrview
@login_required
@storage_required
def unlock( request, repo, org, cid, task_id ):
    """Provides a way to remove collection lockfile through the web UI.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    if task_id and collection.locked() and (task_id == collection.locked()):
        collection.unlock(task_id)
        messages.success(request, 'Collection <b>%s</b> unlocked.' % collection.id)
    return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
