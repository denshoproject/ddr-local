from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
import random

from bs4 import BeautifulSoup

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.context_processors import csrf
from django.core.files import File
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import get_template

from DDR import commands
from DDR import docstore

from ddrlocal.models.collection import COLLECTION_FIELDS

from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui import get_repos_orgs
from webui import api
from webui.decorators import ddrview, search_index
from webui.forms import DDRForm
from webui.forms.collections import NewCollectionForm, UpdateForm
from webui.models import Collection, COLLECTION_STATUS_CACHE_KEY, COLLECTION_STATUS_TIMEOUT
from webui.tasks import collection_sync, csv_export_model, export_csv_path
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

COLLECTION_SYNC_STATUS_CACHE_KEY = 'webui:collection:%s:sync-status'

def _sync_status( request, repo, org, cid, collection=None, cache_set=False ):
    """Cache collection repo sync status info for collections list page.
    Used in both .collections() and .sync_status_ajax().
    """
    collection_id = '-'.join([repo, org, cid])
    key = COLLECTION_SYNC_STATUS_CACHE_KEY % collection_id
    data = cache.get(key)
    if not data and cache_set:
        if not collection:
            collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
        status = 'unknown'
        btn = 'muted'
        if   collection.repo_ahead(): status = 'ahead'; btn = 'warning'
        elif collection.repo_behind(): status = 'behind'; btn = 'warning'
        elif collection.repo_conflicted(): status = 'conflicted'; btn = 'danger'
        elif collection.locked(): status = 'locked'; btn = 'warning'
        elif collection.repo_synced(): status = 'synced'; btn = 'success'
        data = {
            'row': '#%s' % collection.id,
            'color': btn,
            'cell': '#%s td.status' % collection.id,
            'status': status,
        }
        cache.set(key, data, COLLECTION_STATUS_TIMEOUT)
    return data


# views ----------------------------------------------------------------

@search_index
@storage_required
def collections( request ):
    """
    We are displaying collection status vis-a-vis the project Gitolite server.
    It takes too long to run git-status on every repo so, if repo statuses are not
    cached they will be updated by jQuery after page load has finished.
    """
    collections = []
    collection_ids = []
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
                # get status if cached, farm out to jquery if not
                collection.sync_status = _sync_status(request, repo, org, cid)
                if not collection.sync_status:
                    collection_ids.append( [repo,org,cid] )
        collections.append( (o,repo,org,colls) )
    # list of URLs for status updater
    random.shuffle(collection_ids)
    urls = ['"%s"' % reverse('webui-collection-sync-status-ajax',args=cid) for cid in collection_ids]
    collection_status_urls = ', '.join(urls)
    return render_to_response(
        'webui/collections/index.html',
        {'collections': collections,
         'collection_status_urls': collection_status_urls,},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def detail( request, repo, org, cid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    alert_if_conflicted(request, collection)
    return render_to_response(
        'webui/collections/detail.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'collection': collection,
         'entities': collection.entities(),
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
def sync_status_ajax( request, repo, org, cid ):
    data = _sync_status(request, repo, org, cid, cache_set=True)
    return HttpResponse(json.dumps(data), mimetype="application/json")

@ddrview
@storage_required
def git_status( request, repo, org, cid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    alert_if_conflicted(request, collection)
    status = collection.repo_status()
    astatus = collection.repo_annex_status()
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
    try:
        collection_ids = api.collections_next(request, repo, org, 1)
    except Exception as e:
        logger.error('Could not get new collecion ID!')
        logger.error(str(e.args))
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_ERR_NO_IDS'])
        messages.error(request, e)
        return HttpResponseRedirect(reverse('webui-collections'))
    cid = int(collection_ids[-1].split('-')[2])
    # create the new collection repo
    collection_uid,collection_path = _uid_path(request, repo, org, cid)
    # collection.json template
    Collection(collection_path).dump_json(path=settings.TEMPLATE_CJSON, template=True)
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
        with open(json_path, 'r') as f:
            document = json.loads(f.read())
        docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
        # positive feedback
        return HttpResponseRedirect( reverse('webui-collection-edit', args=[repo,org,cid]) )
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
                with open(collection.json_path, 'r') as f:
                    document = json.loads(f.read())
                docstore.post(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX, document)
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
 
@login_required
@storage_required
def csv_export( request, repo, org, cid, model=None ):
    """
    """
    if (not model) or (not (model in ['entity','file'])):
        raise Http404
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    things = {'entity':'objects', 'file':'files'}
    csv_path = export_csv_path(collection.path, model)
    csv_filename = os.path.basename(csv_path)
    if model == 'entity':
        file_url = reverse('webui-collection-csv-entities', args=[repo,org,cid])
    elif model == 'file':
        file_url = reverse('webui-collection-csv-files', args=[repo,org,cid])
    # do it
    result = csv_export_model.apply_async( (collection.path,model), countdown=2)
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    task = {'task_id': result.task_id,
            'action': 'webui-csv-export-model',
            'collection_id': collection.id,
            'collection_url': collection.url(),
            'things': things[model],
            'file_name': csv_filename,
            'file_url': file_url,
            'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
    celery_tasks[result.task_id] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
    return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )

@storage_required
def csv_download( request, repo, org, cid, model=None ):
    """Offers CSV file in settings.CSV_TMPDIR for download.
    
    File must actually exist in settings.CSV_TMPDIR and be readable.
    File must be readable by Python csv module.
    If all that is true then it must be a legal CSV file.
    """
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    path = export_csv_path(collection.path, model)
    filename = os.path.basename(path)
    if not os.path.exists(path):
        raise Http404
    import csv
    # TODO use vars from migrations.densho or put them in settings.
    CSV_DELIMITER = ','
    CSV_QUOTECHAR = '"'
    CSV_QUOTING = csv.QUOTE_ALL
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    writer = csv.writer(response, delimiter=CSV_DELIMITER, quotechar=CSV_QUOTECHAR, quoting=CSV_QUOTING)
    with open(path, 'rb') as f:
        reader = csv.reader(f, delimiter=CSV_DELIMITER, quotechar=CSV_QUOTECHAR, quoting=CSV_QUOTING)
        for row in reader:
            writer.writerow(row)
    return response

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
