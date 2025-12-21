from rest_framework import authentication, permissions
from rest_framework.exceptions import AuthenticationFailed
from devices.models import Device
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions

# JWT Authentication for users
class UserJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # checks JWT
        header = self.get_header(request)
        if header is None:
            return None
        # extract token
        raw_token = self.get_raw_token(header)
        # validate token
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

# Device API Key Authentication
class DeviceAuthentication(authentication.BaseAuthentication):
    """authentication with API Key"""
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None

        try:
            device = Device.objects.get(api_key=api_key, status='active')
            return (device, None)

        except Device.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')


class IsDeviceOwner(permissions.BasePermission):
    """
    Allows access only to Device owned users.
    Device owner is the clinic.
    Admin → full access
    Clinic users → devices of their clinic
    Device → only itself
    """

    def has_object_permission(self, request, view, obj):
        actor = request.user

        # Device authenticating itself
        if isinstance(actor, Device):
            return actor == obj

        # Admin user
        if hasattr(actor, 'role') and actor.role == 'admin':
            return True

        # Clinic user
        if hasattr(actor, 'clinic'):
            return obj.clinic == actor.clinic

        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """admin>>> POST/PUT/DELETE, others>>>GET"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
