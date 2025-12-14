from rest_framework import serializers
from .models import ReportGeneration

class ReportGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportGeneration
        fields = '__all__'

