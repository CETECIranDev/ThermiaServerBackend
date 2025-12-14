from django.contrib import admin
from .models import ReportGeneration

@admin.register(ReportGeneration)
class ReportGenerationAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_type', 'clinic', 'patient', 'generated_by', 'created_at', 'file_path')
    list_filter = ('report_type', 'clinic', 'generated_by', 'created_at')
    search_fields = ('clinic__name', 'patient__first_name', 'patient__last_name', 'generated_by__username')



