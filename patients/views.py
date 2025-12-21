from django.shortcuts import render
from rest_framework import generics, views, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
import qrcode
from io import BytesIO
import base64
import uuid
import json
from .models import Patient,PatientToken
from .serializers import PatientSerializer, PatientTokenSerializer
from accounts.permissions import IsAdminOrDoctor, ClinicObjectPermission
import secrets
from datetime import timedelta, timezone

class PatientCreateView(generics.CreateAPIView):
    """
    Allows admin or doctor users to create a new patient.
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAdminOrDoctor]
    def perform_create(self, serializer):
        patient = serializer.save()
        print(f"new patient created: {patient.patient_id} by: {self.request.user.username}")


class PatientListView(generics.ListAPIView):
    """
    Lists patients with filtering and search.
    Non-admin users see only patients from their clinic.
    """
    serializer_class = PatientSerializer
    permission_classes = [IsAdminOrDoctor]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['clinic']
    ordering_fields = ['created_at']
    def get_queryset(self):
        user = self.request.user
        queryset = Patient.objects.all()
        # you can only see the clinic patients if you're not an admin
        if user.role != 'admin' and user.clinic:
            queryset = queryset.filter(clinic=user.clinic)

        # searching filter
        search_term = self.request.query_params.get('search', '')
        if search_term:
            queryset = queryset.filter(
                Q(personal_data__icontains=search_term) |
                Q(patient_id__icontains=search_term)
            )
        # filtering name
        first_name = self.request.query_params.get('first_name', '')
        if first_name:
            queryset = queryset.filter(personal_data__first_name__icontains=first_name)

        # filtering national_id
        national_id = self.request.query_params.get('national_id', '')
        if national_id:
            queryset = queryset.filter(personal_data__national_id__icontains=national_id)

        return queryset.order_by('-created_at')


class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a patient.
    Access is restricted based on user role and clinic.
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAdminOrDoctor, ClinicObjectPermission]
    lookup_field = 'patient_id'

    def get_queryset(self):
        user = self.request.user
        queryset = Patient.objects.all()
        # you can only see the clinic patients if you're not an admin
        if user.role != 'admin' and user.clinic:
            queryset = queryset.filter(clinic=user.clinic)
        return queryset


class GeneratePatientTokenView(views.APIView):
    """
    Generates a temporary token for a patient and a QR code.
    Only accessible by admin or doctor users for their own clinic.
    """
    permission_classes = [IsAdminOrDoctor]
    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(patient_id=patient_id)

            # access check
            user = request.user
            if user.role != 'admin' and patient.clinic != user.clinic:
                return Response(
                    {'error': 'access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # clinic license check
            clinic = patient.clinic
            license_valid = True
            if not license_valid:
                return Response(
                    {'error': 'clinic license is invalid'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # creates random token
            token_str = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(hours=24)

            # saves token in database
            # ****it must be saved in redis*****
            # deletes patient's previous tokens
            PatientToken.objects.filter(patient=patient).delete()

            PatientToken.objects.create(
                patient=patient,
                token=token_str,
                clinic_id=str(clinic.clinic_id),
                expires_at=expires_at
            )

            # creates QR Code data
            qr_data = {
                'patient_id': str(patient_id),
                'token': token_str,
                'clinic_id': str(clinic.clinic_id),
                'timestamp': timezone.now().isoformat()
            }
            qr_json = json.dumps(qr_data)

            # convert QR Code to image
            qr = qrcode.make(qr_json)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            buffer.seek(0)
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()

            # sends response
            response_data = {
                'token': token_str,
                'qr_code': f"data:image/png;base64,{qr_base64}",
                'qr_data': qr_json,
                'expires_in': 24,
                'patient_info': {
                    'patient_id': str(patient_id),
                    'clinic_name': clinic.name,
                    'first_name': patient.personal_data.get('first_name'),
                    'last_name': patient.personal_data.get('last_name'),
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)


        except Patient.DoesNotExist:
            return Response(
                {'error': 'patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            print(f"Error generating token: {e}")
            return Response(
                {'error': 'Internal Server Error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

