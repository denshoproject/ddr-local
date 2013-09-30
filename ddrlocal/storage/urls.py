from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^remount/0/$', 'storage.views.remount0', name='storage-remount0'),
    url(r'^remount/1/$', 'storage.views.remount1', name='storage-remount1'),
    url(r'^storage-required/$', 'storage.views.storage_required', name='storage-required'),
    url(r'^activate/$', 'storage.views.activate_device', name='storage-activate'),
    url(r'^unmount/$', 'storage.views.unmount_device', name='storage-unmount'),
    url(r'^mount/$', 'storage.views.mount_device', name='storage-mount'),
    url(r'^$', 'storage.views.index', name='storage-index'),
)
