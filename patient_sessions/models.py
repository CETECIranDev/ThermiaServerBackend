from django.db import models
from django.utils import timezone

class Session(models.Model):
    """
    Represents a treatment session of a patient on a device in a clinic.
    Stores session summary, timing, and related patient/device/clinic.
    """
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, null=True, related_name='sessions')
    device = models.ForeignKey('devices.Device', on_delete=models.CASCADE, null=True, related_name='sessions')
    clinic = models.ForeignKey('accounts.Clinic', on_delete=models.CASCADE, null=True, related_name='sessions')
    summary = models.JSONField(help_text="areas_treated / parameters / extra_data")
    start_time = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        patient_name = self.patient.patient_id if self.patient else "No Patient"
        return f"Session {self.id} - {patient_name}"

class SessionLog(models.Model):
    """
    Logs events or messages related to a session (info, warning, error).
    """
    session = models.ForeignKey('patient_sessions.Session', on_delete=models.CASCADE, null=True, related_name='logs')
    LOG_TYPE_CHOICES = (
        ('info', 'Info'),
        ('error', 'Error'),
        ('warning', 'Warning'),
    )
    log_type = models.CharField(max_length=10, choices=LOG_TYPE_CHOICES)
    logged_at = models.DateTimeField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        session_id = self.session.id if self.session else "No Session"
        return f"{self.log_type} - Session {session_id}"