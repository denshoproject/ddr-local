from datetime import datetime
import json
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

from DDR import commands
from ddrlocal.models import DDRLocalCollection as Collection
from ddrlocal.models import DDRLocalEntity as Entity
from ddrlocal.models import DDRFile
from ddrlocal.forms import FileForm

from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui.forms.files import NewFileForm, EditFileForm, NewAccessFileForm, shared_folder_files
from webui.tasks import entity_add_file, entity_add_access
from webui.views.decorators import login_required


# helpers --------------------------------------------------------------

def handle_uploaded_file(f, dest_dir):
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    print('dest_dir {}'.format(dest_dir))
    dest_path_abs = os.path.join(dest_dir, f.name)
    print('dest_path_abs {}'.format(dest_path_abs))
    with open(dest_path_abs, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    print('destination {}'.format(destination))
    return dest_path_abs



# views ----------------------------------------------------------------

@login_required
@storage_required
def detail( request, repo, org, cid, eid, role, sha1 ):
    """Add file to entity.
    """
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    file_ = entity.file(repo, org, cid, eid, role, sha1)
    formdata = {'path':file_.path_rel}
    return render_to_response(
        'webui/files/detail.html',
        {'repo': file_.repo,
         'org': file_.org,
         'cid': file_.cid,
         'eid': file_.eid,
         'role': file_.role,
         'sha1': file_.sha1,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,
         'file': file_,
         'new_access_form': NewAccessFileForm(formdata),},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def json( request, repo, org, cid, eid, role, sha1 ):
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    file_ = entity.file(repo, org, cid, eid, role, sha1)
    if file_.json_path and os.path.exists(file_.json_path):
        with open(file_.json_path, 'r') as f:
            json = f.read()
        return HttpResponse(json, mimetype="application/json")
    messages.success(request, 'no JSON file. sorry.')
    return HttpResponseRedirect( reverse('webui-file', args=[repo,org,cid,eid,role,sha1]) )

@login_required
@storage_required
def new( request, repo, org, cid, eid, role='master' ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    #
    if request.method == 'POST':
        form = NewFileForm(request.POST, path_choices=shared_folder_files())
        if form.is_valid():
            src_path = form.cleaned_data['path']
            role = form.cleaned_data['role']
            sort = form.cleaned_data['sort']
            label = form.cleaned_data['label']
            # start tasks
            result = entity_add_file.apply_async(
                (git_name, git_mail, entity, src_path, role, sort, label),
                countdown=2)
            entity.files_log(1,'START task_id %s' % result.task_id)
            entity.files_log(1,'ddrlocal.webui.file.new')
            entity.files_log(1,'Locking %s' % entity.id)
            # lock entity
            lockstatus = entity.lock(result.task_id)
            if lockstatus == 'ok':
                entity.files_log(1, 'locked')
            else:
                entity.files_log(0, lockstatus)
            

            # add celery task_id to session
            celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
            # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
            task = {'task_id': result.task_id,
                    'action': 'webui-file-new-%s' % role,
                    'filename': os.path.basename(src_path),
                    'entity_id': entity.id,
                    'start': datetime.now(),}
            celery_tasks[result.task_id] = task
            #del request.session[settings.CELERY_TASKS_SESSION_KEY]
            request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
            
            # feedback
            messages.success(request, WEBUI_MESSAGES['VIEWS_FILES_UPLOADING'] % (os.path.basename(src_path), result))
            # redirect to entity
            return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    else:
        data = {'role':role,
                'sort': 1,
                'label': '',}
        form = NewFileForm(data, path_choices=shared_folder_files())
    return render_to_response(
        'webui/files/new.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

@login_required
@storage_required
def new_access( request, repo, org, cid, eid, role, sha1 ):
    """Generate a new access file for the specified file.
    
    NOTE: There is no GET for this view.  GET requests will redirect to entity.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    file_ = entity.file(repo, org, cid, eid, role, sha1)
    #
    if request.method == 'POST':
        form = NewAccessFileForm(request.POST)
        if form.is_valid():
            src_path = form.cleaned_data['path']
            # start tasks
            result = entity_add_access.apply_async(
                (git_name, git_mail, entity, file_),
                countdown=2)
            result_dict = result.__dict__
            entity.files_log(1,'START task_id %s' % result.task_id)
            entity.files_log(1,'ddrlocal.webui.file.new_access')
            entity.files_log(1,'Locking %s' % entity.id)
            # lock entity
            lockstatus = entity.lock(result.task_id)
            if lockstatus == 'ok':
                entity.files_log(1, 'locked')
            else:
                entity.files_log(0, lockstatus)
            # add celery task_id to session
            celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
            # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
            task = {'task_id': result.task_id,
                    'action': 'webui-file-new-access',
                    'filename': os.path.basename(src_path),
                    'entity_id': entity.id,
                    'start': datetime.now(),}
            celery_tasks[result.task_id] = task
            #del request.session[settings.CELERY_TASKS_SESSION_KEY]
            request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
            # feedback
            messages.success(request, WEBUI_MESSAGES['VIEWS_FILES_NEWACCESS'] % os.path.basename(src_path))
    # redirect to entity
    return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )

@login_required
@storage_required
def batch( request, repo, org, cid, eid, role='master' ):
    """Add multiple files to entity.
    """
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    return render_to_response(
        'webui/files/new.html',
        {'collection': collection,
         'entity': entity,},
        context_instance=RequestContext(request, processors=[])
    )

@login_required
@storage_required
def edit( request, repo, org, cid, eid, role, sha1 ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    file_ = entity.file(repo, org, cid, eid, role, sha1)
    #
    if request.method == 'POST':
        form = FileForm(request.POST)
        if form.is_valid():
            file_.form_post(form)
            file_.dump_json()
            exit,status = commands.entity_update(git_name, git_mail,
                                                 entity.parent_path, entity.id,
                                                 [file_.json_path,])
            if exit:
                messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
            else:
                messages.success(request, WEBUI_MESSAGES['VIEWS_FILES_UPDATED'])
                return HttpResponseRedirect( reverse('webui-file', args=[repo,org,cid,eid,role,sha1]) )
            # something went wrong
            assert False
    else:
        form = FileForm(file_.form_prep())
    return render_to_response(
        'webui/files/edit-json.html',
        {'repo': file_.repo,
         'org': file_.org,
         'cid': file_.cid,
         'eid': file_.eid,
         'collection': collection,
         'entity': entity,
         'file': file_,
         'form': form,
         },
        context_instance=RequestContext(request, processors=[])
    )

@login_required
@storage_required
def edit_old( request, repo, org, cid, eid, role, sha1 ):
    """Edit file metadata
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    f = entity.file(repo, org, cid, eid, role, sha1)
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect( f.url() )
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_FILES_PARENT_LOCKED'])
        return HttpResponseRedirect( f.url() )
    if request.method == 'POST':
        form = EditFileForm(request.POST, request.FILES)
        if form.is_valid():
            #f.status = form.cleaned_data['status']
            #f.public = form.cleaned_data['public']
            f.sort = form.cleaned_data['sort']
            f.label = form.cleaned_data['label']
            f.xmp = form.cleaned_data['xmp']
            result = entity.file(repo, org, cid, eid, role, sha1, f)
            if result in ['added','updated']:
                entity.dump_json()
                entity.dump_mets()
                exit,status = commands.entity_update(git_name, git_mail,
                                                     entity.parent_path, entity.id,
                                                     [entity.json_path, entity.mets_path,])
                if exit:
                    messages.error(request, WEBUI_MESSAGES['ERROR'].format(status))
                else:
                    messages.success(request, WEBUI_MESSAGES['VIEWS_FILES_UPDATED'])
                    return HttpResponseRedirect( reverse('webui-file', args=[repo,org,cid,eid,role,sha1]) )
            # something went wrong
            assert False
    else:
        data = {
            #'status': f.status,
            #'public': f.public,
            'sort': f.sort,
            'label': f.label,
            'xmp': f.xmp,
            }
        form = EditFileForm(data)
    return render_to_response(
        'webui/files/edit.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,
         'file': f,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )
