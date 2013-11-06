from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os

import git

from django.conf import settings
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import get_template

from DDR import commands, dvcs

from storage.decorators import storage_required
from webui.decorators import ddrview
from webui.models import Collection
from webui.views.decorators import login_required
from webui.forms.merge import MergeCommitForm, MergeRawForm, MergeJSONForm
from webui.merge import list_unmerged, merge_add, merge_commit, diverge_commit





"""
What we want to do:
list unmerged files
link to raw editor
for each file, edit and git-add

    ## fix what we can automagically
    #for filename in unmerged:
    #    if ('changelog' in filename) or ('.json' in filename):
    #        #url_name = 'webui-merge-json'
    #        url_name = 'webui-merge-raw'
    #    elif '.xml' in filename:
    #        url_name = 'webui-merge-auto'
    #    else:
    #        url_name = 'webui-merge-raw'
    #    revrse = reverse(url_name, args=[repo,org,cid])
    #    query = 'filename=%s' % filename
    #    url = '?'.join([revrse, query])
    #    return HttpResponseRedirect( url )

"""





def merge( request, repo, org, cid ):
    """
    Decides how to merge the various files in a merge conflict.
    Sends user around to different editors and things until everything is merged.
    """
    collection_path = Collection.collection_path(request,repo,org,cid)
    collection = Collection.from_json(collection_path)
    task_id = collection.locked()
    status = commands.status(collection_path)
    ahead = collection.repo_ahead()
    behind = collection.repo_behind()
    diverged = collection.repo_diverged()
    conflicted = collection.repo_conflicted()
    unmerged = list_unmerged(collection_path)
    staged = dvcs.list_staged(dvcs.repository(collection_path))
    if request.method == 'POST':
        form = MergeCommitForm(request.POST)
        if form.is_valid():
            which = form.cleaned_data['which']
            if which == 'merge':
                merge_commit(collection_path)
                committed = 1
            elif which == 'commit':
                diverge_commit(collection_path)
                committed = 1
            else:
                committed = 0
            if committed:
                if task_id:
                    collection.unlock(task_id)
                messages.error(request, 'Merge conflict has been resolved. Please sync to make your changes available to other users.')
                return HttpResponseRedirect( reverse('webui-collection', args=[repo,org,cid]) )
            return HttpResponseRedirect( reverse('webui-merge', args=[repo,org,cid]) )
    else:
        which = 'unknown'
        if conflicted and not unmerged:
            which = 'merge'
        elif diverged and staged:
            which = 'commit'
        form = MergeCommitForm({'path':collection_path, 'which':which,})
    return render_to_response(
        'webui/merge/index.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'collection_path': collection_path,
         'collection': collection,
         'status': status,
         'conflicted': conflicted,
         'ahead': ahead,
         'behind': behind,
         'unmerged': unmerged,
         'diverged': diverged,
         'staged': staged,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )


@ddrview
@login_required
@storage_required
def edit_auto( request, repo, org, cid ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection_path = Collection.collection_path(request,repo,org,cid)
    
    filename = request.GET.get('filename', None)
    filepath = os.path.join(collection_path, filename)
    with open(filepath, 'r') as f:
        text = f.read()
    merged = merge.automerge(text, 'left')
    with open(filepath, 'w') as f:
        f.write(merged)
    
    # TODO git add FILENAME
    
    return HttpResponseRedirect(reverse('webui-merge', args=[repo,org,cid]))

@ddrview
@login_required
@storage_required
def edit_raw( request, repo, org, cid ):
    """
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection_path = Collection.collection_path(request,repo,org,cid)
    filename = ''
    if request.method == 'POST':
        filename = request.POST.get('filename', None)
    elif request.method == 'GET':
        filename = request.GET.get('filename', None)
    filepath = os.path.join(collection_path, filename)
    
    if request.method == 'POST':
        form = MergeRawForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data['text']
            # TODO validate XML
            with open(filepath, 'w') as f:
                f.write(text)
            # git add file
            merge_add(collection_path, filename)
            return HttpResponseRedirect( reverse('webui-merge', args=[repo,org,cid]) )
    else:
        with open(filepath, 'r') as f:
            text = f.read()
        form = MergeRawForm({'filename': filename, 'text': text,})
    return render_to_response(
        'webui/merge/edit-raw.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'filename':filename,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

def edit_json( request, repo, org, cid ):
    """
    """
    from webui import merge
    collection_path = Collection.collection_path(request,repo,org,cid)
    
    filename = ''
    if request.method == 'POST':
        filename = request.POST.get('filename', None)
    elif request.method == 'GET':
        filename = request.GET.get('filename', None)
    
    fields = []
    if filename:
        path = os.path.join(collection_path, filename)
        with open(path, 'r') as f:
            txt = f.read()
        fields = merge.conflicting_fields(txt)
    
    if request.method == 'POST':
        #form = MergeJSONForm(request.POST)
        #if form.is_valid():
        #    text = form.cleaned_data['text']
        #    # TODO validate XML
        #    with open(filepath, 'w') as f:
        #        f.write(text)
        #    # git add file
        #    merge_add(collection_path, filename)
        assert False
    elif request.method == 'GET':
        form = MergeJSONForm(fields=fields)
        return render_to_response(
            'webui/merge/edit-json.html',
            {'filename':filename,
             'fields':fields,
             'form':form,},
            context_instance=RequestContext(request, processors=[])
        )
    return HttpResponseRedirect( reverse('webui-merge', args=[repo,org,cid]) )
