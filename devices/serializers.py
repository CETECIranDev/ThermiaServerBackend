from rest_framework import serializers
from .models import Device,License,Firmware
from accounts.serializers import ClinicSerializer
from accounts.models import Clinic
from datetime import timedelta, timezone
from django.utils.timesince import timesince
import hashlib
import secrets

class DeviceSerializer(serializers.ModelSerializer):
    """
    Serializer optimized for Frontend Display.
    Includes computed fields for status, usage, license info, and human-readable times.
    """
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    connection_status = serializers.SerializerMethodField()
    last_used_human = serializers.SerializerMethodField() # human-readable last used
    license_info = serializers.SerializerMethodField()
    software_version = serializers.CharField(source='firmware_version', read_only=True)
    clinic_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Device
        fields = [
            'device_id',
            'serial_number',
            'device_type',
            'category',
            'clinic_name',
            'clinic_id',
            'status',
            'software_version',
            'license_info',
            'installation_date',
            'last_service_date',
            'last_used_human',
            'connection_status',
            'is_locked',
            'lock_reason',
            'created_at'
        ]
        read_only_fields = ['device_id', 'created_at', 'api_key']

    def get_connection_status(self, obj):
        """
        Determine if the device is currently connected.
        If the last heartbeat was within 5 minutes, consider it connected.
        """
        if obj.last_heartbeat:
            if timezone.now() - obj.last_heartbeat < timedelta(minutes=5):
                return "connected"
        return "disconnected"

    def get_last_used_human(self, obj):
        """
        Return a human-readable string for the last time the device was online.
        Example: '10 minutes ago', '3 hours ago'
        """
        if obj.last_online:
            return f"{timesince(obj.last_online)} ago"
        return "Never"

    def get_license_info(self, obj):
        """
        Return information about the currently active license, if any.
        Shows license type and expiration date. Returns 'No Active License' if none.
        """
        active_license = obj.licenses.filter(
            status='active',
            end_date__gte=timezone.now().date()
        ).first()

        if active_license:
            return f"{active_license.get_license_type_display()} (Expires: {active_license.end_date})"
        return "No Active License"

    def create(self, validated_data):
        """
        Override creation to:
        1. Attach the device to a clinic if 'clinic_id' is provided.
        2. Generate a random API key for the device.
        """
        clinic_id = validated_data.pop('clinic_id', None)
        if clinic_id:
            try:
                clinic = Clinic.objects.get(clinic_id=clinic_id)
                validated_data['clinic'] = clinic
            except Clinic.DoesNotExist:
                raise serializers.ValidationError({'clinic_id': 'clinic does not exist'})

        # Generate a secure random API key for the device
        api_key = secrets.token_urlsafe(32)
        validated_data['api_key'] = api_key

        return super().create(validated_data)


class LicenseSerializer(serializers.ModelSerializer):
    """
    Serializer for License.
    Validates end date and ensures no duplicate active license exists for a device.
    """
    device_serial = serializers.CharField(source='device.serial_number', read_only=True)

    class Meta:
        model = License
        fields = [
            'id', 'device', 'device_serial', 'status',
            'license_type', 'start_date', 'end_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        device = data.get('device')
        license_type = data.get('license_type')
        end_date = data.get('end_date')

        # datetime validation
        if end_date and end_date < timezone.now().date():
            raise serializers.ValidationError('end_date must be in the future')

        # checks if device is already licensed
        if device:
            active_license = License.objects.filter(device=device,status='active').exists()
            if active_license and self.instance is None:
                raise serializers.ValidationError('this device is already licensed')

        return data


class FirmwareSerializer(serializers.ModelSerializer):
    """
    Serializer for Firmware.
    Ensures firmware version is unique per device.
    """
    device_serial = serializers.CharField(source='device.serial_number', read_only=True)

    class Meta:
        model = Firmware
        fields = [
            'id', 'device', 'device_serial', 'firmware_version',
            'file_path', 'release_notes', 'checksum', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        device = data.get('device')
        firmware_version = data.get('firmware_version')
        # checks if firmware is unique
        if Firmware.objects.filter(device=device,firmware_version=firmware_version).exists():
            raise serializers.ValidationError('this version of firmware already exists')

        return data

class DeviceSyncSerializer(serializers.Serializer):
    """
    Serializer for device sync data, including firmware version, status,
    sessions, and logs.
    """
    serial = serializers.CharField(max_length=255)
    fw_ver = serializers.CharField(max_length=255, required=False) # Optional because naming varies
    firmware_version = serializers.CharField(max_length=255, required=False)
    status = serializers.CharField(max_length=50, required=False)
    sessions = serializers.JSONField(required=False)
    logs = serializers.JSONField(required=False)