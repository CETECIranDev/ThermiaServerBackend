from django.urls import path
from . import views

urlpatterns = [

    # upload sessions from device
    path('upload/', views.SessionUploadView.as_view(), name='session-upload'),

    # Session history (two options for frontend convenience)
    # Option A: Get history of a specific patient by ID in the URL
    path('history/<uuid:patient_id>/', views.SessionHistoryView.as_view(), name='patient-history-detail'),
    # Option B: List all sessions with search and filter (for doctors)
    path('history/', views.SessionHistoryView.as_view(), name='clinic-history-list'),

    # session details
    path('<int:pk>/', views.SessionDetailView.as_view(), name='session-detail'),
    path('<int:session_id>/logs/', views.SessionLogsView.as_view(), name='session-logs'),

    # session statistics
    path('statistics/', views.SessionStatisticsView.as_view(), name='session-statistics'),
]
