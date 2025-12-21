from django.shortcuts import render
from .models import *
from .serializers import *
from rest_framework.decorators import action, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, viewsets, views, status
from rest_framework.response import Response
from .authentication import DeviceAuthentication
from accounts.permissions import IsAdmin, IsManufacturer, IsAdminOrDoctor,IsAdminOrManufacturer
from django.utils import timezone
from datetime import timedelta
import hashlib
import os
from django.http import FileResponse
import logging
from patient_sessions.models import Session,SessionLog

logger = logging.getLogger(__name__)

class DeviceViewSet(viewsets.ModelViewSet):
    """
    CRUD and management for devices.
    Admin/manufacturer can create/update/delete, others have restricted access.
    Supports lock/unlock actions.
    """
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    def get_permissions(self):
        if self.action in ['create', 'destroy', 'update', 'partial_update']:
            permission_classes = [IsAdminOrManufacturer]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        queryset = Device.objects.all()

        # access for human users
        if hasattr(user, 'role'):
            if user.role in ['admin', 'manufacturer']:
                return queryset
            elif user.role in ['doctor', 'clinic_admin'] and hasattr(user, 'clinic'):
                return queryset.filter(clinic=user.clinic)

        # access for devices themselves
        if hasattr(user, 'device_id'):
            return queryset.filter(device_id=user.device_id)

        # if none of the above, return empty queryset
        return Device.objects.none()

    def perform_create(self, serializer):
        device = serializer.save()
        # Log device creation
        logger.info(f"New device created: {device.serial_number} by user {self.request.user.username}")

    @action(detail=True, methods=['patch'])
    # Lock the device and its license
    def lock(self, request, pk=None):
        device = self.get_object()
        reason = request.data.get('reason', 'access restricted')
        device.is_locked = True
        device.status = 'locked'
        device.lock_reason = reason
        device.save()

        # update license if exists
        try:
            license_obj = device.license
            license_obj.status = 'locked'
            license_obj.save()
        except License.DoesNotExist:
            pass

        logger.info(f"Device {device.serial_number} locked by {request.user.username}, reason: {reason}")

        return Response({
            'status': 'success',
            'message': 'device locked!',
            'device_id': device.device_id,
            'serial_number': device.serial_number
        })

    @action(detail=True, methods=['patch'])
    # Unlock the device and its license
    def unlock(self, request, pk=None):
        device = self.get_object()
        device.is_locked = False
        device.status = 'active'
        device.lock_reason = ''
        device.save()

        # update license if exists
        try:
            license_obj = device.license
            license_obj.status = 'active'
            license_obj.save()
        except License.DoesNotExist:
            pass

        logger.info(f"Device {device.serial_number} unlocked by {request.user.username}")

        return Response({
            'status': 'success',
            'message': 'device unlocked!',
            'device_id': device.device_id,
            'serial_number': device.serial_number
        })


class LicenseCreateView(generics.CreateAPIView):
    """
    Create a new license for a device.
    Updates device status if license is active.
    """
    queryset = License.objects.all()
    serializer_class = LicenseSerializer
    permission_classes = [IsAdminOrManufacturer]

    def perform_create(self, serializer):
        license_obj = serializer.save()
        logger.info(f"License {license_obj.id} created for device {license_obj.device.serial_number} by {self.request.user.username}")

        # activating devices if license is active
        if license_obj.status == 'active' and license_obj.device:
            license_obj.device.status = 'active'
            license_obj.device.is_locked = False
            license_obj.device.save()


class FirmwareUploadView(generics.CreateAPIView):
    """
    Upload a firmware file for a device and calculate checksum.
    """
    queryset = Firmware.objects.all()
    serializer_class = FirmwareSerializer
    permission_classes = [IsAdminOrManufacturer]

    def perform_create(self, serializer):
        firmware_file = self.request.FILES.get('file_path')
        checksum = ''

        if firmware_file:
            # calculate checksum
            file_data = firmware_file.read()
            checksum = hashlib.sha256(file_data).hexdigest()
            firmware_file.seek(0)

        instance = serializer.save(checksum=checksum)
        logger.info(f"Firmware {instance.id} uploaded for device {instance.device.serial_number} by {self.request.user.username}")


class DeviceSyncView(views.APIView):
    """
    Handles device sync requests.
    Updates device info, checks license, processes sessions/logs, returns config and firmware updates.
    """
    authentication_classes = [DeviceAuthentication]
    permission_classes = []
    def post(self, request):
        device = request.user
        serializer = DeviceSyncSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # updating device
        data = serializer.validated_data
        device.firmware_version = data.get('firmware_version', device.firmware_version)
        device.last_heartbeat = timezone.now()
        device.last_online = timezone.now()
        device.save()

        # check license
        license_valid = False
        try:
            license = License.objects.get(device=device, status='active')
            if license.end_date >= timezone.now().date():
                license_valid = True
        except License.DoesNotExist:
            pass


        # check firmware update
        latest_firmware = Firmware.objects.filter(
            device=device,
            firmware_version__gt=device.firmware_version
        ).order_by('-firmware_version').first()

        # lock status
        is_locked = device.is_locked or not license_valid

        # process sessions
        sessions_data = data.get('sessions', [])
        if sessions_data:
            self.process_sessions(device, sessions_data)

        # process logs
        logs_data = data.get('logs', [])
        if logs_data:
            self.process_logs(device, logs_data)

        response_data = {
            'status': 'ok' if not is_locked else 'locked',
            'is_locked': is_locked,
            'lock_reason': device.lock_reason if is_locked else '',
            'license_valid': license_valid,
            'device_config': self.get_device_config(device),
        }

        # if new update is available
        if latest_firmware:
            response_data['firmware_update'] = {
                'version': latest_firmware.firmware_version,
                'url': request.build_absolute_uri(f'/api/devices/firmware/download/{latest_firmware.id}/'),
                'checksum': latest_firmware.checksum,
                'release_notes': latest_firmware.release_notes,
                'mandatory': True
            }

        logger.info(f"Device {device.serial_number} synced at {timezone.now()}")
        return Response(response_data)


    def process_sessions(self, device, sessions_data):
        """Process sessions sent by the device."""

        for session_data in sessions_data:
            try:
                Session.objects.create(
                    device=device,
                    clinic=device.clinic,
                    patient_id=session_data.get('patient_id'),
                    summary=session_data.get('summary', {}),
                    start_time=session_data.get('start_time', timezone.now()),
                    ended_at=session_data.get('ended_at'),
                    created_at=timezone.now()
                )
            except Exception as e:
                logger.error(f"Error processing session for device {device.serial_number}: {e}")



    def process_logs(self, device, logs_data):
        """Process logs sent by the device."""

        for log_data in logs_data:
            try:
                SessionLog.objects.create(
                    session_id=log_data.get('session_id'),
                    log_type=log_data.get('log_type', 'info'),
                    message=log_data.get('message', ''),
                    logged_at=log_data.get('logged_at', timezone.now()),
                    created_at=timezone.now()
                )
            except Exception as e:
                logger.error(f"Error processing log for device {device.serial_number}: {e}")


    def get_device_config(self, device):
        """Return device configuration."""
        return {
            'sync_interval': 300,
            'max_retry_count': 3,
            'log_level': 'info',
            'features': self.get_device_features(device)
        }

    def get_device_features(self, device):
        """Return enabled features for the device."""
        features = {
            'auto_update': True,
            'remote_diagnostics': True,
            'data_encryption': True,
        }
        try:
            license_obj = License.objects.filter(device=device).first()
            if license_obj and license_obj.license_type == 'full':
                features['advanced_reporting'] = True
                features['multi_user'] = True
        except:
            pass

        return features



class FirmwareDownloadView(views.APIView):
    """
    Secure firmware download endpoint for devices.
    Checks device authorization and file integrity before sending.
    """
    authentication_classes = [DeviceAuthentication]
    permission_classes = []

    def get(self, request, firmware_id):
        device = request.user
        try:
            firmware = Firmware.objects.get(id=firmware_id)

            # checks if device has firmware
            if firmware.device != device:
                logger.warning(f"Device {device.serial_number} tried unauthorized firmware access: {firmware_id}")
                return Response({'error': 'access denied to firmware'}, status=status.HTTP_403_FORBIDDEN)

            # opening file
            file_path = firmware.file_path.path
            if not os.path.exists(file_path):
                return Response({'error': 'firmware file not found'}, status=status.HTTP_404_NOT_FOUND)

            # reading file
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # checks checksum
            calculated_checksum = hashlib.sha256(file_data).hexdigest()
            if calculated_checksum != firmware.checksum:
                return Response({'error': 'checksum file is invalid'},status=status.HTTP_400_BAD_REQUEST)

            # send file
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            response['X-Checksum'] = firmware.checksum

            return response

        except Firmware.DoesNotExist:
            return Response({'error': 'Firmware not found'},status=status.HTTP_404_NOT_FOUND)
