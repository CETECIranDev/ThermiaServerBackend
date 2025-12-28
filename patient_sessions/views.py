from django.shortcuts import render
from rest_framework import generics, views, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta, datetime
import json
from .models import Session, SessionLog
from .serializers import SessionSerializer, SessionUploadSerializer, SessionLogSerializer
from accounts.permissions import IsAdminOrDoctor, ClinicObjectPermission
from devices.authentication import DeviceAuthentication
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncDate
from patients.models import Patient, PatientToken

class SessionUploadView(views.APIView):
    """
    Optimized endpoint to receive session and log batches from devices.
    Uses transaction.atomic to ensure either all records are saved or none.
    Logs are saved via bulk_create for high performance.
    """
    authentication_classes = [DeviceAuthentication]
    permission_classes = []

    def post(self, request):
        serializer = SessionUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        device = request.user
        sessions_data = data.get('sessions', [])
        logs_data = data.get('logs', [])

        created_sessions_count = 0
        session_map = {}  # for connecting logs to sessions

        try:
            #  یا همه ذخیره می‌شوند یا هیچکدام (Transaction)
            with transaction.atomic():

                # save session
                for s_data in sessions_data:
                    session = self.create_session(device, s_data)
                    # keep device reference to connect logs
                    session_map[s_data['reference']] = session
                    created_sessions_count += 1

                # preparing logs
                log_objects = []
                for l_data in logs_data:
                    ref = l_data.get('session_reference')
                    session = session_map.get(ref)

                    if session:
                        log_objects.append(SessionLog(
                            session=session,
                            log_type=l_data['log_type'],
                            message=l_data['message'],
                            logged_at=l_data['logged_at'],
                            created_at=timezone.now()
                        ))

                # save logs(bulk create)
                if log_objects:
                    SessionLog.objects.bulk_create(log_objects)

            return Response({
                'status': 'success',
                'created_sessions': created_sessions_count,
                'created_logs': len(log_objects)
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_session(self, device, data):
        """
        Finds the patient by ID or temporary token (QR code) and creates a session.
        If no valid patient is found, session is still created without a patient.
        """
        patient = None

        # 1)if we get patient_id:
        if data.get('patient_id'):
            try:
                patient = Patient.objects.get(patient_id=data['patient_id'])
            except Patient.DoesNotExist:
                pass

        # 2)if we get patient QR Code:
        elif data.get('patient_token'):
            try:
                token_obj = PatientToken.objects.get(
                    token=data['patient_token'],
                    expires_at__gt=timezone.now()
                )
                patient = token_obj.patient
            except PatientToken.DoesNotExist:
                pass

        return Session.objects.create(
            patient=patient,
            device=device,
            clinic=device.clinic,
            summary=data.get('summary', {}),
            start_time=data['start_time'],
            ended_at=data.get('ended_at'),
            created_at=timezone.now()
        )


class SessionStatisticsView(views.APIView):
    """
    Dashboard statistics optimized for performance:
    - Uses single query with TruncDate for daily stats.
    - Provides total sessions, daily counts, and top devices.
    """
    permission_classes = [IsAdminOrDoctor]

    def get(self, request):
        user = request.user
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        if user.role == 'admin':
            queryset = Session.objects.all()
        else:
            queryset = Session.objects.filter(clinic=user.clinic)

        # we only keep sessions that are after start_date
        queryset = queryset.filter(start_time__gte=start_date)

        # counts total sessions
        total_sessions = queryset.count()

        # grouping by day in database
        # TruncDate('start_time') >> extracts session date
        # values('date') >> groups by date
        # annotate(count=Count('id')) >> counts sessions per day
        daily_stats_qs = queryset.annotate(date=TruncDate('start_time')).values('date').annotate(count=Count('id')).order_by('date')

        daily_stats = [
            {'date': item['date'].isoformat(), 'count': item['count']}
            for item in daily_stats_qs
        ]

        # device statistics
        device_stats = queryset.values('device__serial_number').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        response_data = {
            'total_sessions': total_sessions,
            'period_days': days,
            'daily_statistics': daily_stats,
            'top_devices': list(device_stats)
        }

        return Response(response_data)


class SessionDetailView(generics.RetrieveAPIView):
    """
    Retrieves detailed information of a specific session.
    Clinic-based access control is applied for non-admin users.
    """
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAdminOrDoctor, ClinicObjectPermission]

    def get_queryset(self):
        user = self.request.user
        if user.role != 'admin' and user.clinic:
            return Session.objects.filter(clinic=user.clinic)
        return Session.objects.all()


class SessionLogsView(generics.ListAPIView):
    """
    Lists all logs related to a specific session.
    Access is restricted based on clinic ownership.
    """
    serializer_class = SessionLogSerializer
    permission_classes = [IsAdminOrDoctor, ClinicObjectPermission]

    def get_queryset(self):
        session_id = self.kwargs['session_id']
        user = self.request.user

        try:
            session = Session.objects.get(id=session_id)
            if user.role != 'admin' and session.clinic != user.clinic:
                return SessionLog.objects.none()
        except Session.DoesNotExist:
            return SessionLog.objects.none()

        return SessionLog.objects.filter(session_id=session_id).order_by('-logged_at')



class SessionHistoryView(generics.ListAPIView):
    """
    Returns treatment history.
    Scenario 1: Get specific patient history via URL (e.g., /history/UUID/)
    Scenario 2: Doctor searches/filters via Query Params (e.g., /history/?patient_id=UUID)
    """
    serializer_class = SessionSerializer
    permission_classes = [IsAdminOrDoctor]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]

    filterset_fields = ['device', 'clinic', 'status']
    ordering_fields = ['start_time', 'duration', 'cost']

    search_fields = ['patient__personal_data__first_name', 'patient__personal_data__last_name',
                     'patient__personal_data__national_id']

    def get_queryset(self):
        user = self.request.user

        # 1. Get patient_id either from URL kwargs or query params
        patient_id = self.kwargs.get('patient_id') or self.request.query_params.get('patient_id')

        # 2. Base queryset: sessions of the user's clinic
        # Admins can see all sessions; others only their clinic
        if user.role == 'admin':
            queryset = Session.objects.all()
        elif user.clinic:
            queryset = Session.objects.filter(clinic=user.clinic)
        else:
            return Session.objects.none()

        # 3. Filter by specific patient if provided
        if patient_id:
            queryset = queryset.filter(patient__patient_id=patient_id)

        # 4. Optional date filters
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)

        return queryset.order_by('-start_time')
