"""
URL patterns for REST API.
"""
from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    # Health Check
    path('health/', views.health_check, name='health_check'),

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
]
