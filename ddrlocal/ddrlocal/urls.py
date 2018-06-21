from django.conf.urls import include, url
from django.views.debug import technical_500_response
from django.views.generic import TemplateView

from djcelery import urls as djcelery_urls

from storage import urls as storage_urls
from webui import urls as webui_urls


DEBUG_TEXT = """
Scroll down to view request metadata and application settings.
Hit your back button to return to the editor.
"""

class Debug(Exception):
    pass

def debug(request):
    return technical_500_response(request, Debug, Debug(DEBUG_TEXT), None)


urlpatterns = [
    #url(r'^admin/', include(admin.site.urls)),
    url(r'^404/', TemplateView.as_view(template_name="ddrlocal/404.html")),
    url(r'^500/', TemplateView.as_view(template_name="ddrlocal/500.html")),
    url(r'^debug/', debug, name='debug'),
    url(r'^celery/', include(djcelery_urls)),
    url(r'^storage/', include(storage_urls)),
    url(r'^ui/', include(webui_urls)),
    url(r'^$', TemplateView.as_view(template_name="webui/index.html"), name='index'),
]
