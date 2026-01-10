from django.urls import path

from . import views

app_name = 'retailers'

urlpatterns = [
    path('', views.RetailerListView.as_view(), name='list'),
    path('<slug:slug>/', views.RetailerDetailView.as_view(), name='detail'),
]
