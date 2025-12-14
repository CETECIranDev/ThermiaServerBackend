from django.db import models
import uuid

class Device(models.Model):
    """
    Represents a physical device registered in the system,
    associated with a clinic and tracked by status and firmware.
    """
    device_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    serial_number = models.CharField(max_length=255)
    clinic = models.ForeignKey('accounts.Clinic', on_delete=models.SET_NULL,null=True, related_name='devices')
    firmware_version = models.CharField(max_length=255)
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('locked', 'Locked'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    lock_reason = models.TextField(blank=True, null=True)
    last_heartbeat = models.DateTimeField(blank=True, null=True)
    last_online = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.serial_number


class License(models.Model):
    """
    Manages licensing information for a device,
    including type, status, and validity period.
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='licenses')
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('locked', 'Locked'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    LICENSE_TYPE_CHOICES = (
        ('trial', 'Trial'),
        ('full', 'Full'),
    )
    license_type = models.CharField(max_length=10, choices=LICENSE_TYPE_CHOICES)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.device.serial_number} - {self.license_type}"


class Firmware(models.Model):
    """
    Stores firmware versions available for devices.
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='firmwares')
    firmware_version = models.CharField(max_length=255,unique=True)
    file_path = models.FileField(upload_to='firmware/')
    release_notes = models.TextField(blank=True, null=True)
    checksum = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.firmware_version