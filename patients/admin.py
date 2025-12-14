from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_id','clinic','created_at')
    search_fields = ('patient_id','personal_data')
    list_filter = ('clinic','created_at')
    readonly_fields = ('patient_id','created_at')


