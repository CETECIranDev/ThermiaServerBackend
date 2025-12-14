from django.db import models
import uuid

class Patient(models.Model):
    """
    Stores patient personal and contact information.
    Each patient is associated with a clinic.
    """
    patient_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
    clinic = models.ForeignKey('accounts.Clinic', on_delete=models.CASCADE, related_name='patients')
    personal_data = models.JSONField(
        help_text="""
        patient personal information:
        {
          "first_name": "",
          "last_name": "",
          "gender": "",
          "birth_date": "",
          "national_id": "",
          "phone": "",
          "email": "",
          "address": ""
        }
        """
    )
    consent = models.JSONField(help_text="Patient consent data: ")
    indication = models.JSONField(help_text="Medical indication data: ")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return str(self.patient_id)
