from django.conf.urls import include, url
from django.views.generic import TemplateView

from webui import api
from webui.views import LoginOffline, login, logout
from webui.views import task_status, task_dismiss, task_list
from webui.views import gitstatus_queue, gitstatus_toggle
from webui.views import repository, organization, collections, entities, files
from webui.views import detail, merge, search


urlpatterns = [
    url(r'^login/offline$', LoginOffline.as_view(), name='webui-login-offline'),
    url(r'^login/$', login, name='webui-login'),
    url(r'^logout/$', logout, name='webui-logout'),
    
    # admin

    url(r'^task-status/$', task_status, name='webui-task-status'),
    url(r'^tasks/(?P<task_id>[-\w]+)/dismiss/$', task_dismiss, name='webui-tasks-dismiss'),
    url(r'^tasks/$', task_list, name='webui-tasks'),
    
    url(r'^gitstatus-queue/$', gitstatus_queue, name='webui-gitstatus-queue'),
    url(r'^gitstatus-toggle/$', gitstatus_toggle, name='webui-gitstatus-toggle'),
    
    url(r'^restart/$', TemplateView.as_view(template_name="webui/restart-park.html"), name='webui-restart'),
    #url(r'^supervisord/procinfo.html$', supervisord.procinfo_html, name='webui-supervisord-procinfo-html'),
    #url(r'^supervisord/procinfo.json$', supervisord.procinfo_json, name='webui-supervisord-procinfo-json'),
    #url(r'^supervisord/restart/$', supervisord.restart, name='webui-supervisord-restart'),

    # REST API
    
    url(r'^api/1.0/search$', api.Search.as_view(), name='api-search'),
    
    url(r'^api/1.0/es/(?P<oid>[\w\d-]+)/children/$', api.es_children, name='api-es-children'),
    url(r'^api/1.0/es/(?P<oid>[\w\d-]+)/$', api.es_detail, name='api-es-detail'),
    url(r'^api/1.0/(?P<oid>[\w\d-]+)/children/$', api.fs_children, name='api-fs-children'),
    url(r'^api/1.0/(?P<oid>[\w\d-]+)/$', api.fs_detail, name='api-fs-detail'),
    
    url(r'^api/0.2/(?P<object_id>[\w\d-]+)/children/$', api.object_children, name='api-object-children'),
    url(r'^api/0.2/(?P<object_id>[\w\d-]+)/files/$', api.object_nodes, name='api-object-nodes'),
    url(r'^api/0.2/(?P<object_id>[\w\d-]+)/$', api.object_detail, name='api-object'),
    
    url(r'^api/1.0/$', api.index, name='api-index'),
    
    # search

    #url(r'^search/(?P<field>[\w]+):(?P<term>[\w ,]+)/$', search.term_query, name='webui-search-term-query'),
    url(r'^search/$', search.search_ui, name='webui-search'),
 
    # merge
 
    url(r'^collection/(?P<cid>[\w\d-]+)/merge/auto/$', merge.edit_auto, name='webui-merge-auto'),
    url(r'^collection/(?P<cid>[\w\d-]+)/merge/json/$', merge.edit_json, name='webui-merge-json'),
    url(r'^collection/(?P<cid>[\w\d-]+)/merge/raw/$', merge.edit_raw, name='webui-merge-raw'),
    url(r'^collection/(?P<cid>[\w\d-]+)/merge/$', merge.merge, name='webui-merge'),
 
    # repository, organization
    url(r'^repository/(?P<cid>[\w\d-]+)/$', repository, name='webui-repository'),
    url(r'^organization/(?P<cid>[\w\d-]+)/$', organization, name='webui-organization'),
    
    # collections
 
    url(r'^collections/$', collections.collections, name='webui-collections'),
 
    url(r'^(?P<oid>[\w\d-]+)/search/$', search.collection, name='webui-search-collection'),
    
    url(r'^collection/(?P<cid>[\w\d-]+)/edit/$', collections.edit, name='webui-collection-edit'),
    url(r'^collection/(?P<cid>[\w\d-]+)/sync/$', collections.sync, name='webui-collection-sync'),
    url(r'^collection/(?P<cid>[\w\d-]+)/check/$', collections.check, name='webui-collection-check'),
    url(r'^collection/(?P<cid>[\w\d-]+)/signatures/$', collections.signatures, name='webui-collection-signatures'),
    url(r'^collection/(?P<cid>[\w\d-]+)/unlock/(?P<task_id>[\w\d-]+)/$', collections.unlock, name='webui-collection-unlock'),

    url(r'^collection/(?P<cid>[\w\d-]+)/export/objects/$', collections.csv_export, kwargs={'model':'entity'}, name='webui-collection-export-entities'),
    url(r'^collection/(?P<cid>[\w\d-]+)/export/files/$', collections.csv_export, kwargs={'model':'file'}, name='webui-collection-export-files'),
    url(r'^collection/(?P<cid>[\w\d-]+)-objects.csv$', collections.csv_download, kwargs={'model':'entity'}, name='webui-collection-csv-entities'),
    url(r'^collection/(?P<cid>[\w\d-]+)-files.csv$', collections.csv_download, kwargs={'model':'file'}, name='webui-collection-csv-files'),
    url(r'^collection/(?P<cid>[\w\d-]+)/import/objects/$', collections.csv_import, kwargs={'model':'entity'}, name='webui-collection-import-entities'),
    url(r'^collection/(?P<cid>[\w\d-]+)/import/files/$', collections.csv_import, kwargs={'model':'file'}, name='webui-collection-import-files'),

    url(r'^collection/(?P<cid>[\w\d-]+)/children/$', collections.children, name='webui-collection-children'),
    url(r'^collection/(?P<cid>[\w\d-]+)/changelog/$', collections.changelog, name='webui-collection-changelog'),
    url(r'^collection/(?P<cid>[\w\d-]+)/sync-status.json$', collections.sync_status_ajax, name='webui-collection-sync-status-ajax'),
    url(r'^collection/(?P<cid>[\w\d-]+)/git-status/$', collections.git_status, name='webui-collection-git-status'),
    url(r'^collection/(?P<cid>[\w\d-]+)/$', collections.detail, name='webui-collection'),

    url(r'^collection/(?P<oid>[\w\d-]+)/new-idservice/$', collections.new_idservice, name='webui-collection-newidservice'),
    url(r'^collection/(?P<oid>[\w\d-]+)/new-manual/$', collections.new_manual, name='webui-collection-newmanual'),
    url(r'^collection/(?P<oid>[\w\d-]+)/new/$', collections.new, name='webui-collection-new'),

    # entities

    url(r'^vocab/(?P<field>[\w]+)/$', entities.edit_vocab_terms, name='webui-entity-vocab-terms'),
    url(r'^entity/(?P<eid>[\w\d-]+)/delete/$', entities.delete, name='webui-entity-delete'),
    url(r'^entity/(?P<eid>[\w\d-]+)/edit/$', entities.edit, name='webui-entity-edit'),
    url(r'^entity/(?P<eid>[\w\d-]+)/unlock/(?P<task_id>[\w\d-]+)/$', entities.unlock, name='webui-entity-unlock'),

    url(r'^entity/(?P<eid>[\w\d-]+)/addfile.log$', entities.addfile_log, name='webui-entity-addfilelog'),
    url(r'^entity/(?P<eid>[\w\d-]+)/files/reload/$', entities.files_reload, name='webui-entity-files-reload'),
    url(r'^entity/(?P<eid>[\w\d-]+)/files/dedupe/$', entities.files_dedupe, name='webui-entity-files-dedupe'),
    url(r'^entity/(?P<eid>[\w\d-]+)/changelog/$', entities.changelog, name='webui-entity-changelog'),
    url(r'^entity/(?P<eid>[\w\d-]+)/children/$', entities.children, name='webui-entity-children'),
    url(r'^entity/(?P<eid>[\w\d-]+)/$', entities.detail, name='webui-entity'),
    # segments Just Work with entity patterns except for this one
    url(r'^segment/(?P<eid>[\w\d-]+)/$', entities.detail, name='webui-segment'),

    url(r'^entity/(?P<oid>[\w\d-]+)/new-idservice/$', entities.new_idservice, name='webui-entity-newidservice'),
    url(r'^entity/(?P<oid>[\w\d-]+)/new-manual/$', entities.new_manual, name='webui-entity-newmanual'),
    url(r'^entity/(?P<oid>[\w\d-]+)/new/$', entities.new, name='webui-entity-new'),

    # files

    url(r'^file/(?P<fid>[\w\d-]+)/delete/$', files.delete, name='webui-file-delete'),
    url(r'^file/(?P<fid>[\w\d-]+)/xmp.xml$', files.xmp, name='webui-file-xmp'),
    url(r'^file/(?P<fid>[\w\d-]+)/sig/$', files.set_signature, name='webui-file-sig'),
    url(r'^file/(?P<fid>[\w\d-]+)/edit/$', files.edit, name='webui-file-edit'),
    url(r'^file/(?P<fid>[\w\d-]+)/$', files.detail, name='webui-file'),
    url(r'^file/(?P<fid>[\w\d-]+)/new/access/$', files.new_access, name='webui-file-new-access'),

    url(r'^file/(?P<rid>[\w\d-]+)/batch/$', files.batch, name='webui-file-batch'),
    url(r'^file/(?P<rid>[\w\d-]+)/browse/$', files.browse, name='webui-file-browse'),
    url(r'^file/(?P<rid>[\w\d-]+)/new-external/$', files.new_external, name='webui-file-new-external'),
    #url(r'^file/(?P<rid>[\w\d-]+)/new-meta/$', files.new_meta, name='webui-file-new-meta'),
    url(r'^file/(?P<rid>[\w\d-]+)/new/$', files.new, name='webui-file-new'),
    url(r'^file-role/(?P<rid>[\w\d-]+)/$', entities.file_role, name='webui-file-role'),
    url(r'^file/(?P<eid>[\w\d-]+)-master/new/$', files.new, kwargs={'role':'master'}, name='webui-file-new-master'),
    url(r'^file/(?P<eid>[\w\d-]+)-mezzanine/new/$', files.new, kwargs={'role':'mezzanine'}, name='webui-file-new-mezzanine'),
    url(r'^file/(?P<eid>[\w\d-]+)/new/$', files.new, name='webui-file-new'),
 
    #
    url(r'^(?P<oid>[\w\d-]+)/$', detail, name='webui-detail'),
    url(r'^$', TemplateView.as_view(template_name="webui/index.html"), name='webui-index'),
]
