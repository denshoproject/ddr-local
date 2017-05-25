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
from django.core.context_processors import csrf
from django.core.files import File
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import get_template

from DDR import commands
from DDR import converters
from DDR import docstore
from DDR import dvcs
from DDR import fileio
from DDR import idservice
from DDR import util

from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui.decorators import ddrview, search_index
from webui.forms import DDRForm, ObjectIDForm
from webui.forms.collections import UpdateForm
from webui.forms.collections import SyncConfirmForm, SignaturesConfirmForm
from webui import gitolite
from webui.gitstatus import repository, annex_info
from webui.models import Collection, COLLECTION_STATUS_CACHE_KEY, COLLECTION_STATUS_TIMEOUT
from webui.identifier import Identifier
from webui import tasks
from webui.views import idservice_resume
from webui.views.decorators import login_required


# helpers --------------------------------------------------------------

def alert_if_conflicted(request, collection):
    if collection.repo_conflicted():
        url = reverse('webui-merge', args=[collection.id])
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_CONFLICTED'].format(collection.id, url))


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
    collection_status_urls = []
    for object_id in gitolite.get_repos_orgs():
        identifier = Identifier(object_id)
        # TODO Identifier: Organization object instead of repo and org
        repo,org = identifier.parts.values()
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
    return render_to_response(
        'webui/collections/index.html',
        {'collections': collections,
         'collection_status_urls': ', '.join(collection_status_urls),},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def detail( request, cid ):
    collection = Collection.from_identifier(Identifier(cid))
    collection.model_def_commits()
    collection.model_def_fields()
    alert_if_conflicted(request, collection)
    return render_to_response(
        'webui/collections/detail.html',
        {
            'collection': collection,
            'collection_unlock_url': collection.unlock_url(collection.locked()),
            # cache this for later
            'annex_info': annex_info(repository(collection.path_abs)),
        },
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def children( request, cid ):
    collection = Collection.from_identifier(Identifier(cid))
    alert_if_conflicted(request, collection)
    objects = collection.children()
    # paginate
    thispage = request.GET.get('page', 1)
    paginator = Paginator(objects, settings.RESULTS_PER_PAGE)
    page = paginator.page(thispage)
    return render_to_response(
        'webui/collections/entities.html',
        {'collection': collection,
         'paginator': paginator,
         'page': page,
         'thispage': thispage,},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def changelog( request, cid ):
    collection = Collection.from_identifier(Identifier(cid))
    alert_if_conflicted(request, collection)
    return render_to_response(
        'webui/collections/changelog.html',
        {'collection': collection,},
        context_instance=RequestContext(request, processors=[])
    )

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
    return render_to_response(
        'webui/collections/git-status.html',
        {'collection': collection,
         'status': gitstatus.get('status', 'git-status unavailable'),
         'astatus': gitstatus.get('annex_status', 'annex-status unavailable'),
         'timestamp': gitstatus.get('timestamp'),
         'remotes': remotes,
         },
        context_instance=RequestContext(request, processors=[])
    )

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
            result = tasks.collection_sync.apply_async(
                (git_name,git_mail,collection.path),
                countdown=2
            )
            lockstatus = collection.lock(result.task_id)
            # add celery task_id to session
            celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
            # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
            task = {'task_id': result.task_id,
                    'action': 'webui-collection-sync',
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
    return render_to_response(
        'webui/collections/sync-confirm.html',
        {'collection': collection,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def new( request, oid ):
    """Redirect to new_idservice or new_manual.
    """
    if settings.IDSERVICE_API_BASE:
        return HttpResponseRedirect(reverse('webui-collection-newidservice', args=[oid]))
    return HttpResponseRedirect(reverse('webui-collection-newmanual', args=[oid]))

def _create_collection(request, cidentifier, git_name, git_mail):
    """used by both new_idservice and new_manual
    """
    exit,status = Collection.new(cidentifier, git_name, git_mail, settings.AGENT)
    collection = Collection.from_identifier(cidentifier)
    if exit:
        logger.error(exit)
        logger.error(status)
        messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
    else:
        # update search index
        try:
            collection.post_json()
        except ConnectionError:
            logger.error('Could not post to Elasticsearch.')
        tasks.gitstatus_update.apply_async(
            (cidentifier.path_abs(),),
            countdown=2
        )
    return collection

@ddrview
@login_required
@storage_required
def new_idservice( request, oid ):
    """Gets new CID from workbench, creates new collection record.
    
    If it messes up, goes back to collection list.
    """
    parent = Identifier(oid)
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not (git_name and git_mail):
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    
    ic = idservice_resume(request)
    # get new collection ID (dont register just get!)
    http_status,http_reason,next_id = ic.next_object_id(
        parent,
        model='collection',
        register=False
    )
    # quit if can't get an ID
    if (http_status not in [200,201]) or (not next_id):
        logger.error('%s %s' % (http_status, http_reason))
        messages.error(
            request,
            'Did not get new ID from ID service! (%s)' % (
                settings.IDSERVICE_API_BASE))
        return HttpResponseRedirect(reverse('webui-collections'))
    next_identifier = Identifier(next_id)

    # confirm collection not already present in filesystem or Gitolite
    g = dvcs.Gitolite()
    g.initialize()
    results = Collection.exists(
        next_identifier,
        basepath=next_identifier.path_abs(),
        gitolite=g,
        idservice=None
    )
    # quit if exists
    exists = False
    if results.get('filesystem'):
        messages.error(request, 'Collection %s already present in filesystem!' % next_id)
        exists = True
    if results.get('idservice'):
        messages.error(request, 'Collection %s already exists in the ID service! (%s)' % (next_id, settings.IDSERVICE_API_BASE))
        exists = True
    if results.get('gitolite'):
        messages.error(request, 'Collection %s repository already exists on remote server! (%s)' % (next_id, settings.GITOLITE))
        exists = True
    if exists:
        return HttpResponseRedirect(reverse('webui-collections'))
    
    # register new ID
    # TODO should be ic.register_id!!! >:-O
    http_status,http_reason,new_id = ic.next_object_id(
        parent,
        model='collection',
        register=True
    )
    if (http_status not in [200,201]) or (not new_id):
        logger.error('%s %s' % (http_status, http_reason))
        messages.error(
            request,
            'Could not register new ID with ID service! (%s)' % (
                settings.IDSERVICE_API_BASE))
        return HttpResponseRedirect(reverse('webui-collections'))
    new_identifier = Identifier(new_id)

    # Create collection and redirect to edit page
    collection = _create_collection(request, new_identifier, git_name, git_mail)
    if collection:
        return HttpResponseRedirect( reverse('webui-collection-edit', args=[collection.id]) )
    
    # something happened...
    logger.error('Could not create new collecion!')
    messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_ERR_CREATE'])
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
    
    parent = Identifier(oid).object()
    
    if request.method == 'POST':
        form = ObjectIDForm(
            request.POST,
            request=request,
            checks='fgi'  # filesystem, gitolite, idservice
        )
        if form.is_valid():
            
            # TODO get this from Entity class or something
            cid = form.cleaned_data['object_id']
            cidentifier = Identifier(id=cid)
            # Create collection and redirect to edit page
            collection = _create_collection(
                request,
                cidentifier,
                git_name, git_mail
            )
            if collection:
                messages.warning(
                    request,
                    'IMPORTANT: Register this ID with the ID service as soon as possible!'
                )
                return HttpResponseRedirect(
                    reverse('webui-collection-edit', args=[collection.id])
                )
            
    else:
        form = ObjectIDForm(
            initial={
                'model': 'collection',
                'parent_id': parent.id,
            },
            request=request,
            checks='fgi'  # filesystem, gitolite, idservice
        )

    # existing ids -----------------------
    # filesystem
    idparts = parent.idparts
    local_ids = [
        os.path.basename(cpath)
        for cpath in Collection.collection_paths(
            settings.MEDIA_BASE,
            idparts['repo'],
            idparts['org']
        )
    ]
    
    # Gitolite
    gitolite_ids = []
    if settings.GITOLITE:
        g = dvcs.Gitolite(server=settings.GITOLITE)
        g.initialize()
        gitolite_ids = [
            cid for cid in g.collections() if (parent.id in cid)
        ]
    
    # ID service
    idservice_ids = []
    if settings.IDSERVICE_API_BASE:
        status,msg,idservice_ids_raw = idservice.IDServiceClient().child_ids(parent.id)
        idservice_ids = []
        for oid in idservice_ids_raw:
            try:
                oi = identifier.Identifier(id=oi)
            except:
                oi = None
            if oi and (oi.model == 'collection'):
                idservice_ids.append(oi)
    
    existing_ids = util.natural_sort(
        list(set(local_ids + gitolite_ids + idservice_ids))
    )
    existing_ids.reverse()
    
    return render_to_response(
        'webui/collections/new-manual.html',
        {
            'form': form,
            'existing_ids': existing_ids,
            'local_ids': local_ids,
        },
        context_instance=RequestContext(request, processors=[])
    )

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
            tasks.collection_edit(
                request,
                collection, form.cleaned_data,
                git_name, git_mail
            )
            
            return HttpResponseRedirect(collection.absolute_url())
        
    else:
        form = DDRForm(collection.form_prep(), fields=module.FIELDS)
    return render_to_response(
        'webui/collections/edit-json.html',
        {'collection': collection,
         'form': form,
         },
        context_instance=RequestContext(request, processors=[])
    )

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
            
            result = tasks.collection_signatures.apply_async(
                (collection.path,git_name,git_mail),
                countdown=2
            )
            lockstatus = collection.lock(result.task_id)
            # add celery task_id to session
            celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
            # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
            task = {
                'task_id': result.task_id,
                'action': 'webui-collection-signatures',
                'collection_id': collection.id,
                'collection_url': collection.absolute_url(),
                'start': converters.datetime_to_text(datetime.now(settings.TZ)),
            }
            celery_tasks[result.task_id] = task
            request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
            return HttpResponseRedirect(collection.absolute_url())
        
    else:
        form = SignaturesConfirmForm()
    return render_to_response(
        'webui/collections/signatures-confirm.html',
        {
            'collection': collection,
            'form': form,
        },
        context_instance=RequestContext(request, processors=[])
    )
 
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
    result = tasks.csv_export_model.apply_async(
        (collection.path,model),
        countdown=2
    )
    # add celery task_id to session
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
    task = {'task_id': result.task_id,
            'action': 'webui-csv-export-model',
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
