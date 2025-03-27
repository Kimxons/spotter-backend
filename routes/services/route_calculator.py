import datetime
import requests
from django.conf import settings
from geopy.geocoders import Nominatim
from ..models import HOSRegulation

class RouteCalculator:
    """
    Service for calculating routes, including stops, logs, and HOS compliance.
    """
    
    def __init__(self):
        self.mapbox_api_key = settings.MAPBOX_API_KEY
        if not self.mapbox_api_key:
            raise ValueError("Mapbox API key is required.")
        
        self.geolocator = Nominatim(user_agent="eld_planner")
        self.hos_regulation = self._get_hos_regulation()

    def _get_hos_regulation(self):
        regulation = HOSRegulation.objects.filter(is_active=True).first()
        if not regulation:
            raise ValueError("No active HOS regulation found.")
        return regulation

    def calculate_route(self, trip_details):
        """
        Calculate a route based on trip details using real data.
        """
        route_data = self._get_route_coordinates(
            trip_details['current_location'],
            trip_details['pickup_location'],
            trip_details['dropoff_location']
        )
        
        stops = self._calculate_hos_stops(route_data, trip_details.get('cycle_hours_used', 0))
        logs = self._generate_logs(stops, route_data)
        
        return {
            'startLocation': trip_details['current_location'],
            'endLocation': trip_details['dropoff_location'],
            'totalDistance': route_data['total_distance'],
            'totalDuration': route_data['total_duration_text'],
            'stops': stops,
            'logs': logs,
            'routeGeometry': route_data['geometry']
        }

    def _get_route_coordinates(self, start, pickup, dropoff):
        """
        Fetch route data from Mapbox Directions API including all waypoints.
        """
        start_coords = self._geocode_location(start)
        pickup_coords = self._geocode_location(pickup)
        dropoff_coords = self._geocode_location(dropoff)
        
        coordinates = f"{start_coords[0]},{start_coords[1]};{pickup_coords[0]},{pickup_coords[1]};{dropoff_coords[0]},{dropoff_coords[1]}"
        url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates}"
        params = {
            "access_token": self.mapbox_api_key,
            "geometries": "geojson",
            "steps": "true",
            "overview": "full"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('routes'):
            raise Exception("No route found.")
        
        route = data['routes'][0]
        total_distance = route['distance'] / 1609.34  # meters to miles
        total_duration = route['duration'] / 3600  # seconds to hours
        
        return {
            'total_distance': total_distance,
            'total_duration': total_duration,
            'total_duration_text': self._format_duration(total_duration),
            'geometry': route['geometry'],
            'steps': self._process_steps(route['legs'])
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
        """
        Calculate stops based on HOS regulations using real route steps.
        """
        stops = []
        current_driving = 0.0
        cumulative_hours = cycle_hours_used
        
        for step in route_data['steps']:
            step_duration = step['duration']
            cumulative_hours += step_duration
            current_driving += step_duration
            
            if current_driving >= self.hos_regulation.break_required_after:
                stops.append(self._create_stop(
                    step, 
                    'rest', 
                    f"{self.hos_regulation.break_duration}-hour break required"
                ))
                current_driving = 0
                cumulative_hours += self.hos_regulation.break_duration
            
            if cumulative_hours >= self.hos_regulation.max_driving_hours:
                stops.append(self._create_stop(
                    step, 
                    'overnight', 
                    f"{self.hos_regulation.required_rest_hours}-hour rest period"
                ))
                cumulative_hours = 0
                current_driving = 0
        
        return stops

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
        """
        Reverse geocode coordinates to get location name.
        """
        try:
            location = self.geolocator.reverse((coords[1], coords[0]))
            return location.address if location else "Unknown Location"
        except Exception:
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
        """
        Geocode location string to coordinates with error handling.
        """
        try:
            result = self.geolocator.geocode(location)
            if result:
                return (result.longitude, result.latitude)
            raise ValueError(f"Could not geocode location: {location}")
        except Exception as e:
            raise ValueError(f"Geocoding error: {e}")

    def _format_duration(self, total_hours):
        """
        Format duration into days and hours.
        """
        days = int(total_hours // 24)
        hours = int(total_hours % 24)
        return f"{days} days, {hours} hours" if days else f"{hours} hours"