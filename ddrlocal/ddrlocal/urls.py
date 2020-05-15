from django.urls import include, path
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
    #path('admin/', include(admin.site.urls)),
    path('404/', TemplateView.as_view(template_name="ddrlocal/404.html")),
    path('500/', TemplateView.as_view(template_name="ddrlocal/500.html")),
    path('debug/', debug, name='debug'),
    path('storage/', include('storage.urls')),
    path('ui/', include('webui.urls')),
    path('', TemplateView.as_view(template_name="webui/index.html"), name='index'),
]
