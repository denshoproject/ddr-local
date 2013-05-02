from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^storage-required/$', 'storage.views.storage_required', name='storage-required'),
    url(r'^$', 'storage.views.storage', name='storage-index'),
)
