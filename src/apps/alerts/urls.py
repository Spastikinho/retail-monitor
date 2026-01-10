from django.urls import path

from . import views

app_name = 'alerts'

urlpatterns = [
    # Rules
    path('', views.AlertRuleListView.as_view(), name='rule_list'),
    path('rules/new/', views.AlertRuleCreateView.as_view(), name='rule_create'),
    path('rules/<uuid:pk>/', views.AlertRuleDetailView.as_view(), name='rule_detail'),
    path('rules/<uuid:pk>/edit/', views.AlertRuleUpdateView.as_view(), name='rule_edit'),
    path('rules/<uuid:pk>/delete/', views.AlertRuleDeleteView.as_view(), name='rule_delete'),
    # Events
    path('events/', views.AlertEventListView.as_view(), name='event_list'),
    path('events/<uuid:pk>/', views.AlertEventDetailView.as_view(), name='event_detail'),
]
