from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, render

from storage.decorators import storage_required
from webui import WEBUI_MESSAGES
from webui.decorators import ddrview
from webui.forms import DDRForm
from webui.forms.files import NewFileDDRForm, NewExternalFileForm, NewAccessFileForm
from webui.forms.files import DeleteFileForm
from webui.forms.files import shared_folder_files
from webui.gitstatus import repository, annex_whereis_file
from webui.models import Stub, Entity, File
from webui.models import MODULES
from webui.identifier import Identifier
from webui.tasks import files as file_tasks
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

def enforce_git_credentials(request):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])

def check_file(file_):
    if not file_:
        raise Http404

def check_parents(entity, collection, check_locks=True, fetch=True):
    if not entity:
        raise Exception('No parent object!')
    if not collection:
        raise Exception('No parent collection!')
    if check_locks and entity.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_ENT_LOCKED'])
        return HttpResponseRedirect(entity.absolute_url())
    if check_locks and collection.locked():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_LOCKED'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())
    if fetch:
        collection.repo_fetch()
    if collection.repo_behind():
        messages.error(request, WEBUI_MESSAGES['VIEWS_COLL_BEHIND'].format(collection.id))
        return HttpResponseRedirect(entity.absolute_url())



# views ----------------------------------------------------------------

@storage_required
def detail( request, fid ):
    """Add file to entity.
    """
    file_ = File.from_identifier(Identifier(fid))
    check_file(file_)
    entity = file_.parent()
    collection = file_.collection()
    check_parents(entity, collection, check_locks=0, fetch=0)
    file_.model_def_commits()
    file_.model_def_fields()
    formdata = {'path':file_.path_rel}
    if settings.GIT_ANNEX_WHEREIS:
        annex_whereis = annex_whereis_file(repository(collection.path_abs), file_)
    else:
        annex_whereis = {}
    return render(request, 'webui/files/detail.html', {
        'collection': collection,
        'entity': entity,
        'role': file_.identifier.parts['role'],
        'file': file_,
        'new_access_url': file_.new_access_url,
        'new_access_form': NewAccessFileForm(formdata),
        'annex_whereis': annex_whereis,
    })

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
    check_parents(entity, collection, check_locks=0, fetch=0)
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
    return render(request, 'webui/files/browse.html', {
        'collection': collection,
        'entity': entity,
        'file_role': file_role,
        'new_file_url': entity.new_file_url(role),
        'shared_folder': settings.VIRTUALBOX_SHARED_FOLDER,
        'listdir': listdir,
        'parent': parent,
        'home': home,
    })

@ddrview
@login_required
@storage_required
def new( request, rid ):
    enforce_git_credentials(request)
    file_role = Stub.from_identifier(Identifier(rid))
    entity = file_role.parent(stubs=True)
    collection = entity.collection()
    check_parents(entity, collection, fetch=0)
    role = file_role.identifier.parts['role']
    #child_models = CHILDREN_ALL[file_role.identifier.model]
    FILE_MODEL = 'file'
    module = MODULES[FILE_MODEL]
    #
    path = request.GET.get('path', None)
    FIELDS = prep_newfile_form_fields(module.FIELDS_NEW)
    if request.method == 'POST':
        form = NewFileDDRForm(
            request.POST,
            fields=FIELDS,
            path_choices=shared_folder_files()
        )
        if form.is_valid():
            rowd = {
                'id': entity.id,
                'external': False,
                'role': role,
                'basename_orig': form.cleaned_data['path'],
                'public': form.cleaned_data['public'],
                'sort': form.cleaned_data['sort'],
                'label': form.cleaned_data['label'],
            }
            file_tasks.add_local(
                request, rowd, entity, role, path,
                request.session['git_name'], request.session['git_mail'],
            )
            
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
    return render(request, 'webui/files/new.html', {
        'collection': collection,
        'entity': entity,
        'file_role': file_role,
        'form': form,
        'path': path,
    })

@ddrview
@login_required
@storage_required
def new_external(request, rid):
    """Enter initial data for external file
    
    An external file is one that is external to the DDR collection.
    The hashes are known but the binary file itself is not present
    within the collection.
    """
    file_role = Stub.from_identifier(Identifier(rid))
    role = file_role.identifier.parts['role']
    entity = file_role.parent(stubs=True)
    collection = entity.collection()
    check_parents(entity, collection, check_locks=0, fetch=0)
    
    if request.method == 'POST':
        form = NewExternalFileForm(request.POST)
        if form.is_valid():
            rowd = {
                'id': entity.id,
                'external': True,
                'role': role,
                'basename_orig': form.cleaned_data['filename'],
                'sha1': form.cleaned_data['sha1'],
                'sha256': form.cleaned_data['sha256'],
                'md5': form.cleaned_data['md5'],
                'size': form.cleaned_data['size'],
                'mimetype': form.cleaned_data['mimetype'],
            }
            file_tasks.add_external(
                request, rowd, entity, file_role,
                request.session['git_name'], request.session['git_mail'],
            )
            
        return HttpResponseRedirect(entity.absolute_url())
            
    else:
        form = NewExternalFileForm()
    
    return render(request, 'webui/files/new-external.html', {
        'collection': collection,
        'entity': entity,
        'file_role': file_role,
        'form': form,
    })

@ddrview
@login_required
@storage_required
def new_access( request, fid ):
    """Generate a new access file for the specified file.
    
    NOTE: There is no GET for this view.  GET requests will redirect to entity.
    """
    enforce_git_credentials(request)
    file_ = File.from_identifier(Identifier(fid))
    check_file(file_)
    entity = file_.parent()
    collection = file_.collection()
    check_parents(entity, collection)
    #
    if request.method == 'POST':
        form = NewAccessFileForm(request.POST)
        if form.is_valid():
            file_tasks.add_access(
                request, form.cleaned_data,
                entity, file_,
                request.session['git_name'], request.session['git_mail'],
            )
    
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
    check_parents(entity, collection)
    return render(request, 'webui/files/new.html', {
        'collection': collection,
        'entity': entity,
    })

@ddrview
@login_required
@storage_required
def edit( request, fid ):
    enforce_git_credentials(request)
    file_ = File.from_identifier(Identifier(fid))
    check_file(file_)
    entity = file_.parent()
    collection = file_.collection()
    check_parents(entity, collection)
    file_.model_def_commits()
    file_.model_def_fields()
    module = file_.identifier.fields_module()
    #
    if request.method == 'POST':
        form = DDRForm(request.POST, fields=module.FIELDS)
        if form.is_valid():
            
            file_.form_post(form.cleaned_data)
            # write these so we see a change on refresh
            # will be rewritten in file_.save()
            file_.write_json()
            
            # commit files, delete cache, update search index, update git status
            file_tasks.edit(
                request,
                collection, file_, form.cleaned_data,
                request.session['git_name'], request.session['git_mail'],
            )
            
            return HttpResponseRedirect( file_.absolute_url() )
            
    else:
        form = DDRForm(file_.form_prep(), fields=module.FIELDS)
    return render(request, 'webui/files/edit-json.html', {
        'collection': collection,
        'entity': entity,
        'role': file_.identifier.parts['role'],
        'file': file_,
        'form': form,
    })

@ddrview
@login_required
@storage_required
def set_signature( request, fid ):
    """Make file the signature of the specified entity or collection.
    """
    enforce_git_credentials(request)
    file_ = File.from_identifier(Identifier(fid))
    check_file(file_)
    entity = file_.parent()
    collection = file_.collection()
    check_parents(entity, collection)
    #
    if request.method == 'POST':
        parent_id = request.POST.get('object_id')
        if parent_id in [entity.id, collection.id]:
            file_tasks.signature(
                request,
                parent_id=parent_id,
                file_id=fid,
                git_name=request.session['git_name'],
                git_mail=request.session['git_mail'],
            )
    return HttpResponseRedirect( file_.absolute_url() )

@storage_required
def xmp(request, fid):
    """View file XMP data.
    """
    file_ = File.from_identifier(Identifier(fid))
    check_file(file_)
    return HttpResponse(file_.xmp, content_type="application/xml")

@ddrview
@login_required
@storage_required
def delete( request, fid ):
    enforce_git_credentials(request)
    file_ = File.from_identifier(Identifier(fid))
    check_file(file_)
    entity = file_.parent()
    collection = file_.collection()
    check_parents(entity, collection)
    #
    if request.method == 'POST':
        form = DeleteFileForm(request.POST)
        if form.is_valid() and form.cleaned_data['confirmed']:
            file_tasks.delete(
                request,
                request.session['git_name'], request.session['git_mail'],
                collection, entity, file_,
                settings.AGENT
            )
            return HttpResponseRedirect(collection.absolute_url())
    else:
        form = DeleteFileForm()
    return render(request, 'webui/files/delete.html', {
        'file': file_,
        'role': file_.identifier.parts['role'],
        'form': form,
    })
