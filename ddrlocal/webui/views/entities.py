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
from ddrlocal.forms import EntityForm

from storage import base_path
from storage.decorators import storage_required
from webui import api
from webui.forms.entities import NewEntityForm, UpdateForm
from webui.mets import NAMESPACES, NAMESPACES_XPATH
from webui.mets import METS_FIELDS, MetsForm
from webui.views.decorators import login_required
from xmlforms.models import XMLModel



# views ----------------------------------------------------------------

@storage_required
def detail( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    return render_to_response(
        'webui/entities/detail.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def changelog( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    return render_to_response(
        'webui/entities/changelog.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,},
        context_instance=RequestContext(request, processors=[])
    )

@storage_required
def entity_json( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    return HttpResponse(json.dumps(entity.json().data), mimetype="application/json")

@storage_required
def mets_xml( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    soup = BeautifulSoup(entity.mets().xml, 'xml')
    return HttpResponse(soup.prettify(), mimetype="application/xml")

@storage_required
def files( request, repo, org, cid, eid ):
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    return render_to_response(
        'webui/entities/files.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,},
        context_instance=RequestContext(request, processors=[])
    )

@login_required
@storage_required
def new( request, repo, org, cid ):
    """Gets new EID from workbench, creates new entity record.
    
    If it messes up, goes back to collection.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not (git_name and git_mail):
        messages.error(request, 'Login is required')
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    # get new entity ID
    eid = None
    eids = api.entities_next(request, repo, org, cid, 1)
    if eids:
        eid = int(eids[-1].split('-')[3])
    if eid:
        # create new entity
        entity_uid = '{}-{}-{}-{}'.format(repo,org,cid,eid)
        exit,status = commands.entity_create(git_name, git_mail, collection.path, entity_uid)
        if exit:
            messages.error(request, 'Error: {}'.format(status))
        else:
            redirect_url = reverse('webui-entity', args=[repo,org,cid,eid])
            messages.success(request, 'New entity created: {}'.format(entity_uid))
            return HttpResponseRedirect(redirect_url)
    else:
        messages.error(request, 'Error: Could not get new entity IDs from workbench.')
    # something happened...
    messages.error(request, 'Error: Could not create new entity.')
    return HttpResponseRedirect(reverse('webui-collection', args=[repo,org,cid]))

@login_required
@storage_required
def edit( request, repo, org, cid, eid ):
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, 'Login is required')
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    #
    if request.method == 'POST':
        form = EntityForm(request.POST)
        if form.is_valid():
            git_name = request.session.get('git_name')
            git_mail = request.session.get('git_mail')
            if git_name and git_mail:
                entity.form_process(form)
                entity.dump_json()
                entity.dump_mets()
                exit,status = commands.entity_update(git_name, git_mail,
                                                     entity.parent_path, entity.id,
                                                     [entity.json_path, entity.mets_path,])
                if exit:
                    messages.error(request, 'Error: {}'.format(status))
                else:
                    messages.success(request, 'Entity updated')
                    return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
            else:
                messages.error(request, 'Login is required')
    else:
        form = EntityForm(entity.form_data())
    return render_to_response(
        'webui/entities/edit-json.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': collection.id,
         'collection': collection,
         'entity': entity,
         'form': form,
         },
        context_instance=RequestContext(request, processors=[])
    )

@login_required
@storage_required
def edit_mets_xml( request, repo, org, cid, eid ):
    """
    on GET
    - reads contents of EAD.xml
    - puts in form, in textarea
    - user edits XML
    on POST
    - write contents of field to EAD.xml
    - commands.update
    """
    collection = Collection.from_json(Collection.collection_path(request,repo,org,cid))
    entity = Entity.from_json(Entity.entity_path(request,repo,org,cid,eid))
    #
    if request.method == 'POST':
        form = UpdateForm(request.POST)
        if form.is_valid():
            git_name = request.session.get('git_name')
            git_mail = request.session.get('git_mail')
            if git_name and git_mail:
                xml = form.cleaned_data['xml']
                # TODO validate XML
                with open(entity.mets_path, 'w') as f:
                    f.write(xml)
                
                exit,status = commands.entity_update(
                    git_name, git_mail,
                    entity.parent_path, entity.id,
                    [entity.mets_path])
                
                if exit:
                    messages.error(request, 'Error: {}'.format(status))
                else:
                    messages.success(request, 'Entity updated')
                    return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
            else:
                messages.error(request, 'Login is required')
    else:
        form = UpdateForm({'xml': entity.mets().xml,})
    return render_to_response(
        'webui/entities/edit-mets.html',
        {'repo': entity.repo,
         'org': entity.org,
         'cid': entity.cid,
         'eid': entity.eid,
         'collection_uid': entity.parent_uid,
         'entity': entity,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

@login_required
@storage_required
def edit_xml( request, repo, org, cid, eid, slug, Form, FIELDS, namespaces=None ):
    """Edit the contents of <archdesc>.
    """
    git_name = request.session.get('git_name')
    git_mail = request.session.get('git_mail')
    if not git_name and git_mail:
        messages.error(request, 'Login is required')
    collection_uid = '{}-{}-{}'.format(repo, org, cid)
    entity_uid     = '{}-{}-{}-{}'.format(repo, org, cid, eid)
    collection_abs = os.path.join(base_path(request), collection_uid)
    entity_abs     = os.path.join(collection_abs,'files',entity_uid)
    entity_rel     = os.path.join('files',entity_uid)
    xml_path_rel   = 'mets.xml'
    xml_path_abs   = os.path.join(entity_abs, xml_path_rel)
    with open(xml_path_abs, 'r') as f:
        xml = f.read()
    fields = Form.prep_fields(FIELDS, xml, namespaces=namespaces)
    #
    if request.method == 'POST':
        form = Form(request.POST, fields=fields, namespaces=namespaces)
        if form.is_valid():
            form_fields = form.fields
            cleaned_data = form.cleaned_data
            xml_new = Form.process(xml, fields, form, namespaces=namespaces)
            # TODO validate XML
            with open(xml_path_abs, 'w') as fnew:
                fnew.write(xml_new)
            # TODO validate XML
            exit,status = commands.entity_update(git_name, git_mail, collection_abs, entity_uid, [xml_path_rel])
            if exit:
                messages.error(request, 'Error: {}'.format(status))
            else:
                messages.success(request, '<{}> updated'.format(slug))
                return HttpResponseRedirect( reverse('webui-entity', args=[repo,org,cid,eid]) )
    else:
        form = Form(fields=fields, namespaces=namespaces)
    # template
    try:
        tf = 'webui/collections/edit-{}.html'.format(slug)
        t = get_template(tf)
        template_filename = tf
    except:
        template_filename = 'webui/entities/edit-xml.html'
    return render_to_response(
        template_filename,
        {'repo': repo,
         'org': org,
         'cid': cid,
         'eid': eid,
         'collection_uid': collection_uid,
         'entity_uid': entity_uid,
         'slug': slug,
         'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

def edit_mets( request, repo, org, cid, eid ):
    return edit_xml(request, repo, org, cid, eid,
                    slug='mets',
                    Form=MetsForm, FIELDS=METS_FIELDS,
                    namespaces=NAMESPACES,)
