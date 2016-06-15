from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
import random
import sys

from bs4 import BeautifulSoup

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
from DDR import docstore
from DDR import dvcs
from DDR import fileio
from DDR import idservice

from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui.decorators import ddrview, search_index
from webui.forms import DDRForm
from webui.forms.collections import NewCollectionForm, UpdateForm, SyncConfirmForm
from webui import gitolite
from webui.models import Collection, COLLECTION_STATUS_CACHE_KEY, COLLECTION_STATUS_TIMEOUT
from webui.identifier import Identifier
from webui.tasks import collection_new_expert, collection_edit, collection_sync
from webui.tasks import csv_export_model, export_csv_path, gitstatus_update
from webui.views.decorators import login_required


# helpers --------------------------------------------------------------

def alert_if_conflicted(request, collection):
    if collection.repo_conflicted():
        url = reverse('webui-merge', args=collection.idparts)
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
        collections.append( (object_id,repo,org,colls) )
    # load statuses in random order
    random.shuffle(collection_status_urls)
    return render_to_response(
        'webui/collections/index.html',
        {'collections': collections,
         'collection_status_urls': ', '.join(collection_status_urls),},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def detail( request, repo, org, cid ):
    collection = Collection.from_request(request)
    collection.model_def_commits()
    collection.model_def_fields()
    alert_if_conflicted(request, collection)
    return render_to_response(
        'webui/collections/detail.html',
        {'collection': collection,
         'collection_unlock_url': collection.unlock_url(collection.locked()),},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def children( request, repo, org, cid ):
    collection = Collection.from_request(request)
    alert_if_conflicted(request, collection)
    objects = collection.children(quick=True)
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
def changelog( request, repo, org, cid ):
    collection = Collection.from_request(request)
    alert_if_conflicted(request, collection)
    return render_to_response(
        'webui/collections/changelog.html',
        {'collection': collection,},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@storage_required
def sync_status_ajax( request, repo, org, cid ):
    collection = Collection.from_request(request)
    gitstatus = collection.gitstatus()
    if gitstatus:
        sync_status = gitstatus['sync_status']
        if sync_status.get('timestamp',None):
            sync_status['timestamp'] = sync_status['timestamp'].strftime(settings.TIMESTAMP_FORMAT)
        return HttpResponse(json.dumps(sync_status), content_type="application/json")
    raise Http404

@ddrview
@storage_required
def git_status( request, repo, org, cid ):
    collection = Collection.from_request(request)
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
def sync( request, repo, org, cid ):
    try:
        collection = Collection.from_request(request)
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
            result = collection_sync.apply_async( (git_name,git_mail,collection.path), countdown=2)
            lockstatus = collection.lock(result.task_id)
            # add celery task_id to session
            celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
            # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
            task = {'task_id': result.task_id,
                    'action': 'webui-collection-sync',
                    'collection_id': collection.id,
                    'collection_url': collection.absolute_url(),
                    'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
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
def new( request, repo, org ):
    """Gets new CID from workbench, creates new collection record.
    
    If it messes up, goes back to collection list.
    """
    oidentifier = Identifier(request)
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not (git_name and git_mail):
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    
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
        return HttpResponseRedirect(reverse('webui-collections'))
    # get new collection ID
    http_status,http_reason,collection_id = ic.next_object_id(
        oidentifier,
        'collection'
    )
    if http_status not in [200,201]:
        err = '%s %s' % (http_status, http_reason)
        msg = WEBUI_MESSAGES['VIEWS_COLL_ERR_NO_IDS'] % (settings.IDSERVICE_API_BASE, err)
        logger.error(msg)
        messages.error(request, msg)
        return HttpResponseRedirect(reverse('webui-collections'))
    
    identifier = Identifier(id=collection_id, base_path=settings.MEDIA_BASE)
    # create the new collection repo
    collection_path = identifier.path_abs()
    # collection.json template
    fileio.write_text(
        Collection(collection_path).dump_json(template=True),
        settings.TEMPLATE_CJSON
    )
    exit,status = commands.create(
        git_name, git_mail,
        identifier,
        [settings.TEMPLATE_CJSON, settings.TEMPLATE_EAD],
        agent=settings.AGENT
    )
    if exit:
        logger.error(exit)
        logger.error(status)
        messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
    else:
        # update search index
        collection = Collection.from_identifier(identifier)
        collection.post_json(settings.DOCSTORE_HOSTS, settings.DOCSTORE_INDEX)
        gitstatus_update.apply_async((collection_path,), countdown=2)
        # positive feedback
        return HttpResponseRedirect( reverse('webui-collection-edit', args=collection.idparts) )
    # something happened...
    logger.error('Could not create new collecion!')
    messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_ERR_CREATE'])
    return HttpResponseRedirect(reverse('webui-collections'))

@ddrview
@login_required
@storage_required
def newexpert( request, repo, org ):
    """Ask for Entity ID, then create new Entity.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    
    if request.method == 'POST':
        form = NewCollectionForm(request.POST)
        if form.is_valid():

            idparts = {
                'model':'collection',
                'repo':repo, 'org':org,
                'cid':str(form.cleaned_data['cid'])
            }
            identifier = Identifier(parts=idparts)
            collection_id = identifier.id
            collection_ids = [
                os.path.basename(cpath)
                for cpath
                in Collection.collection_paths(settings.MEDIA_BASE, repo, org)
            ]
            already_exists = False
            if collection_id in collection_ids:
                already_exists = True
                messages.error(request, "That collection ID already exists. Try again.")
            
            if collection_id and not already_exists:
                collection_new_expert(
                    request,
                    settings.MEDIA_BASE,
                    collection_id,
                    git_name, git_mail
                )
                return HttpResponseRedirect(reverse('webui-collections'))
            
    else:
        data = {
            'repo':repo,
            'org':org,
        }
        form = NewCollectionForm(data)
    return render_to_response(
        'webui/collections/new.html',
        {'form': form,
         },
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def edit( request, repo, org, cid ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_request(request)
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
            
            collection.form_post(form)
            collection.write_json()
            collection.write_ead()
            updated_files = [collection.json_path, collection.ead_path,]
            
            # if inheritable fields selected, propagate changes to child objects
            inheritables = collection.selected_inheritables(form.cleaned_data)
            modified_ids,modified_files = collection.update_inheritables(inheritables, form.cleaned_data)
            if modified_files:
                updated_files = updated_files + modified_files
            
            # commit files, delete cache, update search index, update git status
            collection_edit(request, collection, updated_files, git_name, git_mail)
            
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
 
@login_required
@storage_required
def csv_export( request, repo, org, cid, model=None ):
    """
    """
    if (not model) or (not (model in ['entity','file'])):
        raise Http404
    collection = Collection.from_request(request)
    things = {'entity':'objects', 'file':'files'}
    csv_path = export_csv_path(collection.path, model)
    csv_filename = os.path.basename(csv_path)
    if model == 'entity':
        file_url = reverse('webui-collection-csv-entities', args=collection.idparts)
    elif model == 'file':
        file_url = reverse('webui-collection-csv-files', args=collection.idparts)
    # do it
    result = csv_export_model.apply_async( (collection.path,model), countdown=2)
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
            'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
    celery_tasks[result.task_id] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
    return HttpResponseRedirect(collection.absolute_url())

@storage_required
def csv_download( request, repo, org, cid, model=None ):
    """Offers CSV file in settings.CSV_TMPDIR for download.
    
    File must actually exist in settings.CSV_TMPDIR and be readable.
    File must be readable by Python csv module.
    If all that is true then it must be a legal CSV file.
    """
    collection = Collection.from_request(request)
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
def unlock( request, repo, org, cid, task_id ):
    """Provides a way to remove collection lockfile through the web UI.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_request(request)
    if task_id and collection.locked() and (task_id == collection.locked()):
        collection.unlock(task_id)
        messages.success(request, 'Collection <b>%s</b> unlocked.' % collection.id)
    return HttpResponseRedirect(collection.absolute_url())
