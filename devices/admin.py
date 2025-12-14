from django.contrib import admin
from .models import Device,License,Firmware

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'firmware_version')
    search_fields = ('created_at', 'status')
    list_filter = ('created_at', 'status')


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('status', 'license_type','start_date','end_date')
    search_fields = ('license_id', 'created_at')
    list_filter = ('status', 'license_type')


@admin.register(Firmware)
class FirmwareAdmin(admin.ModelAdmin):
    list_display = ('firmware_version', 'created_at')
    search_fields = ('firmware_version', 'created_at')


