from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^storage-required/$', 'webui.views.storage_required', name='storage-required'),
    url(r'^/$', 'webui.views.storage', name='storage-index'),
)
