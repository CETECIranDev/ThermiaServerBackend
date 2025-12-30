from django.db import models
import uuid

class Device(models.Model):
    """
    Represents a physical device registered in the system,
    associated with a clinic and tracked by status and firmware.
    """
    device_id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4, editable=False)
    serial_number = models.CharField(max_length=255, unique=True)
    clinic = models.ForeignKey('accounts.Clinic', on_delete=models.SET_NULL,null=True, related_name='devices')
    manufacturer = models.ForeignKey('accounts.User', on_delete=models.PROTECT,related_name='manufactured_devices',null=True, blank=True)
    device_type = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    installation_date = models.DateField(null=True, blank=True)
    last_service_date = models.DateField(null=True, blank=True)
    firmware_version = models.CharField(max_length=255)
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('locked', 'Locked'),
        ('maintenance', 'Maintenance'),
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    lock_reason = models.TextField(blank=True, null=True)
    last_heartbeat = models.DateTimeField(blank=True, null=True)
    last_online = models.DateTimeField(blank=True, null=True)
    api_key = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.serial_number} ({self.device_type})"


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