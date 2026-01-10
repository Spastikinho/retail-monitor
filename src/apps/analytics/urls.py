from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.AnalysisListView.as_view(), name='analysis_list'),
    path('generate/', views.GenerateAnalysisView.as_view(), name='generate'),
    path('<uuid:pk>/', views.AnalysisDetailView.as_view(), name='analysis_detail'),
]
