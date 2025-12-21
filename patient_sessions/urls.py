from django.urls import path
from . import views

urlpatterns = [

    # upload sessions from device
    path('upload/', views.SessionUploadView.as_view(), name='session-upload'),

    # patient history
    path('history/<uuid:patient_id>/', views.SessionHistoryView.as_view(), name='session-history'),

    # session details
    path('<int:pk>/', views.SessionDetailView.as_view(), name='session-detail'),
    path('<int:session_id>/logs/', views.SessionLogsView.as_view(), name='session-logs'),

    # statistics
    path('statistics/', views.SessionStatisticsView.as_view(), name='session-statistics'),
]
