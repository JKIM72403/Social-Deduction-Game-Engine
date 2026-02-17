from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls'),
    path('api/', include('games.urls')),
    # Serve React app for all other routes - must be last
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
]
