import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Route(models.Model):
    """
    Model to store route information including start/end locations,
    distance, duration, and associated stops and logs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,blank=True, related_name='routes')
    
    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)
    total_distance = models.DecimalField(max_digits=10, decimal_places=2)  # in miles
    total_duration = models.CharField(max_length=100) 
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Route')
        verbose_name_plural = _('Routes')
    
    def __str__(self):
        return f"{self.start_location} to {self.end_location} ({self.total_distance} miles)"


class RouteStop(models.Model):
    """
    Model to store information about stops along a route,
    including location, type, arrival/departure times, etc.
    """
    STOP_TYPES = (
        ('start', 'Start'),
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
        ('rest', 'Rest'),
        ('fuel', 'Fuel'),
        ('overnight', 'Overnight'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    
    stop_type = models.CharField(max_length=20, choices=STOP_TYPES)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    arrival_time = models.CharField(max_length=100)
    departure_time = models.CharField(max_length=100)
    duration = models.CharField(max_length=100, blank=True, null=True)
    mileage = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # in miles
    
    # Coordinates for mapping
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['arrival_time']
        verbose_name = _('Route Stop')
        verbose_name_plural = _('Route Stops')
    
    def __str__(self):
        return f"{self.type} at {self.location}"


class LogDay(models.Model):
    """
    Model to store daily log information for a route,
    including date, locations, activities, and hours.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='logs')
    
    # Log details
    date = models.CharField(max_length=100)
    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)
    total_miles = models.DecimalField(max_digits=10, decimal_places=2)  # in miles
    shipping_documents = models.CharField(max_length=255)
    remarks = models.JSONField(default=list)  # List of remarks
    
    # Hours summary
    off_duty_hours = models.DecimalField(max_digits=5, decimal_places=2)
    sleeper_berth_hours = models.DecimalField(max_digits=5, decimal_places=2)
    driving_hours = models.DecimalField(max_digits=5, decimal_places=2)
    on_duty_not_driving_hours = models.DecimalField(max_digits=5, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date']
        verbose_name = _('Log Day')
        verbose_name_plural = _('Log Days')
    
    def __str__(self):
        return f"Log for {self.date}: {self.start_location} to {self.end_location}"


class LogActivity(models.Model):
    """
    Model to store individual activities within a log day,
    such as driving, rest periods, etc.
    """
    ACTIVITY_TYPES = (
        ('offDuty', 'Off Duty'),
        ('sleeperBerth', 'Sleeper Berth'),
        ('driving', 'Driving'),
        ('onDutyNotDriving', 'On Duty (Not Driving)'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    log_day = models.ForeignKey(LogDay, on_delete=models.CASCADE, related_name='activities')
    
    # Activity details
    type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    start_time = models.CharField(max_length=10)  # Format: "HH:MM"
    end_time = models.CharField(max_length=10)  # Format: "HH:MM"
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_time']
        verbose_name = _('Log Activity')
        verbose_name_plural = _('Log Activities')
    
    def __str__(self):
        return f"{self.type} from {self.start_time} to {self.end_time}"


class HOSRegulation(models.Model):
    """
    Model to store Hours of Service regulations,
    which can be updated as regulations change.
    """
    name = models.CharField(max_length=255)
    description = models.TextField()
    max_driving_hours = models.DecimalField(max_digits=5, decimal_places=2)
    max_duty_hours = models.DecimalField(max_digits=5, decimal_places=2)
    required_rest_hours = models.DecimalField(max_digits=5, decimal_places=2)
    cycle_hours = models.DecimalField(max_digits=5, decimal_places=2)
    cycle_days = models.IntegerField()
    break_required_after = models.DecimalField(max_digits=5, decimal_places=2)
    break_duration = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('HOS Regulation')
        verbose_name_plural = _('HOS Regulations')
    
    def __str__(self):
        return self.name

