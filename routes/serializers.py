from rest_framework import serializers
from .models import Route, RouteStop, LogDay, LogActivity, HOSRegulation
from decimal import Decimal

class LogActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = LogActivity
        fields = ['id', 'type', 'start_time', 'end_time', 'location', 'description']
        read_only_fields = ['id']


class LogDaySerializer(serializers.ModelSerializer):
    activities = LogActivitySerializer(many=True, read_only=False)
    total_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = LogDay
        fields = [
            'id', 'date', 'start_location', 'end_location', 'total_miles',
            'shipping_documents', 'remarks', 'activities', 'total_hours'
        ]
        read_only_fields = ['id']
    
    def get_total_hours(self, obj):
        return {
            'offDuty': str(obj.off_duty_hours),
            'sleeperBerth': str(obj.sleeper_berth_hours),
            'driving': str(obj.driving_hours),
            'onDutyNotDriving': str(obj.on_duty_not_driving_hours)
        }
    
    def create(self, validated_data):
        activities_data = validated_data.pop('activities', [])
        log_day = LogDay.objects.create(**validated_data)
        
        for activity_data in activities_data:
            LogActivity.objects.create(log_day=log_day, **activity_data)
        
        return log_day


class RouteStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteStop
        fields = [
            'id', 'type', 'location', 'description', 'arrival_time',
            'departure_time', 'duration', 'mileage', 'latitude', 'longitude'
        ]
        read_only_fields = ['id']


class RouteSerializer(serializers.ModelSerializer):
    stops = RouteStopSerializer(many=True, read_only=False)
    logs = LogDaySerializer(many=True, read_only=False)
    
    class Meta:
        model = Route
        fields = [
            'id', 'start_location', 'end_location', 'total_distance',
            'total_duration', 'stops', 'logs', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        stops_data = validated_data.pop('stops', [])
        logs_data = validated_data.pop('logs', [])
        
        validated_data['user'] = self.context['request'].user
        
        route = Route.objects.create(**validated_data)
        
        for stop_data in stops_data:
            RouteStop.objects.create(route=route, **stop_data)
        
        for log_data in logs_data:
            activities_data = log_data.pop('activities', [])
            log = LogDay.objects.create(route=route, **log_data)
            
            for activity_data in activities_data:
                LogActivity.objects.create(log_day=log, **activity_data)
        
        return route


class TripDetailsSerializer(serializers.Serializer):
    """
    Serializer for trip details input to calculate a route.
    """
    current_location = serializers.CharField(max_length=255)
    pickup_location = serializers.CharField(max_length=255)
    dropoff_location = serializers.CharField(max_length=255)
    cycle_hours_used = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal('0'), max_value=Decimal('70'))


class HOSRegulationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HOSRegulation
        fields = [
            'id', 'name', 'description', 'max_driving_hours', 'max_duty_hours',
            'required_rest_hours', 'cycle_hours', 'cycle_days',
            'break_required_after', 'break_duration', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

