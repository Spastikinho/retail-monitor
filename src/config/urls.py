"""
URL configuration for Retail Monitor project.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Apps
    path('', include('apps.core.urls')),
    path('products/', include('apps.products.urls')),
    path('retailers/', include('apps.retailers.urls')),
    path('scraping/', include('apps.scraping.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('alerts/', include('apps.alerts.urls')),
    path('reports/', include('apps.reports.urls')),

    # REST API
    path('api/v1/', include('apps.api.urls')),
]

# Customize admin site
admin.site.site_header = 'Retail Monitor'
admin.site.site_title = 'Retail Monitor Admin'
admin.site.index_title = 'Управление системой мониторинга'
