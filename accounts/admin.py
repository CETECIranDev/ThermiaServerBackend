from django.contrib import admin
from .models import *

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('clinic_id', 'name', 'phone', 'created_at')
    search_fields = ('name', 'phone')
    ordering = ('-created_at',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id','username', 'role', 'clinic')
    list_filter = ('role','clinic')
    search_fields = ('username', 'email')