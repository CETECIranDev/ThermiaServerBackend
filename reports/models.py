from django.db import models

class ReportGeneration(models.Model):
    """
    Represents a generated report for a clinic or patient,
    including the report type, file, and creator.
    """
    clinic = models.ForeignKey('accounts.Clinic', on_delete=models.CASCADE, related_name='reports')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, null=True, related_name='reports')
    generated_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reports')
    REPORT_TYPE_CHOICES = (
        ('clinic_summary', 'Clinic Summary'),
        ('patient_history', 'Patient History'),
        ('device_usage', 'Device Usage'),
    )
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    file_path= models.FileField(upload_to='reports/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report_type} - {self.created_at}"