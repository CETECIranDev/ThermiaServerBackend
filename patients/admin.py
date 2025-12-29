from django.contrib import admin
from .models import Patient,PatientToken

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('id','patient_id','clinic','created_at')
    search_fields = ('patient_id','personal_data')
    list_filter = ('clinic','created_at')
    readonly_fields = ('patient_id','created_at')

@admin.register(PatientToken)
class PatientTokenAdmin(admin.ModelAdmin):
    list_display = ('id','token','patient','get_clinic','expires_at','created_at')
    search_fields = ('token','patient__patient_id')
    list_filter = ('expires_at','created_at','patient__clinic',)
    readonly_fields = ('token','created_at')

    # PatientToken doesn't have direct access to clinic
    def get_clinic(self, obj):
        return obj.patient.clinic
    get_clinic.short_description = 'Clinic'
