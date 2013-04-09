from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^collections/$', 'webui.views.collections', name='webui-collections'),
)
