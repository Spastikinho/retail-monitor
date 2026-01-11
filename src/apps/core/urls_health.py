"""
Health check URLs - always available regardless of UI mode.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.health_check, name='health'),
    path('ready/', views.ready_check, name='ready'),
]
