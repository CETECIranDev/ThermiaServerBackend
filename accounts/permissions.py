from rest_framework import permissions
from rest_framework.permissions import BasePermission

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsDoctor(permissions.BasePermission):
    """
    Allows access only to doctor users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "doctor"

class IsManufacturer(permissions.BasePermission):
    """
    Allows access only to manufacturer users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "manufacturer"


class IsAdminOrDoctor(permissions.BasePermission):
    """
    Allows access to admin and doctor users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'doctor']


class ClinicObjectPermission(permissions.BasePermission):
    """
    Object-level permission based on clinic ownership.
    Admin users have full access.
    Other users can only access objects related to their own clinic.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admin has access to all objects
        if user.role == 'admin':
            return True

        # Object is directly related to a clinic
        if hasattr(obj, 'clinic'):
            return obj.clinic == user.clinic

        # Object is related to a patient (patient belongs to a clinic)
        if hasattr(obj, 'patient'):
            return obj.patient.clinic == user.clinic

        # Object is related to a device (device belongs to a clinic)
        if hasattr(obj, 'device'):
            return obj.device.clinic == user.clinic

        return False


class IsAdminOrManufacturer(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'role') and request.user.role in ['admin', 'manufacturer']
