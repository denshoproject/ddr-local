from django.urls import path
from django.views.generic import TemplateView

from rest_framework.schemas import get_schema_view

from webui import api
from webui.views import LoginOffline, login, logout
from webui.views import task_status, task_dismiss, task_list
from webui.views import gitstatus_queue, gitstatus_toggle
from webui.views import repository, organizations, collections, entities, files
from webui.views import detail, merge, search
from webui.views import batch


urlpatterns = [
    path('login/offline', LoginOffline.as_view(), name='webui-login-offline'),
    path('login/', login, name='webui-login'),
    path('logout/', logout, name='webui-logout'),
    
    # admin

    path('task-status/', task_status, name='webui-task-status'),
    path('tasks/<slug:task_id>/dismiss/', task_dismiss, name='webui-tasks-dismiss'),
    path('tasks/', task_list, name='webui-tasks'),
    
    path('gitstatus-queue/', gitstatus_queue, name='webui-gitstatus-queue'),
    path('gitstatus-toggle/', gitstatus_toggle, name='webui-gitstatus-toggle'),
    
    path('restart/', TemplateView.as_view(template_name="webui/restart-park.html"), name='webui-restart'),
    #path('supervisord/procinfo.html', supervisord.procinfo_html, name='webui-supervisord-procinfo-html'),
    #path('supervisord/procinfo.json', supervisord.procinfo_json, name='webui-supervisord-procinfo-json'),
    #path('supervisord/restart/', supervisord.restart, name='webui-supervisord-restart'),

    # REST API
    
    # Use the `get_schema_view()` helper to add a `SchemaView` to project URLs.
    #   * `title` and `description` parameters are passed to `SchemaGenerator`.
    #   * Provide view name for use with `reverse()`.
    path('openapi/', get_schema_view(
        title='Densho Digital Repository Editor API',
        description='DESCRIPTION GOES HERE',
        version='1.0',
    ), name='openapi-schema'),
    
    path('api/1.0/ui-state/', api.ui_state, name='api-state'),
    
    path('api/1.0/search', api.Search.as_view(), name='api-search'),
    
    path('api/1.0/es/<slug:oid>/children/', api.es_children, name='api-es-children'),
    path('api/1.0/es/<slug:oid>/', api.es_detail, name='api-es-detail'),
    path('api/1.0/<slug:oid>/children/', api.fs_children, name='api-fs-children'),
    path('api/1.0/<slug:oid>/', api.fs_detail, name='api-fs-detail'),
    
    path('api/0.2/<slug:object_id>/children/', api.object_children, name='api-object-children'),
    path('api/0.2/<slug:object_id>/files/', api.object_nodes, name='api-object-nodes'),
    path('api/0.2/<slug:object_id>/', api.object_detail, name='api-object'),
    
    path('api/1.0/', api.index, name='api-index'),
    
    # search

    #path('search/<slug:field>:<slug:term>/', search.term_query, name='webui-search-term-query'),
    path('search/', search.search_ui, name='webui-search'),
 
    # merge
 
    path('collection/<slug:cid>/merge/auto/', merge.edit_auto, name='webui-merge-auto'),
    path('collection/<slug:cid>/merge/json/', merge.edit_json, name='webui-merge-json'),
    path('collection/<slug:cid>/merge/raw/', merge.edit_raw, name='webui-merge-raw'),
    path('collection/<slug:cid>/merge/', merge.merge, name='webui-merge'),
 
    # repository, organization
    path('repository/<slug:cid>/', repository, name='webui-repository'),
    path('organizations/', organizations.list, name='webui-organizations'),
    path('organizations/<slug:oid>/', organizations.detail, name='webui-organization'),
    
    # collections
 
    path('collections/', collections.collections, name='webui-collections'),
 
    path('collection/<slug:oid>/search/', search.collection, name='webui-collection-search'),
    
    path('collection/<slug:cid>/edit/', collections.edit, name='webui-collection-edit'),
    path('collection/<slug:cid>/sync/', collections.sync, name='webui-collection-sync'),
    path('collection/<slug:cid>/reindex/', collections.reindex, name='webui-collection-reindex'),
    path('collection/<slug:cid>/check/', collections.check, name='webui-collection-check'),
    path('collection/<slug:cid>/signatures/', collections.signatures, name='webui-collection-signatures'),
    path('collection/<slug:cid>/unlock/<slug:task_id>/', collections.unlock, name='webui-collection-unlock'),

    path('collection/<slug:cid>/export/objects/', collections.csv_export, kwargs={'model':'entity'}, name='webui-collection-export-entities'),
    path('collection/<slug:cid>/export/files/', collections.csv_export, kwargs={'model':'file'}, name='webui-collection-export-files'),
    path('collection/<slug:cid>-objects.csv', collections.csv_download, kwargs={'model':'entity'}, name='webui-collection-csv-entities'),
    path('collection/<slug:cid>-files.csv', collections.csv_download, kwargs={'model':'file'}, name='webui-collection-csv-files'),

    path('collection/<slug:cid>/import/objects/', collections.csv_import, kwargs={'model':'entity'}, name='webui-collection-import-entities'),

    path('collection/<slug:cid>/import/files/confirm/', batch.ImportFiles.as_view(), name='webui-import-files-confirm'),
    path('collection/<slug:cid>/import/files/', batch.import_files_browse, name='webui-import-files-browse'),

    path('collection/<slug:cid>/children/', collections.children, name='webui-collection-children'),
    path('collection/<slug:cid>/changelog/', collections.changelog, name='webui-collection-changelog'),
    path('collection/<slug:cid>/sync-status.json', collections.sync_status_ajax, name='webui-collection-sync-status-ajax'),
    path('collection/<slug:cid>/git-status/', collections.git_status, name='webui-collection-git-status'),
    path('collection/<slug:cid>/', collections.detail, name='webui-collection'),

    path('collection/<slug:oid>/new-idservice/', collections.new_idservice, name='webui-collection-newidservice'),
    path('collection/<slug:oid>/new-manual/', collections.new_manual, name='webui-collection-newmanual'),
    path('collection/<slug:oid>/new/', collections.new, name='webui-collection-new'),

    # entities

    path('vocab/<slug:field>/', entities.edit_vocab_terms, name='webui-entity-vocab-terms'),
    path('entity/<slug:eid>/delete/', entities.delete, name='webui-entity-delete'),
    path('entity/<slug:eid>/edit/', entities.edit, name='webui-entity-edit'),
    path('entity/<slug:eid>/unlock/<slug:task_id>/', entities.unlock, name='webui-entity-unlock'),

    path('entity/<slug:eid>/addfile.log', entities.addfile_log, name='webui-entity-addfilelog'),
    path('entity/<slug:eid>/files/reload/', entities.files_reload, name='webui-entity-files-reload'),
    path('entity/<slug:eid>/files/dedupe/', entities.files_dedupe, name='webui-entity-files-dedupe'),
    path('entity/<slug:eid>/changelog/', entities.changelog, name='webui-entity-changelog'),
    path('entity/<slug:eid>/children/', entities.children, name='webui-entity-children'),
    path('entity/<slug:eid>/', entities.detail, name='webui-entity'),
    # segments Just Work with entity patterns except for this one
    path('segment/<slug:eid>/', entities.detail, name='webui-segment'),

    path('entity/<slug:oid>/new-idservice/', entities.new_idservice, name='webui-entity-newidservice'),
    path('entity/<slug:oid>/new-manual/', entities.new_manual, name='webui-entity-newmanual'),
    path('entity/<slug:oid>/new/', entities.new, name='webui-entity-new'),

    # files

    path('file/<slug:fid>/delete/', files.delete, name='webui-file-delete'),
    path('file/<slug:fid>/xmp.xml', files.xmp, name='webui-file-xmp'),
    path('file/<slug:fid>/sig/', files.set_signature, name='webui-file-sig'),
    path('file/<slug:fid>/edit/', files.edit, name='webui-file-edit'),
    path('file/<slug:fid>/', files.detail, name='webui-file'),
    path('file/<slug:fid>/new/access/', files.new_access, name='webui-file-new-access'),

    path('file/<slug:rid>/batch/', files.batch, name='webui-file-batch'),
    path('file/<slug:rid>/browse/', files.browse, name='webui-file-browse'),
    path('file/<slug:rid>/new-external/', files.new_external, name='webui-file-new-external'),
    #path('file/<slug:rid>/new-meta/', files.new_meta, name='webui-file-new-meta'),
    path('file/<slug:rid>/new/', files.new, name='webui-file-new'),
    path('file-role/<slug:rid>/', entities.file_role, name='webui-file-role'),
    path('file/<slug:eid>-master/new/', files.new, kwargs={'role':'master'}, name='webui-file-new-master'),
    path('file/<slug:eid>-mezzanine/new/', files.new, kwargs={'role':'mezzanine'}, name='webui-file-new-mezzanine'),
    path('file/<slug:eid>/new/', files.new, name='webui-file-new'),

    #
    path('<slug:oid>/', detail, name='webui-detail'),
    path('', TemplateView.as_view(template_name="webui/index.html"), name='webui-index'),
]
