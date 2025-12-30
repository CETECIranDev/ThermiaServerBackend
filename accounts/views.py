from django.shortcuts import render
from .serializers import *
from .models import *
import uuid
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics, permissions, status, views
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import *
import logging
from django.contrib.auth import get_user_model
from drf_spectacular.openapi import AutoSchema
from rest_framework import viewsets
from rest_framework import serializers
from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)

class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT login view that updates user's last login time
    after successful authentication.
    """
    schema = AutoSchema()

    serializer_class = CustomTokenObtainPairSerializer
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            try:
                User = get_user_model()
                user = User.objects.get(username=request.data['username'])
                user.last_login = timezone.now()
                user.save()
            except Exception as e:
                logger.error(e)

        return response


class UserLogoutView(views.APIView):
    """
    Logs out the authenticated user by blacklisting the refresh token.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # adds refresh token to the blacklist
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"message": "logged out successfully"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class ClinicCreateView(generics.CreateAPIView):
    """
    Allows admin users to create a new clinic.
    The clinic_id (UUID) is generated automatically by the Model.
    """
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    permission_classes = [IsAdmin]


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieves and updates the authenticated user's profile.
    Non-admin users are not allowed to change their role.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # you can't change your role if you're not an admin
        if 'role' in request.data and request.user.role != 'admin':
            return Response(
                {"error": "you do not have permission to perform this action"},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_update(serializer)

        return Response(serializer.data)


class ClinicListView(generics.ListAPIView):
    """
    Lists clinics based on user role.
    Admin users see all clinics, others see only their own clinic.
    """
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Clinic.objects.none()

        user = self.request.user
        if user.role != 'admin' and user.clinic:
            return Clinic.objects.filter(id=user.clinic.id)
        return Clinic.objects.all()


class ClinicUserViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for clinic-related users.
    Clinic manager can create and manage doctors or staff,
    but is NOT allowed to create admin or manufacturer users.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrClinicManager]

    def get_queryset(self):
        # Clinic manager can only see users belonging to their own clinic
        # Excludes the manager himself from the list
        # prevents swagger error
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()

        return User.objects.filter(clinic=self.request.user.clinic).exclude(id=self.request.user.id)

    def perform_create(self, serializer):
        # Get role from request data
        # Default role is set to 'doctor' if not provided
        role = self.request.data.get('role', 'doctor')

        # Prevent clinic manager from creating admin or manufacturer accounts
        if role in ['admin', 'manufacturer']:
            raise serializers.ValidationError({'role': 'You are not allowed to create admins.'})

        # Save user and force-assign them to the manager's clinic
        serializer.save(clinic=self.request.user.clinic,role=role)

    def perform_update(self, serializer):

        # Check if a new role is provided in the request
        new_role = self.request.data.get('role')

        # Prevent clinic manager from promoting users to admin or manufacturer
        if new_role and new_role in ['admin', 'manufacturer']:
            raise serializers.ValidationError({'role': 'You are not allowed to promote users to admin.'})

        # Save changes while forcing the user to stay in manager's clinic
        # This prevents moving users between clinics
        serializer.save(clinic=self.request.user.clinic)