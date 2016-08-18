from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^login/$', 'webui.views.login', name='webui-login'),
    url(r'^logout/$', 'webui.views.logout', name='webui-logout'),
    
    # admin

    url(r'^task-status/$', 'webui.views.task_status', name='webui-task-status'),
    url(r'^tasks/(?P<task_id>[-\w]+)/dismiss/$', 'webui.views.task_dismiss', name='webui-tasks-dismiss'),
    url(r'^tasks/$', 'webui.views.tasks', name='webui-tasks'),
    
    url(r'^gitstatus-queue/$', 'webui.views.gitstatus_queue', name='webui-gitstatus-queue'),
    
    url(r'^restart/$', TemplateView.as_view(template_name="webui/restart-park.html"), name='webui-restart'),
    url(r'^supervisord/procinfo.html$', 'webui.views.supervisord.procinfo_html', name='webui-supervisord-procinfo-html'),
    url(r'^supervisord/procinfo.json$', 'webui.views.supervisord.procinfo_json', name='webui-supervisord-procinfo-json'),
    url(r'^supervisord/restart/$', 'webui.views.supervisord.restart', name='webui-supervisord-restart'),

    # search

    url(r'^search/admin/$', 'webui.views.search.admin', name='webui-search-admin'),
    url(r'^search/reindex/$', 'webui.views.search.reindex', name='webui-search-reindex'),
    url(r'^search/drop/$', 'webui.views.search.drop_index', name='webui-search-drop'),
    #url(r'^search/(?P<field>[\w]+):(?P<term>[\w ,]+)/$', 'webui.views.search.term_query', name='webui-search-term-query'),
    url(r'^search/results/$', 'webui.views.search.results', name='webui-search-results'),
    url(r'^search/$', 'webui.views.search.index', name='webui-search-index'),

    # merge

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/merge/auto/$', 'webui.views.merge.edit_auto', name='webui-merge-auto'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/merge/json/$', 'webui.views.merge.edit_json', name='webui-merge-json'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/merge/raw/$', 'webui.views.merge.edit_raw', name='webui-merge-raw'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/merge/$', 'webui.views.merge.merge', name='webui-merge'),
    
    # collections

    url(r'^collections/$', 'webui.views.collections.collections', name='webui-collections'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/$', 'webui.views.collections.edit', name='webui-collection-edit'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/sync/$', 'webui.views.collections.sync', name='webui-collection-sync'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/unlock/(?P<task_id>[\w\d-]+)/$', 'webui.views.collections.unlock', name='webui-collection-unlock'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/export/objects/$', 'webui.views.collections.csv_export', kwargs={'model':'entity'}, name='webui-collection-export-entities'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/export/files/$', 'webui.views.collections.csv_export', kwargs={'model':'file'}, name='webui-collection-export-files'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/objects/csv$', 'webui.views.collections.csv_download', kwargs={'model':'entity'}, name='webui-collection-csv-entities'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/files/csv$', 'webui.views.collections.csv_download', kwargs={'model':'file'}, name='webui-collection-csv-files'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/children/$', 'webui.views.collections.children', name='webui-collection-children'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/collection.json$', 'webui.views.collections.collection_json', name='webui-collection-json'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/ead.xml$', 'webui.views.collections.ead_xml', name='webui-collection-ead-xml'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/changelog/$', 'webui.views.collections.changelog', name='webui-collection-changelog'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/sync-status.json$', 'webui.views.collections.sync_status_ajax', name='webui-collection-sync-status-ajax'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/git-status/$', 'webui.views.collections.git_status', name='webui-collection-git-status'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/$', 'webui.views.collections.detail', name='webui-collection'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)/new-expert/$', 'webui.views.collections.newexpert', name='webui-collection-newexpert'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)/new/$', 'webui.views.collections.new', name='webui-collection-new'),

    # entities

    url(r'^vocab/(?P<field>[\w]+)/$', 'webui.views.entities.edit_vocab_terms', name='webui-entity-vocab-terms'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/entity.json/edit/$', 'webui.views.entities.edit_json', name='webui-entity-edit-json'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/delete/$', 'webui.views.entities.delete', name='webui-entity-delete'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/edit/$', 'webui.views.entities.edit', name='webui-entity-edit'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/unlock/(?P<task_id>[\w\d-]+)/$', 'webui.views.entities.unlock', name='webui-entity-unlock'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/addfile.log$', 'webui.views.entities.addfile_log', name='webui-entity-addfilelog'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/files/dedupe/$', 'webui.views.entities.files_dedupe', name='webui-entity-files-dedupe'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/changelog/$', 'webui.views.entities.changelog', name='webui-entity-changelog'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/entity.json$', 'webui.views.entities.entity_json', name='webui-entity-json'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/mets.xml$', 'webui.views.entities.mets_xml', name='webui-entity-mets-xml'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/$', 'webui.views.entities.detail', name='webui-entity'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/new-expert/$', 'webui.views.entities.newexpert', name='webui-entity-newexpert'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/new/$', 'webui.views.entities.new', name='webui-entity-new'),

    # files

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<role>[\w]+)-(?P<sha1>[\w]+)/delete/$', 'webui.views.files.delete', name='webui-file-delete'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<role>[\w]+)-(?P<sha1>[\w]+)/edit/$', 'webui.views.files.edit', name='webui-file-edit'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<role>[\w]+)-(?P<sha1>[\w]+)/json/$', 'webui.views.files.file_json', name='webui-file-json'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<role>[\w]+)-(?P<sha1>[\w]+)/$', 'webui.views.files.detail', name='webui-file'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<role>[\w]+)-(?P<sha1>[\w]+)/new/access/$', 'webui.views.files.new_access', name='webui-file-new-access'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)(?P<role>[\w]+)/batch/$', 'webui.views.files.batch', name='webui-file-batch'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<role>[\w]+)/browse/$', 'webui.views.files.browse', name='webui-file-browse'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-(?P<role>[\w]+)/new/$', 'webui.views.files.new', name='webui-file-new'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/(?P<role>[\w]+)/$', 'webui.views.entities.children', name='webui-file-role'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-master/new/$', 'webui.views.files.new', kwargs={'role':'master'}, name='webui-file-new-master'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)-mezzanine/new/$', 'webui.views.files.new', kwargs={'role':'mezzanine'}, name='webui-file-new-mezzanine'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/new/$', 'webui.views.files.new', name='webui-file-new'),

    #

    url(r'^$', TemplateView.as_view(template_name="webui/index.html"), name='webui-index'),
)
