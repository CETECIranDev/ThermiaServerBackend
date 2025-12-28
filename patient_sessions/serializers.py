from rest_framework import serializers
from .models import Session,SessionLog
from devices.models import Device

class SessionSummaryValidator(serializers.Serializer):
    """
    Validates the structure of the session summary JSON field.
    Used to ensure consistency of device-submitted data.
    """
    areas_treated = serializers.ListField(child=serializers.CharField(), required=False)
    parameters = serializers.DictField(required=False)
    extra_data = serializers.DictField(required=False)

class SessionSerializer(serializers.ModelSerializer):
    """
    Serializer for Session model.
    Optimized for Frontend Table Display.
    """
    summary = serializers.JSONField()
    patient_name = serializers.SerializerMethodField()
    patient_code = serializers.CharField(source='patient.patient_code', read_only=True)
    device_name = serializers.CharField(source='device.serial_number', read_only=True)
    duration_minutes = serializers.ReadOnlyField(source='duration')
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id',
            'formatted_date',
            'patient_name',
            'patient_code',
            'device_name',
            'duration_minutes',
            'cost',
            'status',
            'summary',
            'start_time',
            'ended_at',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_summary(self, value):
        """
        Validate structure of summary JSON
        using a dedicated summary validator.
        """
        validator = SessionSummaryValidator(data=value)
        if not validator.is_valid():
            raise serializers.ValidationError(validator.errors)
        return value

    def get_patient_name(self, obj):
        """
        Extract and format patient full name
        from personal_data JSON field.
        """
        if obj.patient and obj.patient.personal_data:
            first = obj.patient.personal_data.get('first_name', '')
            last = obj.patient.personal_data.get('last_name', '')
            return f"{first} {last}".strip() or "Unknown"
        return "Unknown"

    def get_formatted_date(self, obj):
        """
        Format session start time for frontend display.
        Example: 2025-12-27 14:30
        """
        return obj.start_time.strftime('%Y-%m-%d %H:%M')

class SessionLogSerializer(serializers.ModelSerializer):
    """
    Serializer for individual session logs.
    """
    class Meta:
        model = SessionLog
        fields = '__all__'


class LogUploadItemSerializer(serializers.Serializer):
    """
    Single log item sent from device.
    Uses a temporary session reference to link logs to sessions.
    """
    session_reference = serializers.CharField(help_text="Temporary reference to map log to session")
    log_type = serializers.ChoiceField(choices=SessionLog.LOG_TYPE_CHOICES)
    message = serializers.CharField()
    logged_at = serializers.DateTimeField()

class SessionUploadItemSerializer(serializers.Serializer):
    """
    Single session item sent from device.
    Includes a unique reference for mapping related logs.
    """
    reference = serializers.CharField(help_text="Device-side unique reference for session")
    patient_id = serializers.UUIDField(required=False, allow_null=True)
    patient_token = serializers.CharField(required=False, allow_null=True)
    start_time = serializers.DateTimeField()
    ended_at = serializers.DateTimeField(required=False, allow_null=True)
    summary = serializers.JSONField()

class SessionUploadSerializer(serializers.Serializer):
    """
    Main serializer for batch upload of sessions and logs from device.
    """
    sessions = serializers.ListField(child=SessionUploadItemSerializer())
    logs = serializers.ListField(child=LogUploadItemSerializer(), required=False)

    def validate(self, data):
        sessions = data.get('sessions', [])
        logs = data.get('logs', [])

        # collect all session references sent by device
        session_refs = {session['reference'] for session in sessions}

        # check that every log refers to a valid session reference
        for log in logs:
            if log['session_reference'] not in session_refs:
                raise serializers.ValidationError(
                    f"Log references unknown session: {log['session_reference']}"
                )

        return data
