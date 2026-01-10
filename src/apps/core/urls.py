from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('health/', views.health_check, name='health'),
    path('ready/', views.ready_check, name='ready'),

    # API endpoints for charts
    path('api/price-trends/', views.api_price_trends, name='api_price_trends'),
    path('api/reviews-by-rating/', views.api_reviews_by_rating, name='api_reviews_by_rating'),
    path('api/reviews-trend/', views.api_reviews_trend, name='api_reviews_trend'),
    path('api/retailer-comparison/', views.api_retailer_comparison, name='api_retailer_comparison'),
    path('api/scraping-activity/', views.api_scraping_activity, name='api_scraping_activity'),
]
