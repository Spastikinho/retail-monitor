"""
URL patterns for REST API.
"""
from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    # Health Check & Setup
    path('health/', views.health_check, name='health_check'),
    path('setup/retailers/', views.setup_retailers, name='setup_retailers'),

    # Authentication
    path('auth/csrf/', views.get_csrf_token, name='get_csrf_token'),
    path('auth/login/', views.api_login, name='api_login'),
    path('auth/logout/', views.api_logout, name='api_logout'),
    path('auth/check/', views.check_auth, name='check_auth'),

    # Products
    path('products/', views.products_list, name='products_list'),
    path('products/<uuid:product_id>/', views.product_detail, name='product_detail'),

    # Retailers
    path('retailers/', views.retailers_list, name='retailers_list'),

    # Price History
    path('listings/<uuid:listing_id>/prices/', views.price_history, name='price_history'),

    # Reviews
    path('listings/<uuid:listing_id>/reviews/', views.reviews_list, name='reviews_list'),

    # Alerts
    path('alerts/', views.alerts_list, name='alerts_list'),

    # Analytics
    path('analytics/summary/', views.analytics_summary, name='analytics_summary'),

    # Scraping Control
    path('scrape/', views.trigger_scrape, name='trigger_scrape'),
    path('scrape/<uuid:session_id>/status/', views.scrape_status, name='scrape_status'),

    # Export
    path('export/products/', views.export_products, name='export_products'),
    path('export/monitoring/', views.export_monitoring_excel, name='export_monitoring_excel'),
    path('export/import/<uuid:import_id>/', views.export_import_excel, name='export_import_excel'),

    # Manual Import
    path('imports/', views.import_list, name='import_list'),
    path('imports/create/', views.import_urls, name='import_urls'),
    path('imports/<uuid:import_id>/', views.import_detail, name='import_detail'),

    # Monitoring Groups
    path('groups/', views.monitoring_groups_list, name='monitoring_groups_list'),
    path('groups/create/', views.monitoring_group_create, name='monitoring_group_create'),

    # Periods
    path('periods/', views.available_periods, name='available_periods'),

    # Runs API (batch import with status tracking)
    path('runs/', views.list_runs, name='list_runs'),
    path('runs/create/', views.create_run, name='create_run'),
    path('runs/<uuid:run_id>/', views.get_run, name='get_run'),
]
