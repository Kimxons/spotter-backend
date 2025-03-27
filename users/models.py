from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class UserProfile(models.Model):
    """
    Extended user profile with additional driver information.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company_name = models.CharField(max_length=255, blank=True)
    driver_license = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Preferences
    preferred_units = models.CharField(
        max_length=10,
        choices=[('miles', 'Miles'), ('kilometers', 'Kilometers')],
        default='miles'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
    
    def __str__(self):
        return f"Profile for {self.user.username}"

