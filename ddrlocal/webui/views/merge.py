import logging
logger = logging.getLogger(__name__)
import os

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from DDR import commands
from DDR import dvcs

from storage.decorators import storage_required
from webui.decorators import ddrview
from webui.models import Collection
from webui.views.decorators import login_required
from webui.forms.merge import MergeCommitForm, MergeRawForm, MergeJSONForm





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
    collection = Collection.from_request(request)
    repository = dvcs.repository(collection.path_abs)
    task_id = collection.locked()
    status = commands.status(collection)
    ahead = collection.repo_ahead()
    behind = collection.repo_behind()
    diverged = collection.repo_diverged()
    conflicted = collection.repo_conflicted()
    unmerged = dvcs.list_conflicted(repository)
    staged = dvcs.list_staged(repository)
    if request.method == 'POST':
        assert False
        form = MergeCommitForm(request.POST)
        if form.is_valid():
            which = form.cleaned_data['which']
            if which == 'merge':
                dvcs.merge_commit(repository)
                committed = 1
            elif which == 'commit':
                dvcs.diverge_commit(repository)
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
        form = MergeCommitForm({'path':collection.path, 'which':which,})
    return render(request, 'webui/merge/index.html', {
        'repo': repo,
        'org': org,
        'cid': cid,
        'collection_path': collection.path,
        'collection': collection,
        'status': status,
        'conflicted': conflicted,
        'ahead': ahead,
        'behind': behind,
        'unmerged': unmerged,
        'diverged': diverged,
        'staged': staged,
        'form': form,
    })


@ddrview
@login_required
@storage_required
def edit_auto( request, repo, org, cid ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, WEBUI_MESSAGES['LOGIN_REQUIRED'])
    collection = Collection.from_request(request)
    
    filename = request.GET.get('filename', None)
    filepath = os.path.join(collection.path, filename)
    with open(filepath, 'r') as f:
        text = f.read()
    merged = dvcs.automerge_conflicted(text, 'left')
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
    collection = Collection.from_request(request)
    repository = dvcs.repository(collection.path)
    filename = ''
    if request.method == 'POST':
        assert False
        filename = request.POST.get('filename', None)
    elif request.method == 'GET':
        filename = request.GET.get('filename', None)
    filepath = os.path.join(collection.path, filename)
    
    if request.method == 'POST':
        assert False
        form = MergeRawForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data['text']
            # TODO validate XML
            with open(filepath, 'w') as f:
                f.write(text)
            # git add file
            dvcs.merge_add(repository, filename)
            return HttpResponseRedirect( reverse('webui-merge', args=[repo,org,cid]) )
    else:
        with open(filepath, 'r') as f:
            text = f.read()
        form = MergeRawForm({'filename': filename, 'text': text,})
    return render(request, 'webui/merge/edit-raw.html', {
        'repo': repo,
        'org': org,
        'cid': cid,
        'filename':filename,
        'form': form,
    })

def edit_json( request, repo, org, cid ):
    """
    """
    collection = Collection.from_request(request)
    repository = dvcs.repository(collection.path)
    
    filename = ''
    if request.method == 'POST':
        assert False
        filename = request.POST.get('filename', None)
    elif request.method == 'GET':
        filename = request.GET.get('filename', None)
    
    fields = []
    if filename:
        path = os.path.join(collection.path, filename)
        with open(path, 'r') as f:
            txt = f.read()
        fields = dvcs.conflicting_fields(txt)
    
    if request.method == 'POST':
        assert False
        #form = MergeJSONForm(request.POST)
        #if form.is_valid():
        #    text = form.cleaned_data['text']
        #    # TODO validate XML
        #    with open(filepath, 'w') as f:
        #        f.write(text)
        #    # git add file
        #    dvcs.merge_add(repository, filename)
        assert False
    elif request.method == 'GET':
        form = MergeJSONForm(fields=fields)
        return render(request, 'webui/merge/edit-json.html', {
            'filename':filename,
            'fields':fields,
            'form':form,
        })
    return HttpResponseRedirect( reverse('webui-merge', args=[repo,org,cid]) )
