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
from ddrlocal.models.collection import DDRLocalCollection as Collection
from ddrlocal.models.entity import DDRLocalEntity as Entity
from ddrlocal.models.file import DDRFile
from storage.decorators import storage_required
from webui.forms.files import NewFileForm, EditFileForm
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
def detail( request, repo, org, cid, eid, sha1 ):
    """Add file to entity.
    """
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    return render_to_response(
        'webui/files/detail.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,
         'file': entity.file(sha1)},
        context_instance=RequestContext(request, processors=[])
    )

@login_required
@storage_required
def new( request, repo, org, cid, eid, role='master' ):
    """Add file to entity
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, 'Login is required')
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    #
    if request.method == 'POST':
        form = NewFileForm(request.POST, request.FILES)
        if form.is_valid():
            role = form.cleaned_data['role']
            src_path = form.cleaned_data['path']
            # complain
            src_exists = os.path.exists(src_path)
            src_is_readable = os.access(src_path, os.R_OK)
            dest = entity.files_path
            dest_exists = os.path.exists(dest)
            dest_is_writable = os.access(dest, os.W_OK)
            if not src_exists:       messages.error(request, 'Source file does not exist: {}'.format(src))
            if not src_is_readable:  messages.error(request, 'Source file not readable: {}'.format(src))
            if not dest_exists:      messages.error(request, 'Destination directory does not exist: {}'.format(dest))
            if not dest_is_writable: messages.error(request, 'Destination directory not writable: {}'.format(dest))
            # do, or do not
            if src_exists and src_is_readable and dest_exists and dest_is_writable:
                dest_name = DDRFile.file_name(entity, src_path)
                dest_path = os.path.join(dest, dest_name)
                assert False
                # write file to entity files dir
                file_abs = handle_uploaded_file(request.FILES['file'], entity.files_path)
                file_rel = os.path.basename(file_abs)
                
                exit,status = commands.entity_annex_add(git_name, git_mail,
                                                        entity.parent_path,
                                                        entity.id, file_rel)
                if exit:
                    messages.error(request, 'Error: {}'.format(status))
                else:
                    messages.success(request, 'New file added: {}'.format(status))
                    return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    else:
        data = {'role':role,}
        form = NewFileForm(data)
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
def batch( request, repo, org, cid, eid, role='master' ):
    """Add multiple files to entity.
    """
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    return render_to_response(
        'webui/files/new.html',
        {'collection': collection,
         'entity': entity,},
        context_instance=RequestContext(request, processors=[])
    )

@login_required
@storage_required
def edit( request, repo, org, cid, eid, sha1 ):
    """Edit file metadata
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, 'Login is required')
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    f = entity.file(sha1)
    if request.method == 'POST':
        form = EditFileForm(request.POST, request.FILES)
        if form.is_valid():
            #f.status = form.cleaned_data['status']
            #f.public = form.cleaned_data['public']
            f.sort = form.cleaned_data['sort']
            f.role = form.cleaned_data['role']
            f.label = form.cleaned_data['label']
            f.exif = form.cleaned_data['exif']
            result = entity.file(sha1, f)
            if result in ['added','updated']:
                entity.dump_json()
                entity.dump_mets()
                exit,status = commands.entity_update(git_name, git_mail,
                                                     entity.parent_path, entity.id,
                                                     [entity.json_path, entity.mets_path,])
                if exit:
                    messages.error(request, 'Error: {}'.format(status))
                else:
                    messages.success(request, 'File metadata updated')
                    return HttpResponseRedirect( reverse('webui-file', args=[repo,org,cid,eid,sha1]) )
            # something went wrong
            assert False
    else:
        data = {
            'status': f.status,
            'public': f.public,
            'sort': f.sort,
            'role': f.role,
            'label': f.label,
            'exif': f.exif,
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
