from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
import pandas as pd
import io
import datetime
from .models import ReportGeneration
from patient_sessions.models import Session
from patients.models import Patient
from devices.models import Device

@shared_task
def generate_report_task(report_id, report_type, file_format, start_date=None, end_date=None, parameters=None):
    """
    Celery task responsible for generating report files (Excel / CSV)
    based on database data and saving them to ReportGeneration model.
    """
    try:
        # 1. Fetch report record from database
        # This record was created earlier by the API
        report = ReportGeneration.objects.get(id=report_id)
        clinic = report.clinic

        # 2. Build base queryset
        # Default: all sessions related to the clinic
        queryset = Session.objects.filter(clinic=clinic)

        # Apply optional date filters
        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)

        # 3. Prepare container for extracted report rows
        data_list = []

        if report_type == 'patient_history':
            # Patient-specific session history report
            # Optional patient filter from parameters or report record
            target_patient_id = parameters.get('patient_id') if parameters else None
            if report.patient:
                queryset = queryset.filter(patient=report.patient)

            # Convert each session into a flat row (dict)
            for session in queryset:
                data_list.append({
                    'Session ID': session.id,
                    'Patient Name': f"{session.patient.personal_data.get('first_name', '')} "
                                    f"{session.patient.personal_data.get('last_name', '')}" if session.patient else 'Unknown',
                    'Device': session.device.serial_number if session.device else 'Unknown',
                    'Start Time': session.start_time.strftime('%Y-%m-%d %H:%M'),
                    'Duration (Min)': round((session.ended_at - session.start_time).seconds / 60,
                                            2) if session.ended_at else 0,
                    'Areas Treated': ", ".join(session.summary.get('areas_treated', [])) if session.summary else '-'
                })

        elif report_type == 'device_usage':
            # Device usage and performance report
            for session in queryset:
                data_list.append({
                    'Device Serial': session.device.serial_number if session.device else 'Unknown',
                    'Firmware': session.device.firmware_version if session.device else '-',
                    'Session Date': session.start_time.strftime('%Y-%m-%d'),
                    'Shots/Energy': session.summary.get('parameters', {}).get('total_energy', 0),  # مثال
                    'Status': 'Completed' if session.ended_at else 'Interrupted'
                })

        elif report_type == 'clinic_summary':
            # High-level clinic activity summary
            for session in queryset:
                data_list.append({
                    'Date': session.start_time.strftime('%Y-%m-%d'),
                    'Patient ID': str(session.patient.patient_id) if session.patient else '-',
                    'Device': session.device.serial_number if session.device else '-',
                    'Doctor': session.clinic.users.filter(
                        role='doctor').first().username if session.clinic.users.exists() else 'Admin',
                })

        else:
            # Fallback case if report type logic is not implemented
            data_list = [{'Info': 'No data logic defined for this report type'}]

        # 4. Convert collected rows into Pandas DataFrame
        df = pd.DataFrame(data_list)

        # Ensure the file is not empty (Excel cannot be totally empty)
        if df.empty:
            df = pd.DataFrame([{'Message': 'No data found for the selected period'}])

        # 5. Generate output file in memory (RAM)
        output_buffer = io.BytesIO()
        file_ext = 'xlsx'
        mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        # Default behavior: always generate Excel file
        # (PDF requires templates and font handling, so skipped here)

        if file_format == 'excel' or True:
            with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Report Data')
            file_ext = 'xlsx'

        # CSV support can be added later if needed
        # else:
        #     df.to_csv(output_buffer, index=False)
        #     file_ext = 'csv'

        # 6. Save generated file into FileField of ReportGeneration
        file_name = f"{report_type}_{timezone.now().strftime('%Y%m%d_%H%M')}.{file_ext}"
        report.file_path.save(file_name, ContentFile(output_buffer.getvalue()))
        report.save()
        return f"Report {report_id} generated successfully."

    except Exception as e:
        # Error handling (can be extended with status field in model)
        print(f"Error generating report {report_id}: {e}")
        return f"Failed: {str(e)}"