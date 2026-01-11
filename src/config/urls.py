"""
URL configuration for Retail Monitor project.

Production architecture:
- Frontend: Next.js on Vercel (single source of UI truth)
- Backend: Django on Railway (API-only + Admin)

In production (UI_MODE='api-only'):
- /admin/ - Django admin (internal ops)
- /api/v1/* - REST API (consumed by frontend)
- /health/, /ready/ - Infrastructure checks
- All other routes redirect to frontend

In development (UI_MODE='django'):
- Full Django template UI available for testing
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.urls import path, include, re_path

def frontend_redirect(request):
    """Redirect to frontend for non-API routes in production."""
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    return HttpResponseRedirect(f"{frontend_url}{request.path}")


# Core URL patterns (always available)
urlpatterns = [
    # Admin (always available - internal ops)
    path('admin/', admin.site.urls),

    # REST API (always available - consumed by frontend)
    path('api/v1/', include('apps.api.urls')),

    # Health/Ready checks (always available - infrastructure)
    path('health/', include([
        path('', include('apps.core.urls_health')),
    ])),
]

# UI Mode determines which routes are available
if getattr(settings, 'UI_MODE', 'api-only') == 'django':
    # Development mode: Django templates available
    urlpatterns += [
        # Authentication
        path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
        path('logout/', auth_views.LogoutView.as_view(), name='logout'),

        # Django template apps
        path('', include('apps.core.urls')),
        path('products/', include('apps.products.urls')),
        path('retailers/', include('apps.retailers.urls')),
        path('scraping/', include('apps.scraping.urls')),
        path('analytics/', include('apps.analytics.urls')),
        path('alerts/', include('apps.alerts.urls')),
        path('reports/', include('apps.reports.urls')),
    ]
else:
    # Production mode: Redirect all non-API routes to frontend
    urlpatterns += [
        # Catch-all: redirect to frontend
        re_path(r'^(?!admin|api|health|ready|static).*$', frontend_redirect),
    ]

# Customize admin site
admin.site.site_header = 'Retail Monitor'
admin.site.site_title = 'Retail Monitor Admin'
admin.site.index_title = 'System Administration'
