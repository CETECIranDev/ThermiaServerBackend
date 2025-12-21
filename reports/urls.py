from django.urls import path
from . import views

urlpatterns = [
    # generate report
    path('generate/', views.ReportGenerateView.as_view(), name='report-generate'),
    path('list/', views.ReportListView.as_view(), name='report-list'),
    path('<int:report_id>/download/', views.ReportDownloadView.as_view(), name='report-download'),
    path('<int:report_id>/status/', views.ReportStatusView.as_view(), name='report-status'),

    # summary
    path('clinic/summary/', views.ClinicReportView.as_view(), name='clinic-summary'),
]

