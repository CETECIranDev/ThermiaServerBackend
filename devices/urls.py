from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'devices', views.DeviceViewSet)

urlpatterns = [
    # Admin Panel Endpoints
    path('', include(router.urls)),
    path('licenses/', views.LicenseCreateView.as_view(), name='license-create'),
    path('firmware/', views.FirmwareUploadView.as_view(), name='firmware-upload'),

    # IoT Device Endpoints
    path('sync/', views.DeviceSyncView.as_view(), name='device-sync'),
    path('firmware/download/<int:firmware_id>/', views.FirmwareDownloadView.as_view(), name='firmware-download'),

]