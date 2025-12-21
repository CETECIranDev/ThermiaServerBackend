from rest_framework import serializers
from .models import User, Clinic
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ['clinic_id', 'name', 'address', 'phone', 'created_at']
        read_only_fields = ['clinic_id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    """
    Custom JWT serializer that includes user data in the token response.
    """
    clinic = ClinicSerializer(read_only=True)
    clinic_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name','role', 'clinic', 'clinic_id', 'is_active', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def create(self, validated_data):
        clinic_id = validated_data.pop('clinic_id', None)
        if clinic_id:
            try:
                clinic = Clinic.objects.get(clinic_id=clinic_id)
                validated_data['clinic'] = clinic
            except Clinic.DoesNotExist:
                raise serializers.ValidationError({'clinic_id': 'clinic not found!'})

        user = User.objects.create_user(**validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that includes user data in the token response.
    """
    def validate(self, attrs):
        # 1.validates username and password
        data = super().validate(attrs)

        # 2.creates token for user and adds custom claims
        refresh = self.get_token(self.user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)

        # 3.adds user info
        user_data = UserSerializer(self.user).data
        data['user'] = user_data

        return data


class LoginSerializer(serializers.Serializer):
    """
    Handles username and password authentication.
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)

            if user:
                if not user.is_active:
                    raise serializers.ValidationError('user account is disabled')
                data['user'] = user
            else:
                raise serializers.ValidationError('wrong username or password')
        else:
            raise serializers.ValidationError('username and passwords fields are required')

        return data
