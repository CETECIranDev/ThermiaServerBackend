from django.db import models
from django.contrib.auth.models import AbstractUser

class Clinic(models.Model):
    """
    Represents a medical clinic.
    """
    clinic_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=250)
    address = models.TextField()
    phone = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name

class User(AbstractUser):
    """
    Custom user model with role-based access.
    """
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('manufacturer', 'Manufacturer'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    clinic = models.ForeignKey(Clinic,null=True,blank=True, on_delete=models.SET_NULL,related_name='users')

    def __str__(self):
        return f"{self.username} - ({self.role})"

