from rest_framework import serializers
from .models import Patient
from accounts.serializers import ClinicSerializer
from accounts.models import Clinic
import json

class PersonalDataValidator(serializers.Serializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    gender = serializers.CharField(required=True)
    birth_date = serializers.CharField(required=True)
    national_id = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    address = serializers.CharField(required=True)


class PatientSerializer(serializers.ModelSerializer):
    """
    Serializer for patient data.
    Handles patient creation with clinic assignment and
    validates required personal data fields.
    """
    clinic = ClinicSerializer(read_only=True)
    clinic_id = serializers.CharField(write_only=True)

    class Meta:
        model = Patient
        fields = ['patient_id', 'clinic', 'clinic_id','personal_data', 'consent', 'indication', 'created_at']
        read_only_fields = ['patient_id', 'created_at']

    def validate_personal_data(self, value):
        # validating required fields in personal data
        validator = PersonalDataValidator(data=value)
        if not validator.is_valid():
            raise serializers.ValidationError(validator.errors)

        # checks if national_id is unique
        clinic_id = self.initial_data.get('clinic_id')
        national_id = value.get('national_id')
        if clinic_id and national_id:
            existing = Patient.objects.filter(clinic__clinic_id=clinic_id,personal_data__national_id=national_id).exists()
            if existing:
                raise serializers.ValidationError('national_id is already taken!')
        return value


    def create(self, validated_data):
        clinic_id = validated_data.pop('clinic_id')
        try:
            clinic = Clinic.objects.get(clinic_id=clinic_id)
        except Clinic.DoesNotExist:
            raise serializers.ValidationError({'clinic_id': 'clinic does not exist!'})

        patient = Patient.objects.create(
            clinic=clinic,
            personal_data=validated_data['personal_data'],
            consent=validated_data.get('consent', {}),
            indication=validated_data.get('indication', {})
        )
        return patient

class PatientTokenSerializer(serializers.Serializer):
    """
    Serializer to generate a token for a patient with a purpose and expiry.
    Checks access permissions based on user role and clinic.
    """
    patient_id = serializers.UUIDField()
    purpose = serializers.CharField(max_length=100, default='treatment')
    expires_in = serializers.IntegerField(default=24)

    def validate(self, data):
        patient_id = data['patient_id']
        try:
            patient = Patient.objects.get(patient_id=patient_id)
            # checks if user has access to patient(only admin and clinic users can create token for patients)
            user = self.context['request'].user
            if user.role != 'admin' and patient.clinic != user.clinic:
                raise serializers.ValidationError('access denied')
            data['patient'] = patient
            return data
        except Patient.DoesNotExist:
            raise serializers.ValidationError('patient does not exist!')
