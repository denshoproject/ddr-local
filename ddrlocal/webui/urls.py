from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^login/$', 'webui.views.login', name='webui-login'),
    url(r'^logout/$', 'webui.views.logout', name='webui-logout'),
    url(r'^working/$', TemplateView.as_view(template_name="webui/working.html"), name='webui-working'),

    # collections

    url(r'^collections/$', 'webui.views.collections.collections', name='webui-collections'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/ead/$', 'webui.views.collections.edit_ead', name='webui-collection-edit-ead'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/overview/$', 'webui.views.collections.edit_overview', name='webui-collection-edit-overview'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/admininfo/$', 'webui.views.collections.edit_admininfo', name='webui-collection-edit-admininfo'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/bioghist/$', 'webui.views.collections.edit_bioghist', name='webui-collection-edit-bioghist'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/scopecontent/$', 'webui.views.collections.edit_scopecontent', name='webui-collection-edit-scopecontent'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/adjunctdesc/$', 'webui.views.collections.edit_adjunctdesc', name='webui-collection-edit-adjunctdesc'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/edit/$', 'webui.views.collections.edit', name='webui-collection-edit'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/sync/$', 'webui.views.collections.sync', name='webui-collection-sync'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/entities/$', 'webui.views.collections.entities', name='webui-collection-entities'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/collection.json$', 'webui.views.collections.collection_json', name='webui-collection-json'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/ead.xml$', 'webui.views.collections.ead_xml', name='webui-collection-ead-xml'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/changelog/$', 'webui.views.collections.changelog', name='webui-collection-changelog'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/git-status/$', 'webui.views.collections.git_status', name='webui-collection-git-status'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/$', 'webui.views.collections.detail', name='webui-collection'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)/new/$', 'webui.views.collections.new', name='webui-collection-new'),

    # entities

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/edit/mets.xml/$', 'webui.views.entities.edit_mets_xml', name='webui-entity-edit-mets-xml'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/edit/mets/$', 'webui.views.entities.edit_mets', name='webui-entity-edit-mets'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/edit/$', 'webui.views.entities.edit', name='webui-entity-edit'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/files/$', 'webui.views.entities.files', name='webui-entity-files'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/changelog/$', 'webui.views.entities.changelog', name='webui-entity-changelog'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/entity.json$', 'webui.views.entities.entity_json', name='webui-entity-json'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/mets.xml$', 'webui.views.entities.mets_xml', name='webui-entity-mets-xml'),
    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/$', 'webui.views.entities.detail', name='webui-entity'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/new/$', 'webui.views.entities.new', name='webui-entity-new'),

    # files

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/files/(?P<filenum>[\d]+)/edit/$', 'webui.views.files.edit', name='webui-file-edit'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/files/(?P<filenum>[\d]+)/$', 'webui.views.files.detail', name='webui-file-detail'),

    url(r'^(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/files/new/$', 'webui.views.files.new', name='webui-file-new'),

    #

    url(r'^$', TemplateView.as_view(template_name="webui/index.html"), name='webui-index'),
)
