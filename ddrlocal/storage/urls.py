from django.conf.urls import url
from django.views.generic import TemplateView

from storage import views

urlpatterns = [
    url(r'^storage-required/$', views.storage_required, name='storage-required'),
    url(r'^(?P<opcode>[\w]+)/(?P<devicetype>[\w]+)/$', views.operation, name='storage-operation'),
    url(r'^$', views.index, name='storage-index'),
]
