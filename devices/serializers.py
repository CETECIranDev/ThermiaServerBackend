from rest_framework import serializers
from .models import Device,License,Firmware
from accounts.serializers import ClinicSerializer
from accounts.models import Clinic
from datetime import timedelta, timezone
import hashlib
import secrets
class DeviceSerializer(serializers.ModelSerializer):
    """
    Serializer for Device.
    Handles creation with optional clinic assignment, random API key,
    and default trial license.
    """
    clinic = ClinicSerializer(read_only=True)
    clinic_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Device
        fields = [
            'device_id', 'serial_number', 'clinic', 'clinic_id',
            'firmware_version', 'status', 'lock_reason',
            'last_heartbeat', 'last_online', 'api_key', 'created_at'
        ]
        read_only_fields = ['device_id', 'api_key', 'created_at']

    def create(self, validated_data):
        clinic_id = validated_data.pop('clinic_id', None)

        if clinic_id:
            try:
                clinic = Clinic.objects.get(clinic_id=clinic_id)
                validated_data['clinic'] = clinic
            except Clinic.DoesNotExist:
                raise serializers.ValidationError({'clinic_id': 'clinic does not exist'})

        # create random API Key
        api_key = secrets.token_urlsafe(32)
        validated_data['api_key'] = api_key
        device = Device.objects.create(**validated_data)

        # create license(default=trial)
        License.objects.create(
            device=device,
            license_type='trial',
            status='active',
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=30)).date()
        )
        return device


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
    firmware_version = serializers.CharField(max_length=255)
    status = serializers.CharField(max_length=50, required=False)
    sessions = serializers.JSONField(required=False)
    logs = serializers.JSONField(required=False)
