from django.urls import path
from django.views.generic import TemplateView

from storage import views

urlpatterns = [
    path('storage-required/', views.storage_required, name='storage-required'),
    path('<slug:opcode>/<slug:devicetype>/', views.operation, name='storage-operation'),
    path('', views.index, name='storage-index'),
]
