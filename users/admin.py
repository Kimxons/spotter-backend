from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'driver_license', 'phone_number', 'preferred_units')
    search_fields = ('user__username', 'user__email', 'company_name')
    list_filter = ('preferred_units',)

