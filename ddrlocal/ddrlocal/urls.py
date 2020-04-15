from django.conf.urls import include, url
from django.views.debug import technical_500_response
from django.views.generic import TemplateView


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
    url(r'^storage/', include('storage.urls')),
    url(r'^ui/', include('webui.urls')),
    url(r'^$', TemplateView.as_view(template_name="webui/index.html"), name='index'),
]
