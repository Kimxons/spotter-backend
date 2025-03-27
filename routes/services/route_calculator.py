import datetime
import requests
from django.conf import settings
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
from decimal import Decimal
from ..models import HOSRegulation

class RouteCalculator:
    """
    Service for calculating routes, including stops, logs, and HOS compliance.
    """
    
    def __init__(self):
        self.mapbox_api_key = getattr(settings, 'MAPBOX_API_KEY', None)
        if not self.mapbox_api_key:
            raise ValueError("MAPBOX_API_KEY is required in Django settings")
        
        self.geolocator = Nominatim(user_agent="eld_planner", timeout=10)
        
        self.hos_regulation = self._get_hos_regulation()

    def _get_hos_regulation(self):
        """Retrieve active HOS regulation with field validation"""
        regulation = HOSRegulation.objects.filter(is_active=True).first()
        if not regulation:
            raise ValueError("No active HOS regulations found in database")
        
        required_fields = ['break_duration', 'break_required_after',
                          'max_driving_hours', 'required_rest_hours']
        for field in required_fields:
            if not hasattr(regulation, field):
                raise AttributeError(f"HOS regulation missing required field: {field}")
                
        return regulation

    def calculate_route(self, trip_details):
        """
        Calculate route with enhanced error handling and data validation
        """
        required_keys = ['current_location', 'pickup_location', 'dropoff_location']
        for key in required_keys:
            if key not in trip_details:
                raise KeyError(f"Missing required trip detail: {key}")
        cycle_hours_used = float(trip_details.get('cycle_hours_used', Decimal('0')))

        try:
            route_data = self._get_route_coordinates(
                trip_details['current_location'],
                trip_details['pickup_location'],
                trip_details['dropoff_location']
            )
            stops = self._calculate_hos_stops(route_data, cycle_hours_used)
            logs = self._generate_logs(stops, route_data)
            
            return {
                'startLocation': trip_details['current_location'],
                'endLocation': trip_details['dropoff_location'],
                'totalDistance': round(route_data['total_distance'], 1),
                'totalDuration': route_data['total_duration_text'],
                'stops': stops,
                'logs': logs,
                'routeGeometry': route_data['geometry']
            }
            
        except Exception as e:
            raise RuntimeError(f"Route calculation failed: {str(e)}")

    def _get_route_coordinates(self, start, pickup, dropoff):
        """Fetch route data from Mapbox with improved error handling"""
        try:
            start_coords = self._geocode_location(start)
            pickup_coords = self._geocode_location(pickup)
            dropoff_coords = self._geocode_location(dropoff)
        except ValueError as e:
            raise RuntimeError(f"Geocoding error: {str(e)}")

        coordinates = f"{start_coords[0]},{start_coords[1]};{pickup_coords[0]},{pickup_coords[1]};{dropoff_coords[0]},{dropoff_coords[1]}"
        url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates}"
        
        params = {
            "access_token": self.mapbox_api_key,
            "geometries": "geojson",
            "steps": "true",
            "overview": "full",
            "annotations": "duration,distance"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Mapbox API request failed: {str(e)}")

        if not data.get('routes'):
            raise RuntimeError("No valid route found in Mapbox response")

        route = data['routes'][0]
        return {
            'total_distance': route['distance'] / 1609.34,  # meters to miles
            'total_duration': route['duration'] / 3600,     # seconds to hours
            'total_duration_text': self._format_duration(route['duration']),
            'geometry': route['geometry'],
            'legs': route['legs']
        }

    def _process_steps(self, legs):
        """
        Process route steps to include cumulative distance and duration.
        """
        steps = []
        cumulative_distance = 0
        cumulative_duration = 0
        
        for leg in legs:
            for step in leg['steps']:
                step_distance = step['distance'] / 1609.34
                step_duration = step['duration'] / 3600
                steps.append({
                    'distance': step_distance,
                    'duration': step_duration,
                    'cumulative_distance': cumulative_distance + step_distance,
                    'cumulative_duration': cumulative_duration + step_duration,
                    'coordinates': step['geometry']['coordinates']
                })
                cumulative_distance += step_distance
                cumulative_duration += step_duration
        
        return steps

    def _calculate_hos_stops(self, route_data, cycle_hours_used):
        """Calculate HOS-compliant stops with real-time validation"""
        stops = []
        current_driving = 0.0
        cumulative_hours = cycle_hours_used
        legs = route_data.get('legs', [])

        for leg in legs:
            for step in leg.get('steps', []):
                step_duration = step['duration'] / 3600  # Convert to hours
                cumulative_hours += step_duration
                current_driving += step_duration

                # Check for required breaks
                if current_driving >= self.hos_regulation.break_required_after:
                    stops.append(self._create_hos_stop(
                        step,
                        'break',
                        f"Required {self.hos_regulation.break_duration}h break"
                    ))
                    current_driving = 0
                    cumulative_hours += self.hos_regulation.break_duration

                # Check for driving hour limits
                if cumulative_hours >= self.hos_regulation.max_driving_hours:
                    stops.append(self._create_hos_stop(
                        step,
                        'rest',
                        f"Mandatory {self.hos_regulation.required_rest_hours}h rest"
                    ))
                    cumulative_hours = 0
                    current_driving = 0

        return stops

    def _create_hos_stop(self, step, stop_type, description):
        """Create standardized stop entry with validation"""
        coordinates = step['geometry']['coordinates'][0] if step['geometry']['coordinates'] else None
        return {
            'type': stop_type,
            'location': self._reverse_geocode(coordinates) if coordinates else "Unknown Location",
            'description': description,
            'mileage': step['distance'] / 1609.34 if 'distance' in step else 0,
            'coordinates': coordinates,
            'duration': (
                self.hos_regulation.break_duration 
                if stop_type == 'break' 
                else self.hos_regulation.required_rest_hours
            ),
            'timestamp': datetime.datetime.now().isoformat()
        }


    def _create_stop(self, step, stop_type, description):
        """
        Create a stop entry using step data.
        """
        return {
            'type': stop_type,
            'location': self._reverse_geocode(step['coordinates'][0]),
            'description': description,
            'mileage': step['cumulative_distance'],
            'coordinates': step['coordinates'][0],
            'duration': self.hos_regulation.break_duration if stop_type == 'rest' 
                        else self.hos_regulation.required_rest_hours
        }

    def _reverse_geocode(self, coords):
        """Reverse geocode coordinates with fallback"""
        try:
            location = self.geolocator.reverse((coords[1], coords[0]), exactly_one=True)
            return location.address if location else "Unknown Location"
        except (GeocoderUnavailable, GeocoderTimedOut):
            return "Unknown Location"

    def _generate_logs(self, stops, route_data):
        """
        Generate logs dynamically based on stops and route data.
        """
        logs = []
        current_date = datetime.datetime.now().date()
        
        for i, stop in enumerate(stops):
            log_date = current_date + datetime.timedelta(days=i)
            logs.append({
                'date': log_date.strftime("%m/%d/%Y"),
                'startLocation': stops[i-1]['location'] if i > 0 else "Start",
                'endLocation': stop['location'],
                'totalMiles': stop['mileage'],
                'activities': self._generate_activities(stop, log_date)
            })
        
        return logs

    def _generate_activities(self, stop, date):
        """
        Generate activities for a log entry based on stop details.
        """
        return [{
            'type': 'driving' if stop['type'] != 'rest' else 'offDuty',
            'startTime': "08:00",
            'endTime': "16:00",
            'location': stop['location'],
            'description': stop['description']
        }]

    def _geocode_location(self, location):
        """Geocode location with improved error handling"""
        try:
            result = self.geolocator.geocode(location, exactly_one=True)
            if not result:
                raise ValueError(f"Could not geocode location: {location}")
            return (result.longitude, result.latitude)
        except (GeocoderUnavailable, GeocoderTimedOut) as e:
            raise RuntimeError(f"Geocoding service unavailable: {str(e)}")

    def _format_duration(self, total_seconds):
        """Convert seconds to human-readable format"""
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        duration_parts = []
        if days > 0:
            duration_parts.append(f"{int(days)} day{'s' if days != 1 else ''}")
        if hours > 0:
            duration_parts.append(f"{int(hours)} hour{'s' if hours != 1 else ''}")
        if minutes > 0 and days == 0:
            duration_parts.append(f"{int(minutes)} minute{'s' if minutes != 1 else ''}")
            
        return ' '.join(duration_parts) or "0 minutes"