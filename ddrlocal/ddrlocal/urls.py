from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^404/', TemplateView.as_view(template_name="ddrlocal/404.html")),
    url(r'^500/', TemplateView.as_view(template_name="ddrlocal/500.html")),
    #url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$', 'webui.views.login', name='webui-login'),
    url(r'^logout/$', 'webui.views.logout', name='webui-logout'),
    url(r'^collections/$', 'webui.views.collections', name='webui-collections'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/$', 'webui.views.collection', name='webui-collection'),
    url(r'^$', TemplateView.as_view(template_name="webui/index.html"), name='webui-index'),
)
