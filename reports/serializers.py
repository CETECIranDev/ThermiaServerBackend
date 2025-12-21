from rest_framework import serializers
from .models import ReportGeneration

class ReportGenerationSerializer(serializers.ModelSerializer):
    """Serializer for ReportGeneration model."""
    class Meta:
        model = ReportGeneration
        fields = '__all__'

class ReportRequestSerializer(serializers.Serializer):
    """
    Serializer to validate report generation requests.
    """
    clinic_id = serializers.CharField(required=False)
    patient_id = serializers.UUIDField(required=False)

    # Report type must be one of the allowed choices
    report_type = serializers.ChoiceField(choices=ReportGeneration.REPORT_TYPE_CHOICES)

    # Output format
    FORMAT_CHOICES = (('pdf', 'PDF'), ('excel', 'Excel'))
    format = serializers.ChoiceField(choices=FORMAT_CHOICES, default='pdf')

    # Optional date range
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    # Additional parameters (JSON)
    parameters = serializers.DictField(required=False, default=dict)

    def validate(self, data):
        """Validate that start_date is not after end_date."""
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and start > end:
            raise serializers.ValidationError("Start date cannot be after end date.")
        return data