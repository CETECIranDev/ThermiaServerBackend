from django.urls import path
from . import views

urlpatterns = [
    # patients management
    path('', views.PatientListView.as_view(), name='patient-list'),
    path('create/', views.PatientCreateView.as_view(), name='patient-create'),
    path('<uuid:patient_id>/', views.PatientDetailView.as_view(), name='patient-detail'),

    # QR Code and token
    path('<uuid:patient_id>/generate-token/', views.GeneratePatientTokenView.as_view(), name='generate-patient-token'),
    path('tablet/update/', views.PatientUpdateByTokenView.as_view(), name='patient-tablet-update'),
]

