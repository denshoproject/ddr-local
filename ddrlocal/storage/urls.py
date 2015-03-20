from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^storage-required/$', 'storage.views.storage_required', name='storage-required'),
    url(r'^(?P<opcode>[\w]+)/(?P<devicetype>[\w]+)/$', 'storage.views.operation', name='storage-operation'),
    url(r'^$', 'storage.views.index', name='storage-index'),
)
