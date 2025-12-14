from django.contrib import admin
from .models import Session,SessionLog
@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'device', 'clinic', 'start_time', 'ended_at')
    list_filter = ('clinic', 'device', 'start_time')
    search_fields = ('patient__first_name', 'patient__last_name', 'device__serial_number', 'clinic__name')

@admin.register(SessionLog)
class SessionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'log_type', 'logged_at')
    list_filter = ('log_type', 'logged_at')
    search_fields = ('session__patient__first_name', 'session__patient__last_name', 'message')
