from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
import random
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
from django.template.loader import get_template

from DDR import batch
from DDR import commands
from DDR import converters
from DDR import dvcs
from DDR import fileio

from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui import docstore
from webui.decorators import ddrview
from webui.forms import DDRForm
from webui.forms.collections import NewCollectionForm, UpdateForm, UploadFileForm
from webui.forms.collections import SyncConfirmForm, SignaturesConfirmForm
from webui import gitolite
from webui.gitstatus import repository, annex_info
from webui.models import Collection, COLLECTION_STATUS_CACHE_KEY, COLLECTION_STATUS_TIMEOUT
from webui.identifier import Identifier
from webui.tasks import collection as collection_tasks
from webui.tasks import dvcs as dvcs_tasks
from webui.views.decorators import login_required


# helpers --------------------------------------------------------------

def alert_if_conflicted(request, collection):
    if collection.repo_conflicted():
        url = reverse('webui-merge', args=[collection.id])
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_CONFLICTED'].format(collection.id, url))
    


# views ----------------------------------------------------------------

@storage_required
def collections( request ):
    """
    We are displaying collection status vis-a-vis the project Gitolite server.
    It takes too long to run git-status on every repo so, if repo statuses are not
    cached they will be updated by jQuery after page load has finished.
    """
    collections = []
    collection_status_urls = []
    for object_id in gitolite.get_repos_orgs():
        identifier = Identifier(object_id)
        # TODO Identifier: Organization object instead of repo and org
        repo,org = list(identifier.parts.values())
        collection_paths = Collection.collection_paths(settings.MEDIA_BASE, repo, org)
        colls = []
        for collection_path in collection_paths:
            if collection_path:
                identifier = Identifier(path=collection_path)
                collection = Collection.from_identifier(identifier)
                colls.append(collection)
                gitstatus = collection.gitstatus()
                if gitstatus and gitstatus.get('sync_status'):
                    collection.sync_status = gitstatus['sync_status']
                else:
                    collection_status_urls.append( "'%s'" % collection.sync_status_url())
        collections.append( (object_id,colls) )
    # load statuses in random order
    random.shuffle(collection_status_urls)
    return render(request, 'webui/collections/index.html', {
        'collections': collections,
        'collection_status_urls': ', '.join(collection_status_urls),
    })

@storage_required
def detail( request, cid ):
    collection = Collection.from_identifier(Identifier(cid))
    collection.model_def_commits()
    collection.model_def_fields()
    alert_if_conflicted(request, collection)
    return render(request, 'webui/collections/detail.html', {
        'collection': collection,
        'collection_unlock_url': collection.unlock_url(collection.locked()),
        # cache this for later
        'annex_info': annex_info(repository(collection.path_abs)),
    })

@storage_required
def children( request, cid ):
    collection = Collection.from_identifier(Identifier(cid))
    alert_if_conflicted(request, collection)
    objects = collection.children()
    # paginate
    thispage = request.GET.get('page', 1)
    paginator = Paginator(objects, settings.RESULTS_PER_PAGE)
    page = paginator.page(thispage)
    return render(request, 'webui/collections/entities.html', {
        'collection': collection,
        'paginator': paginator,
        'page': page,
        'thispage': thispage,
    })

@storage_required
def changelog( request, cid ):
    collection = Collection.from_identifier(Identifier(cid))
    alert_if_conflicted(request, collection)
    return render(request, 'webui/collections/changelog.html', {
        'collection': collection,
    })

@ddrview
@storage_required
def sync_status_ajax( request, cid ):
    collection = Collection.from_identifier(Identifier(cid))
    gitstatus = collection.gitstatus()
    if gitstatus:
        sync_status = gitstatus['sync_status']
        if sync_status.get('timestamp',None):
            sync_status['timestamp'] = converters.datetime_to_text(sync_status['timestamp'])
        return HttpResponse(json.dumps(sync_status), content_type="application/json")
    raise Http404

@ddrview
@storage_required
def git_status( request, cid ):
    collection = Collection.from_identifier(Identifier(cid))
    alert_if_conflicted(request, collection)
    gitstatus = collection.gitstatus()
    remotes = dvcs.remotes(dvcs.repository(collection.path))
    return render(request, 'webui/collections/git-status.html', {
        'collection': collection,
        'status': gitstatus.get('status', 'git-status unavailable'),
        'astatus': gitstatus.get('annex_status', 'annex-status unavailable'),
        'timestamp': gitstatus.get('timestamp'),
        'remotes': remotes,
    })

@ddrview
@login_required
@storage_required
def sync( request, cid ):
    try:
        collection = Collection.from_identifier(Identifier(cid))
    except:
        raise Http404
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    alert_if_conflicted(request, collection)
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect(collection.absolute_url())
    if request.method == 'POST':
        form = SyncConfirmForm(request.POST)
        form_is_valid = form.is_valid()
        if form.is_valid() and form.cleaned_data['confirmed']:
            result = collection_tasks.sync.apply_async(
                (git_name,git_mail,collection.path),
                countdown=2
            )
            lockstatus = collection.lock(result.task_id)
            # add celery task_id to session
            celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
            # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
            task = {'task_id': result.task_id,
                    'action': 'collection-sync',
                    'collection_id': collection.id,
                    'collection_url': collection.absolute_url(),
                    'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
            celery_tasks[result.task_id] = task
            request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
            return HttpResponseRedirect(collection.absolute_url())
        #else:
        #    assert False
    else:
        form = SyncConfirmForm()
    return render(request, 'webui/collections/sync-confirm.html', {
        'collection': collection,
        'form': form,
    })

@ddrview
@login_required
@storage_required
def new( request, oid ):
    """Redirect to new_idservice or new_manual.
    """
    if settings.IDSERVICE_API_BASE:
        return HttpResponseRedirect(
            reverse('webui-collection-newidservice', args=[oid])
        )
    return HttpResponseRedirect(reverse('webui-collection-newmanual', args=[oid]))

@ddrview
@login_required
@storage_required
def new_idservice( request, oid ):
    """Gets new CID from workbench, creates new collection record.
    
    If it messes up, goes back to collection list.
    """
    oidentifier = Identifier(oid)
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not (git_name and git_mail):
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    # refer task to celery backend
    collection_tasks.new_idservice(
        request,
        oidentifier,
        git_name, git_mail
    )
    return HttpResponseRedirect(reverse('webui-collections'))

@ddrview
@login_required
@storage_required
def new_manual( request, oid ):
    """Ask for Entity ID, then create new Entity.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    
    oidentifier = Identifier(oid).object()
    idparts = oidentifier.idparts
    collection_ids = sorted([
        os.path.basename(cpath)
        for cpath in Collection.collection_paths(
            settings.MEDIA_BASE,
            idparts['repo'],
            idparts['org']
        )
    ])
    collection_ids.reverse()
    
    if request.method == 'POST':
        form = NewCollectionForm(request.POST)
        if form.is_valid():
            
            # TODO get this from Entity class or something
            idparts['model'] = 'collection'
            idparts['cid'] = str(form.cleaned_data['cid'])
            cidentifier = Identifier(parts=idparts)
            if not cidentifier:
                messages.error(
                    request,
                    "Could not generate a legal ID from your input. Try again."
                )
            elif cidentifier.parent_id(stubs=True) != oidentifier.id:
                messages.error(
                    request,
                    "Can only create collections for this organization. Try again."
                )
            elif cidentifier.id in collection_ids:
                messages.error(
                    request,
                    "Object ID %s already exists. Try again." % cidentifier.id
                )
            else:
                # refer task to celery backend
                collection_tasks.new_manual(request, cidentifier)
                messages.warning(
                    request,
                    'IMPORTANT: Register this ID with the ID service ASAP!'
                )
                    
            return HttpResponseRedirect(
                reverse('webui-collections')
            )
            
    else:
        data = {
            'repo': idparts['repo'],
            'org': idparts['org'],
        }
        form = NewCollectionForm(data)
    return render(request, 'webui/collections/new-manual.html', {
        'form': form,
        'collection_ids': collection_ids,
    })

@ddrview
@login_required
@storage_required
def edit( request, cid ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_identifier(Identifier(cid))
    module = collection.identifier.fields_module()
    collection.model_def_commits()
    collection.model_def_fields()
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect(collection.absolute_url())
    collection.repo_fetch()
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect(collection.absolute_url())
    if request.method == 'POST':
        form = DDRForm(request.POST, fields=module.FIELDS)
        if form.is_valid():
            
            collection.form_post(form.cleaned_data)
            # write these so we see a change on refresh
            # will be rewritten in collection.save()
            collection.write_json()
            
            # commit files, delete cache, update search index, update git status
            collection_tasks.edit(
                request,
                collection, form.cleaned_data,
                git_name, git_mail
            )
            
            return HttpResponseRedirect(collection.absolute_url())
        
    else:
        form = DDRForm(collection.form_prep(), fields=module.FIELDS)
    return render(request, 'webui/collections/edit-json.html', {
        'collection': collection,
        'form': form,
    })

@ddrview
@login_required
@storage_required
def signatures( request, cid ):
    try:
        collection = Collection.from_identifier(Identifier(cid))
    except:
        raise Http404
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    alert_if_conflicted(request, collection)
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect(collection.absolute_url())
    if request.method == 'POST':
        form = SignaturesConfirmForm(request.POST)
        form_is_valid = form.is_valid()
        if form.is_valid() and form.cleaned_data['confirmed']:
            
            result = collection_tasks.signatures.apply_async(
                (collection.path,git_name,git_mail),
                countdown=2
            )
            lockstatus = collection.lock(result.task_id)
            # add celery task_id to session
            celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
            # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
            task = {
                'task_id': result.task_id,
                'action': 'collection-signatures',
                'collection_id': collection.id,
                'collection_url': collection.absolute_url(),
                'start': converters.datetime_to_text(datetime.now(settings.TZ)),
            }
            celery_tasks[result.task_id] = task
            request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
            return HttpResponseRedirect(collection.absolute_url())
        
    else:
        form = SignaturesConfirmForm()
    return render(request, 'webui/collections/signatures-confirm.html', {
        'collection': collection,
        'form': form,
    })
 
@login_required
@storage_required
def csv_export( request, cid, model=None ):
    """
    """
    if (not model) or (not (model in ['entity','file'])):
        raise Http404
    collection = Collection.from_identifier(Identifier(cid))
    things = {'entity':'objects', 'file':'files'}
    csv_path = settings.CSV_EXPORT_PATH[model] % collection.id
    csv_filename = os.path.basename(csv_path)
    if model == 'entity':
        file_url = reverse('webui-collection-csv-entities', args=[collection.id])
    elif model == 'file':
        file_url = reverse('webui-collection-csv-files', args=[collection.id])
    # do it
    result = collection_tasks.csv_export_model.apply_async(
        (collection.path,model),
        countdown=2
    )
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    task = {'task_id': result.task_id,
            'action': 'csv-export-model',
            'collection_id': collection.id,
            'collection_url': collection.absolute_url(),
            'things': things[model],
            'file_name': csv_filename,
            'file_url': file_url,
            'start': converters.datetime_to_text(datetime.now(settings.TZ)),}
    celery_tasks[result.task_id] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
    return HttpResponseRedirect(collection.absolute_url())

@storage_required
def csv_download( request, cid, model=None ):
    """Offers CSV file in settings.CSV_TMPDIR for download.
    
    File must actually exist in settings.CSV_EXPORT_PATH and be readable.
    File must be readable by Python csv module.
    If all that is true then it must be a legal CSV file.
    """
    collection = Collection.from_identifier(Identifier(cid))
    path = settings.CSV_EXPORT_PATH[model] % collection.id
    filename = os.path.basename(path)
    if not os.path.exists(path):
        raise Http404
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    writer = csv.writer(
        response,
        delimiter=fileio.CSV_DELIMITER,
        quotechar=fileio.CSV_QUOTECHAR,
        quoting=fileio.CSV_QUOTING
    )
    with open(path, 'rb') as f:
        reader = csv.reader(
            f,
            delimiter=fileio.CSV_DELIMITER,
            quotechar=fileio.CSV_QUOTECHAR,
            quoting=fileio.CSV_QUOTING
        )
        for row in reader:
            writer.writerow(row)
    return response

CSV_IMPORT_FILE = '/tmp/import-{cid}-{model}.csv'

def handle_uploaded_file(cid, model, f):
    path = CSV_IMPORT_FILE.format(cid=cid, model=model)
    with open(path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
 
@login_required
@storage_required
def csv_import( request, cid, model=None ):
    """Accepts a CSV file for batch.Import
    """
    if (not model) or (not (model in ['entity','file'])):
        raise Http404
    collection = Collection.from_identifier(Identifier(cid))
    repo = dvcs.repository(collection.identifier.path_abs())
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            
            git_name = request.session['git_name']
            git_mail = request.session['git_mail']
            
            csv_path = CSV_IMPORT_FILE.format(
                cid=collection.identifier.id,
                model=collection.identifier.model
            )
            handle_uploaded_file(
                collection.identifier.id,
                collection.identifier.model,
                request.FILES['file']
            )
            if os.path.exists(csv_path):
                messages.success(request, 'CSV file upload success!.')
            else:
                messages.error(request, 'CSV file upload failed!')
                return HttpResponseRedirect(collection.absolute_url())

            if model == 'entity':
                
                imported = batch.Importer.import_entities(
                    csv_path=csv_path,
                    cidentifier=collection.identifier,
                    vocabs_url=settings.VOCABS_URL,
                    git_name=git_name,
                    git_mail=git_mail,
                    agent='ddrlocal-csv-import-entity',
                    dryrun=False,
                )
                imported_rel = [
                    o.identifier.path_rel()
                    for o in imported
                ]
                changelogs = list(set([
                    os.path.join(
                        os.path.dirname(path_rel),
                        'changelog'
                    )
                    for path_rel in imported_rel
                    if 'entity.json' in path_rel
                ]))
                imported_all = imported_rel + changelogs
                result = commands.commit_files(
                    repo=repo,
                    message='Imported by ddr-local from file "%s"' % csv_path,
                    git_files=imported_all,
                    annex_files=[]
                )
                msg = 'Successfully imported {} objects from {}.'.format(
                    str(len(imported)),
                    request.FILES['file'].name,
                )
                messages.success(request, msg)

            elif model == 'file':
                
                imported = batch.Importer.import_files(
                    csv_path=csv_path,
                    cidentifier=collection.identifier,
                    vocabs_url=settings.VOCABS_URL,
                    git_name=git_name,
                    git_mail=git_mail,
                    agent='ddrlocal-csv-import-file',
                    row_start=0,
                    row_end=9999999,
                    dryrun=False
                )
                # flatten: import_files returns a list of file,entity lists
                imported_flat = [i for imprtd in imported for i in imprtd]
                # import_files returns absolute paths but we need relative
                imported_rel = [
                    os.path.relpath(
                        file_path_abs,
                        collection.identifier.path_abs()
                    )
                    for file_path_abs in imported_flat
                ]
                # Add changelog for each entity
                changelogs = list(set([
                    os.path.join(
                        os.path.dirname(path_rel),
                        'changelog'
                    )
                    for path_rel in imported_rel
                    if 'entity.json' in path_rel
                ]))
                imported_all = imported_rel + changelogs
                result = commands.commit_files(
                    repo=repo,
                    message='Imported by ddr-local from file "%s"' % csv_path,
                    git_files=imported_all,
                    annex_files=[],
                )
                msg = 'Successfully imported {} files from {}.'.format(
                    str(len(imported)),
                    request.FILES['file'].name,
                )
                messages.success(request, msg)

            return HttpResponseRedirect(collection.absolute_url())
    else:
        form = UploadFileForm()
    return render(request, 'webui/collections/csv-import.html', {
        'collection': collection,
        'form': form,
    })

@ddrview
@login_required
@storage_required
def unlock( request, cid, task_id ):
    """Provides a way to remove collection lockfile through the web UI.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_identifier(Identifier(cid))
    if task_id and collection.locked() and (task_id == collection.locked()):
        collection.unlock(task_id)
        messages.success(request, 'Collection <b>%s</b> unlocked.' % collection.id)
    return HttpResponseRedirect(collection.absolute_url())

@ddrview
@login_required
@storage_required
def check(request, cid):
    ci = Identifier(cid)
    result = collection_tasks.check.apply_async(
        [ci.path_abs()],
        countdown=2
    )
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    task = {
        'task_id': result.task_id,
        'action': 'collection-check',
        'collection_id': ci.id,
        'collection_url': ci.urlpath('editor'),
        'start': converters.datetime_to_text(datetime.now(settings.TZ)),
    }
    celery_tasks[result.task_id] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
    return HttpResponseRedirect(ci.urlpath('editor'))
