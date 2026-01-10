from django.urls import path

from . import views

app_name = 'products'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='list'),
    path('create/', views.ProductCreateView.as_view(), name='create'),
    path('import/', views.ProductImportView.as_view(), name='import'),
    path('export/', views.ProductExportView.as_view(), name='export'),
    path('batch/', views.BatchActionView.as_view(), name='batch_action'),
    path('<uuid:pk>/', views.ProductDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.ProductUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.ProductDeleteView.as_view(), name='delete'),
    # Listings
    path('<uuid:product_pk>/listings/add/', views.ListingCreateView.as_view(), name='listing_add'),
    path('listings/<uuid:pk>/delete/', views.ListingDeleteView.as_view(), name='listing_delete'),
]
