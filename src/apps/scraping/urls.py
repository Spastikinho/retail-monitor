from django.urls import path

from . import views

app_name = 'scraping'

urlpatterns = [
    path('sessions/', views.ScrapeSessionListView.as_view(), name='session_list'),
    path('sessions/<uuid:pk>/', views.ScrapeSessionDetailView.as_view(), name='session_detail'),
    path('run/', views.RunScrapeView.as_view(), name='run'),
    path('run/<uuid:listing_pk>/', views.RunScrapeView.as_view(), name='run_listing'),
    # Reviews
    path('reviews/', views.ReviewListView.as_view(), name='reviews_list'),
    path('reviews/<uuid:pk>/', views.ReviewDetailView.as_view(), name='review_detail'),
    # Manual Import (basic)
    path('import/', views.ManualImportCreateView.as_view(), name='import_create'),
    path('import/list/', views.ManualImportListView.as_view(), name='import_list'),
    path('import/<uuid:pk>/', views.ManualImportDetailView.as_view(), name='import_detail'),
    path('import/<uuid:pk>/status/', views.ManualImportStatusView.as_view(), name='import_status'),
    path('import/<uuid:pk>/delete/', views.ManualImportDeleteView.as_view(), name='import_delete'),
    path('import/quick/', views.QuickImportView.as_view(), name='quick_import'),
    # Enhanced Import with Monitoring
    path('monitoring/', views.EnhancedImportView.as_view(), name='monitoring_import'),
    path('monitoring/analytics/', views.MonitoringAnalyticsView.as_view(), name='analytics'),
    # Monitoring Groups
    path('groups/', views.MonitoringGroupListView.as_view(), name='group_list'),
    path('groups/create/', views.MonitoringGroupCreateView.as_view(), name='group_create'),
    path('groups/<uuid:pk>/delete/', views.MonitoringGroupDeleteView.as_view(), name='group_delete'),
    # Export
    path('export/', views.ExportMonitoringView.as_view(), name='export_monitoring'),
    path('export/<uuid:pk>/', views.ExportSingleImportView.as_view(), name='export_single'),
]
