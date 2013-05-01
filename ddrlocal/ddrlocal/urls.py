from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()
from django.views.generic import TemplateView

from storage import urls as storage_urls
from webui import urls as webui_urls

urlpatterns = patterns(
    '',
    #url(r'^admin/', include(admin.site.urls)),
    url(r'^404/', TemplateView.as_view(template_name="ddrlocal/404.html")),
    url(r'^500/', TemplateView.as_view(template_name="ddrlocal/500.html")),
    url(r'^storage/', include(storage_urls)),
    url(r'^ui/', include(webui_urls)),
    url(r'^$', TemplateView.as_view(template_name="webui/index.html"), name='index'),
)
