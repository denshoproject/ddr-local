import csv
from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
import random

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseRedirect
from django.http import StreamingHttpResponse
from django.shortcuts import Http404, render
from django.urls import reverse

from DDR import converters
from DDR import docstore
from DDR import dvcs

from elastictools.docstore import TransportError
from elastictools import search
from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui import csvio
from webui.decorators import ddrview
from webui.forms import DDRForm
from webui.forms.collections import NewCollectionForm, UploadFileForm
from webui.forms.collections import SyncConfirmForm, SignaturesConfirmForm
from webui.forms.collections import ReindexConfirmForm
from webui import gitolite
from webui.gitstatus import repository, annex_info
from webui.models import Collection, INDEX_PREFIX
from webui.identifier import Identifier, InvalidIdentifierException
from webui.tasks import collection as collection_tasks
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
        try:
            identifier = Identifier(object_id)
        except InvalidIdentifierException as err:
            messages.error(request, f'{err}')
            break
        # TODO Identifier: Organization object instead of repo and org
        repo,org = list(identifier.parts.values())
        collection_paths = Collection.collection_paths(settings.MEDIA_BASE, repo, org)
        colls = []
        for collection_path in collection_paths:
            if collection_path:
                identifier = Identifier(path=collection_path)
                collection = Collection.from_identifier(identifier)
                colls.append(collection)
                #gitstatus = collection.gitstatus()
                gitstatus = {}
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
        'collection_unlock_url': collection.unlock_url(),
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
        messages.error(
            request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id)
        )
        return HttpResponseRedirect(collection.absolute_url())
    if not settings.OFFLINE:
        collection.repo_fetch()
        if collection.repo_behind():
            messages.error(
                request,
                WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id)
            )
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
def csv_export(request, cid, model):
    try:
        collection = Collection.from_identifier(Identifier(cid))
    except:
        raise Http404
    if not model in list(csvio.CSV_MODELS.keys()):
        raise Http404
    collection_tasks.csv_export(request, collection, model)
    return HttpResponseRedirect(collection.absolute_url())

@storage_required
def csv_download(request, cid, model):
    """Offers CSV file in settings.CSV_TMPDIR for download.
    
    File must actually exist in settings.CSV_EXPORT_PATH and be readable.
    File must be readable by Python csv module.
    If all that is true then it must be a legal CSV file.
    """
    try:
        collection = Collection.from_identifier(Identifier(cid))
    except:
        raise Http404
    if not model in list(csvio.CSV_MODELS.keys()):
        raise Http404
    path = csvio.csv_path(collection, model)
    if not path.exists():
        raise Http404
    
    class Echo:
        """Object that implements write method of file-like interface."""
        def write(self, value):
            """Write value by returning it instead of storing in a buffer"""
            return value
    
    rows = csvio.csv_rows(path)
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse(
        (writer.writerow(row) for row in rows),
        content_type="text/csv"
    )
    response['Content-Disposition'] = 'attachment; filename="%s"' % path.name
    return response

@login_required
@storage_required
def csv_import(request, cid, model):
    """Accepts a CSV file for batch import
    
    TODO fix broken files import
    """
    try:
        collection = Collection.from_identifier(Identifier(cid))
    except:
        raise Http404
    if not model in list(csvio.CSV_MODELS.keys()):
        raise Http404
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # write uploaded file to tmp/
            handle_uploaded_file(cid, model, request.FILES['file'])
            csv_path = csvio.csv_import_path(cid, model)
            if csv_path.exists():
                messages.success(request, 'CSV file upload success!.')
            else:
                messages.error(request, 'CSV file upload failed!')
                return HttpResponseRedirect(collection.absolute_url())
            # process the contents
            result,imported = csvio.import_from_csv(
                csv_path, collection, model,
                request.session['git_name'],
                request.session['git_mail'],
            )
            msg = 'Successfully imported {} objects from {}.'.format(
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

def handle_uploaded_file(cid, model, f):
    """Write uploaded file to /tmp/
    """
    path = csvio.csv_import_path(cid, model)
    with path.open('wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

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

@ddrview
@login_required
def reindex(request, cid):
    # nice UI if Elasticsearch is down
    try:
        docstore.DocstoreManager(INDEX_PREFIX, settings.DOCSTORE_HOST, settings).status()
    except TransportError:
        messages.error(
            request, "<b>TransportError</b>: Cannot connect to search engine."
        )

    try:
        collection = Collection.from_identifier(Identifier(cid))
    except:
        raise Http404
    alert_if_conflicted(request, collection)
    if request.method == 'POST':
        form = ReindexConfirmForm(request.POST)
        form_is_valid = form.is_valid()
        if form.is_valid() and form.cleaned_data['confirmed']:
            # update search index
            collection_tasks.reindex(
                request,
                collection,
            )
            return HttpResponseRedirect(collection.absolute_url())
        #else:
        #    assert False
    else:
        form = ReindexConfirmForm()
    return render(request, 'webui/collections/reindex-confirm.html', {
        'collection': collection,
        'form': form,
    })
