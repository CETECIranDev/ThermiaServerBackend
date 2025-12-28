from django.shortcuts import render
from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
import os
from .models import ReportGeneration
from .serializers import ReportGenerationSerializer, ReportRequestSerializer
from accounts.permissions import IsAdminOrDoctor,IsManagerOrDoctor
from .tasks import generate_report_task
from accounts.models import Clinic
from patients.models import Patient
from devices.models import Device
from patient_sessions.models import Session
from drf_spectacular.utils import extend_schema, OpenApiTypes

class ReportGenerateView(views.APIView):
    """
    Create a new report request.
    The report is generated asynchronously using Celery.
    """
    permission_classes = [IsManagerOrDoctor ]

    def post(self, request):
        # Validate incoming request data
        serializer = ReportRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = request.user

        # Determine target clinic
        clinic_id = data.get('clinic_id')
        target_clinic = None

        if not clinic_id:
            # Use user's clinic if not explicitly provided
            if user.clinic:
                target_clinic = user.clinic
            else:
                return Response({'error': 'Clinic ID required for admins without clinic'}, status=400)
        else:
            # Fetch clinic by provided ID
            try:
                target_clinic = Clinic.objects.get(clinic_id=clinic_id)
            except Clinic.DoesNotExist:
                return Response({'error': 'Clinic not found'}, status=404)

        # Access control: non-admin users can only access their own clinic
        if user.role != 'admin' and target_clinic != user.clinic:
            return Response({'error': 'Access denied to this clinic'}, status=403)

        # Create initial report record
        report = ReportGeneration.objects.create(
            clinic=target_clinic,
            patient_id=data.get('patient_id'),
            generated_by=user,
            report_type=data['report_type'],
            created_at=timezone.now()
        )

        # Prepare parameters for background task
        task_params = {
            'report_id': report.id,
            'report_type': data['report_type'],
            'file_format': data['format'],
            'start_date': str(data.get('start_date')) if data.get('start_date') else None,
            'end_date': str(data.get('end_date')) if data.get('end_date') else None,
            'parameters': data.get('parameters', {})
        }

        # Send task to Celery queue (non-blocking)
        generate_report_task.delay(**task_params)

        return Response({
            'status': 'processing',
            'message': 'Report generation started',
            'report_id': report.id,
            'estimated_time': 'Depends on data size'
        }, status=status.HTTP_202_ACCEPTED)


class ReportListView(generics.ListAPIView):
    """
    List generated reports.
    Admins see all reports, doctors see only their clinic reports.
    """
    serializer_class = ReportGenerationSerializer
    permission_classes = [IsManagerOrDoctor]
    def get_queryset(self):
        user = self.request.user

        # Admin sees all reports, others only their clinic
        if user.role == 'admin':
            queryset = ReportGeneration.objects.all()
        else:
            queryset = ReportGeneration.objects.filter(clinic=user.clinic)

        # Optional filters
        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)

        return queryset.order_by('-created_at')


class ReportDownloadView(views.APIView):
    """
    Secure download endpoint for generated report files.
    """
    permission_classes = [IsManagerOrDoctor]

    def get(self, request, report_id):
        try:
            report = ReportGeneration.objects.get(id=report_id)
            user = request.user

            # Access check
            if user.role != 'admin' and report.clinic != user.clinic:
                return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

            # Check if file exists and is ready
            if not report.file_path or not os.path.exists(report.file_path.path):
                return Response({'error': 'File not ready or missing'}, status=status.HTTP_404_NOT_FOUND)

            # Stream file using FileResponse (memory efficient)
            response = FileResponse(open(report.file_path.path, 'rb'))
            filename = os.path.basename(report.file_path.name)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except ReportGeneration.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)


class ReportStatusView(views.APIView):
    """
    Check report generation status.
    Used by frontend polling.
    """
    permission_classes = [IsManagerOrDoctor]

    def get(self, request, report_id):
        try:
            report = ReportGeneration.objects.get(id=report_id)
            user = request.user

            # Access check
            if user.role != 'admin' and report.clinic != user.clinic:
                return Response({'error': 'Access denied'}, status=403)

            # Determine readiness based on file existence
            is_ready = bool(report.file_path and os.path.exists(report.file_path.path))

            return Response({
                'report_id': report.id,
                'status': 'ready' if is_ready else 'processing',
                'created_at': report.created_at,
                'download_url': f"/api/reports/{report.id}/download/" if is_ready else None
            })

        except ReportGeneration.DoesNotExist:
            return Response({'error': 'Report not found'}, status=404)


class ClinicReportView(views.APIView):
    """
    Real-time clinic dashboard statistics (last 30 days).
    """
    permission_classes = [IsManagerOrDoctor]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})

    def get(self, request):
        user = request.user
        clinic_id = request.query_params.get('clinic_id')

        # Resolve target clinic
        target_clinic = None
        if not clinic_id:
            if user.clinic:
                target_clinic = user.clinic
            else:
                return Response({'error': 'Clinic ID required'}, status=400)
        else:
            try:
                target_clinic = Clinic.objects.get(clinic_id=clinic_id)
            except Clinic.DoesNotExist:
                return Response({'error': 'Clinic not found'}, status=404)

        # Access check
        if user.role != 'admin' and target_clinic != user.clinic:
            return Response({'error': 'Access denied'}, status=403)

        # Time window for statistics
        days_30_ago = timezone.now() - timedelta(days=30)

        # Basic counts
        total_patients = Patient.objects.filter(clinic=target_clinic).count()
        new_patients = Patient.objects.filter(clinic=target_clinic, created_at__gte=days_30_ago).count()
        total_devices = Device.objects.filter(clinic=target_clinic).count()
        active_devices = Device.objects.filter(clinic=target_clinic, status='active').count()

        # Session statistics
        sessions_qs = Session.objects.filter(clinic=target_clinic, start_time__gte=days_30_ago)
        total_sessions = sessions_qs.count()

        # Daily trend aggregated by database
        daily_stats_qs = sessions_qs.annotate(date=TruncDate('start_time')).values('date').annotate(count=Count('id')).order_by('date')

        daily_stats = [
            {'date': item['date'].isoformat(), 'count': item['count']}
            for item in daily_stats_qs
        ]

        return Response({
            'clinic_name': target_clinic.name,
            'generated_at': timezone.now().isoformat(),
            'stats': {
                'patients': {
                    'total': total_patients,
                    'new_30d': new_patients
                },
                'devices': {
                    'total': total_devices,
                    'active': active_devices
                },
                'sessions': {
                    'total_30d': total_sessions,
                    'daily_trend': daily_stats
                }
            }
        })
