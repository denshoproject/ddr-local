from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
import sys

from bs4 import BeautifulSoup

from django.conf import settings
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.files import File
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from DDR.ingest import addfile_logger
from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui.decorators import ddrview
from webui.forms import DDRForm
from webui.forms.files import NewFileDDRForm, NewAccessFileForm, DeleteFileForm
from webui.forms.files import shared_folder_files
from webui.models import Stub, Collection, Entity, DDRFile
from webui.models import MODULES
from webui.identifier import Identifier, CHILDREN_ALL
from webui.tasks import entity_add_file, entity_add_access
from webui.tasks import entity_file_edit, entity_delete_file
from webui.tasks import gitstatus_update
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

def prep_newfile_form_fields(FIELDS):
    """
    - path field is needed even though it's not in the model
    """
    path = {
        'name':       'path',
        'group':      '',
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'max_length': 255,
            'widget':     'HiddenInput',
            'initial':    '',
            'required':   True,
        },
        'default':    '',
    }
    FIELDS.insert(0, path)
    return FIELDS


# views ----------------------------------------------------------------

@storage_required
def detail( request, fid ):
    """Add file to entity.
    """
    file_ = DDRFile.from_identifier(Identifier(fid))
    entity = file_.parent()
    collection = file_.collection()
    file_.model_def_commits()
    file_.model_def_fields()
    formdata = {'path':file_.path_rel}
    return render_to_response(
        'webui/files/detail.html',
        {'collection': collection,
         'entity': entity,
         'role': file_.identifier.parts['role'],
         'file': file_,
         'new_access_url': file_.new_access_url,
         'new_access_form': NewAccessFileForm(formdata),},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def browse( request, rid ):
    """Browse for a file in vbox shared folder.
    """
    file_role = Stub.from_identifier(Identifier(rid))
    role = file_role.identifier.parts['role']
    entity = file_role.parent(stubs=True)
    collection = entity.collection()
    path = request.GET.get('path')
    home = None
    parent = None
    if path:
        path_abs = os.path.join(settings.VIRTUALBOX_SHARED_FOLDER, path)
        parent = os.path.dirname(path)
        home = settings.VIRTUALBOX_SHARED_FOLDER
    else:
        path_abs = settings.VIRTUALBOX_SHARED_FOLDER
    listdir = []
    if os.path.exists(path_abs):
        for x in os.listdir(path_abs):
            xabs = os.path.join(path_abs, x)
            rel = xabs.replace(settings.VIRTUALBOX_SHARED_FOLDER, '')
            if rel and rel[0] == '/':
                rel = rel[1:]
            isdir = os.path.isdir(xabs)
            if isdir:
                x = '%s/' % x
            mtime = datetime.fromtimestamp(os.path.getmtime(xabs))
            size = None
            if not isdir:
                size = os.path.getsize(xabs)
            attribs = {'basename':x, 'rel':rel, 'path':xabs, 'isdir':isdir, 'size':size, 'mtime':mtime}
            if os.path.exists(xabs):
                listdir.append(attribs)
    return render_to_response(
        'webui/files/browse.html',
        {'collection': collection,
         'entity': entity,
         'file_role': file_role,
         'new_file_url': entity.new_file_url(role),
         'shared_folder': settings.VIRTUALBOX_SHARED_FOLDER,
         'listdir': listdir,
         'parent': parent,
         'home': home,},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def new( request, rid ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    file_role = Stub.from_identifier(Identifier(rid))
    role = file_role.identifier.parts['role']
    #child_models = CHILDREN_ALL[file_role.identifier.model]
    FILE_MODEL = 'file'
    module = MODULES[FILE_MODEL]
    entity = file_role.parent(stubs=True)
    collection = entity.collection()
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect(entity.absolute_url())
    #
    path = request.GET.get('path', None)
    FIELDS = prep_newfile_form_fields(module.FIELDS_NEW)
    if request.method == 'POST':
        form = NewFileDDRForm(request.POST, fields=FIELDS, path_choices=shared_folder_files())
        if form.is_valid():
            data = form.cleaned_data
            src_path = path
            # inheritable fields
            inherited = []
            for field in entity.inheritable_fields():
                inherited.append( (field,getattr(entity,field)) )
            # start tasks
            result = entity_add_file.apply_async(
                (git_name, git_mail, entity, src_path, role, data, settings.AGENT),
                countdown=2)
            result_dict = result.__dict__
            log = addfile_logger(entity.identifier)
            log.ok('START task_id %s' % result.task_id)
            log.ok('ddrlocal.webui.file.new')
            log.ok('Locking %s' % entity.id)
            # lock entity
            lockstatus = entity.lock(result.task_id)
            if lockstatus == 'ok':
                log.ok('locked')
            else:
                log.not_ok(lockstatus)
            
            # add celery task_id to session
            celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
            # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
            task = {'task_id': result.task_id,
                    'action': 'webui-file-new-%s' % role,
                    'filename': os.path.basename(src_path),
                    'entity_id': entity.id,
                    'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
            celery_tasks[result.task_id] = task
            #del request.session[settings.CELERY_TASKS_SESSION_KEY]
            request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
            
            # feedback
#            messages.success(request, WEBUI_MESSAGES['VIEWS_FILES_UPLOADING'] % (os.path.basename(src_path), result))
            # redirect to entity
        return HttpResponseRedirect(entity.absolute_url())
    else:
        if not path:
            messages.error(request, 'specify a path')
        data = {'path': path,
                'role':role,
                'sort': 1,
                'label': '',}
        # inheritable fields
        for field in entity.inheritable_fields():
            data[field] = getattr(entity, field)
        form = NewFileDDRForm(data, fields=FIELDS, path_choices=shared_folder_files())
    return render_to_response(
        'webui/files/new.html',
        {'collection': collection,
         'entity': entity,
         'file_role': file_role,
         'form': form,
         'path': path,},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def new_access( request, fid ):
    """Generate a new access file for the specified file.
    
    NOTE: There is no GET for this view.  GET requests will redirect to entity.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    file_ = DDRFile.from_identifier(Identifier(fid))
    entity = file_.parent()
    collection = file_.collection()
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())
    collection.repo_fetch()
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect(entity.absolute_url())
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
            log = addfile_logger(entity.identifier)
            log.ok('START task_id %s' % result.task_id)
            log.ok('ddrlocal.webui.file.new_access')
            log.ok('Locking %s' % entity.id)
            # lock entity
            lockstatus = entity.lock(result.task_id)
            if lockstatus == 'ok':
                log.ok( 'locked')
            else:
                log.not_ok( lockstatus)
            # add celery task_id to session
            celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
            # IMPORTANT: 'action' *must* match a message in webui.tasks.TASK_STATUS_MESSAGES.
            task = {'task_id': result.task_id,
                    'action': 'webui-file-new-access',
                    'filename': os.path.basename(src_path),
                    'file_url': file_.absolute_url(),
                    'entity_id': entity.id,
                    'start': datetime.now().strftime(settings.TIMESTAMP_FORMAT),}
            celery_tasks[result.task_id] = task
            #del request.session[settings.CELERY_TASKS_SESSION_KEY]
            request.session[settings.CELERY_TASKS_SESSION_KEY] = celery_tasks
            # feedback
            #messages.success(request, WEBUI_MESSAGES['VIEWS_FILES_NEWACCESS'] % os.path.basename(src_path))
    # redirect to entity
    return HttpResponseRedirect(entity.absolute_url())

@ddrview
@login_required
@storage_required
def batch( request, rid ):
    """Add multiple files to entity.
    """
    file_role = Stub.from_identifier(Identifier(rid))
    entity = Entity.from_request(request)
    collection = entity.collection()
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())
    collection.repo_fetch()
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect(entity.absolute_url())
    return render_to_response(
        'webui/files/new.html',
        {'collection': collection,
         'entity': entity,},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def edit( request, fid ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    file_ = DDRFile.from_identifier(Identifier(fid))
    module = file_.identifier.fields_module()
    entity = file_.parent()
    collection = file_.collection()
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())
    collection.repo_fetch()
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect(entity.absolute_url())
    file_.model_def_commits()
    file_.model_def_fields()
    #
    if request.method == 'POST':
        form = DDRForm(request.POST, fields=module.FIELDS)
        if form.is_valid():
            
            file_.form_post(form)
            # write these so we see a change on refresh
            # will be rewritten in file_.save()
            file_.write_json()
            
            # commit files, delete cache, update search index, update git status
            entity_file_edit(request, collection, file_, git_name, git_mail)
            
            return HttpResponseRedirect( file_.absolute_url() )
            
    else:
        form = DDRForm(file_.form_prep(), fields=module.FIELDS)
    return render_to_response(
        'webui/files/edit-json.html',
        {'collection': collection,
         'entity': entity,
         'role': file_.identifier.parts['role'],
         'file': file_,
         'form': form,
         },
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
@login_required
@storage_required
def delete( request, fid ):
    try:
        file_ = DDRFile.from_identifier(Identifier(fid))
        entity = file_.parent()
        collection = file_.collection()
    except:
        raise Http404
    if entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect(entity.absolute_url())
    if collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    #
    if request.method == 'POST':
        form = DeleteFileForm(request.POST)
        if form.is_valid() and form.cleaned_data['confirmed']:
            entity_delete_file(request, git_name, git_mail, collection, entity, file_, settings.AGENT)
            return HttpResponseRedirect(collection.absolute_url())
    else:
        form = DeleteFileForm()
    return render_to_response(
        'webui/files/delete.html',
        {'file': file_,
         'role': file_.identifier.parts['role'],
         'form': form,
         },
        context_instance=RequestContext(request, processors=[])
    )
