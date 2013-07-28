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
from ddrlocal.models.file import DDRFile, FILEMETA_BLANK
from storage.decorators import storage_required
from webui.forms.files import NewFileForm, EditFileForm, shared_folder_files
from webui.tasks import entity_add_file
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
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, 'Login is required')
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    if entity.locked():
        messages.error(request, 'This entity is locked.')
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    #
    if request.method == 'POST':
        form = NewFileForm(request.POST, request.FILES)
        if form.is_valid():
            src_path = form.cleaned_data['path']
            role = form.cleaned_data['role']
            sort = form.cleaned_data['sort']
            label = form.cleaned_data['label']
            result = entity_add_file.apply_async(
                (git_name, git_mail, entity, src_path, role, sort, label),
                countdown=2)
            entity.files_log(1,'------------------------------------------------------------------------')
            entity.files_log(1,'ddrlocal.webui.file.new: START')
            entity.files_log(1,'task_id: %s' % result.task_id)
            entity.files_log(1,'Locking')
            lockstatus = entity.lock(result.task_id)
            if lockstatus == 'ok':
                entity.files_log(1, 'locked')
            else:
                entity.files_log(0, lockstatus)
            messages.success(request, 'Uploading <b>%s</b> (%s)' % (os.path.basename(src_path), result))
            return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    else:
        data = {'role':role,
                'sort': FILEMETA_BLANK['sort'],
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
def batch( request, repo, org, cid, eid, role='master' ):
    """Add multiple files to entity.
    """
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    if entity.locked():
        messages.error(request, 'This entity is locked.')
        return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
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
    if entity.locked():
        messages.error(request, "This file's parent entity is locked.")
        return HttpResponseRedirect( f.url() )
    if request.method == 'POST':
        form = EditFileForm(request.POST, request.FILES)
        if form.is_valid():
            #f.status = form.cleaned_data['status']
            #f.public = form.cleaned_data['public']
            f.sort = form.cleaned_data['sort']
            f.role = form.cleaned_data['role']
            f.label = form.cleaned_data['label']
            f.xmp = form.cleaned_data['xmp']
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
            #'status': f.status,
            #'public': f.public,
            'role': f.role,
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
