from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^query/$', 'search.views.query', name='search-query'),
    url(r'^admin/$', 'search.views.admin', name='search-admin'),
    url(r'^reindex/$', 'search.views.reindex', name='search-reindex'),
    url(r'^drop/$', 'search.views.drop_index', name='search-drop'),
    url(r'^$', 'search.views.index', name='search-index'),
)
