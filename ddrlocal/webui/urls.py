from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^login/$', 'webui.views.login', name='webui-login'),
    url(r'^logout/$', 'webui.views.logout', name='webui-logout'),
    url(r'^working/$', TemplateView.as_view(template_name="webui/working.html"), name='webui-working'),

    # collection(s)

    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/sync/$', 'webui.views.collections.sync', name='webui-collection-sync'),

    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/ead/$', 'webui.views.collections.edit_ead', name='webui-collection-edit-ead'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/overview/$', 'webui.views.collections.edit_overview', name='webui-collection-edit-overview'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/admininfo/$', 'webui.views.collections.edit_admininfo', name='webui-collection-edit-admininfo'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/bioghist/$', 'webui.views.collections.edit_bioghist', name='webui-collection-edit-bioghist'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/scopecontent/$', 'webui.views.collections.edit_scopecontent', name='webui-collection-edit-scopecontent'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/adjunctdesc/$', 'webui.views.collections.edit_adjunctdesc', name='webui-collection-edit-adjunctdesc'),

    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/ead.xml$', 'webui.views.collections.ead_xml', name='webui-collection-ead-xml'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/changelog/$', 'webui.views.collections.changelog', name='webui-collection-changelog'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/entities/$', 'webui.views.collections.entities', name='webui-collection-entities'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/git-status/$', 'webui.views.collections.git_status', name='webui-collection-git-status'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/git-annex-status/$', 'webui.views.collections.git_annex_status', name='webui-collection-git-annex-status'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/$', 'webui.views.collections.detail', name='webui-collection'),

    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)/new/$', 'webui.views.collections.new', name='webui-collection-new'),

    url(r'^collections/$', 'webui.views.collections.collections', name='webui-collections'),

    # entity

    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/edit/mets/$', 'webui.views.entities.edit_mets', name='webui-entity-edit-mets'),
    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/edit/metshdr/$', 'webui.views.entities.edit_metshdr', name='webui-entity-edit-metshdr'),
    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/add/$', 'webui.views.entities.entity_add', name='webui-entity-add'),

    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/files/(?P<filenum>[\d]+)/$', 'webui.views.entities.entity_file', name='webui-entity-file'),
    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/files/$', 'webui.views.entities.entity_files', name='webui-entity-files'),
    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/changelog/$', 'webui.views.entities.changelog', name='webui-entity-changelog'),
    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/mets.xml$', 'webui.views.entities.entity_mets_xml', name='webui-entity-mets-xml'),
    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/$', 'webui.views.entities.detail', name='webui-entity'),

    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/new/$', 'webui.views.entities.new', name='webui-entity-new'),


    url(r'^$', TemplateView.as_view(template_name="webui/index.html"), name='webui-index'),
)
