import datetime
from django.conf import settings
from ..models import HOSRegulation

class RouteCalculator:
    """
    Service for calculating routes, including stops, logs, and HOS compliance.
    """
    
    def __init__(self):
        self.mapbox_api_key = settings.MAPBOX_API_KEY
        # Get the current HOS regulation
        self.hos_regulation = HOSRegulation.objects.filter(is_active=True).first()
        if not self.hos_regulation:
            # Default values if no regulation is found
            self.max_driving_hours = 11 
            # Default values if no regulation is found
            self.max_driving_hours = 11
            self.max_duty_hours = 14
            self.required_rest_hours = 10
            self.cycle_hours = 70
            self.cycle_days = 8
            self.break_required_after = 8
            self.break_duration = 0.5
        else:
            # Use values from the database
            self.max_driving_hours = float(self.hos_regulation.max_driving_hours)
            self.max_duty_hours = float(self.hos_regulation.max_duty_hours)
            self.required_rest_hours = float(self.hos_regulation.required_rest_hours)
            self.cycle_hours = float(self.hos_regulation.cycle_hours)
            self.cycle_days = self.hos_regulation.cycle_days
            self.break_required_after = float(self.hos_regulation.break_required_after)
            self.break_duration = float(self.hos_regulation.break_duration)
    
    def calculate_route(self, trip_details):
        """
        Calculate a route based on trip details.
        
        Args:
            trip_details (dict): Dictionary containing trip details
                - current_location: Starting location
                - pickup_location: Pickup location
                - dropoff_location: Dropoff location
                - cycle_hours_used: Hours already used in the current cycle
                
        Returns:
            dict: Complete route data including stops and logs
        """
        # Extract trip details
        current_location = trip_details['current_location']
        pickup_location = trip_details['pickup_location']
        dropoff_location = trip_details['dropoff_location']
        cycle_hours_used = float(trip_details['cycle_hours_used'])
        
        # Get route coordinates and distances
        route_data = self._get_route_coordinates(current_location, pickup_location, dropoff_location)
        
        # Calculate stops based on HOS regulations
        stops = self._calculate_stops(route_data, cycle_hours_used)
        
        # Generate daily logs
        logs = self._generate_logs(stops, cycle_hours_used)
        
        # Prepare the complete route result
        result = {
            'startLocation': current_location,
            'endLocation': dropoff_location,
            'totalDistance': route_data['total_distance'],
            'totalDuration': route_data['total_duration_text'],
            'stops': stops,
            'logs': logs
        }
        
        return result
    
    def _get_route_coordinates(self, start, pickup, dropoff):
        """
        Get route coordinates, distances, and durations using Mapbox API.
        
        In a production environment, this would make actual API calls to Mapbox.
        For this implementation, we'll simulate the response.
        """
        # In a real implementation, we would call the Mapbox Directions API
        # For now, we'll simulate the response with realistic data
        
        # Simulate distances (in miles) and durations (in seconds)
        start_to_pickup_distance = 120
        start_to_pickup_duration = 7200  # 2 hours
        pickup_to_dropoff_distance = 630
        pickup_to_dropoff_duration = 34200  # 9.5 hours
        
        total_distance = start_to_pickup_distance + pickup_to_dropoff_distance
        total_duration = start_to_pickup_duration + pickup_to_dropoff_duration
        
        # Format the duration as days, hours
        days = total_duration // 86400
        hours = (total_duration % 86400) // 3600
        total_duration_text = f"{days} days, {hours} hours" if days > 0 else f"{hours} hours"
        
        return {
            'start_to_pickup_distance': start_to_pickup_distance,
            'start_to_pickup_duration': start_to_pickup_duration,
            'pickup_to_dropoff_distance': pickup_to_dropoff_distance,
            'pickup_to_dropoff_duration': pickup_to_dropoff_duration,
            'total_distance': total_distance,
            'total_duration': total_duration,
            'total_duration_text': total_duration_text
        }
    
    def _calculate_stops(self, route_data, cycle_hours_used):
        """
        Calculate stops along the route based on HOS regulations.
        """
        stops = []
        
        # Starting point
        current_date = datetime.datetime.now()
        current_time = datetime.time(8, 0)  # Start at 8:00 AM
        current_datetime = datetime.datetime.combine(current_date.date(), current_time)
        
        # Add starting point
        stops.append({
            'type': 'start',
            'location': route_data.get('start_location', 'Starting Point'),
            'description': 'Starting location',
            'arrivalTime': f"Day 1, {current_time.strftime('%I:%M %p')}",
            'departureTime': f"Day 1, {(current_datetime + datetime.timedelta(minutes=30)).time().strftime('%I:%M %p')}",
            'duration': '30 min',
            'mileage': 0
        })
        
        # Update current time (30 min for pre-trip inspection)
        current_datetime += datetime.timedelta(minutes=30)
        
        # Add pickup location
        driving_time_to_pickup = route_data['start_to_pickup_duration'] / 3600  # Convert to hours
        current_datetime += datetime.timedelta(hours=driving_time_to_pickup)
        
        stops.append({
            'type': 'pickup',
            'location': route_data.get('pickup_location', 'Pickup Point'),
            'description': 'Cargo pickup',
            'arrivalTime': f"Day 1, {current_datetime.time().strftime('%I:%M %p')}",
            'departureTime': f"Day 1, {(current_datetime + datetime.timedelta(hours=1)).time().strftime('%I:%M %p')}",
            'duration': '1 hour',
            'mileage': route_data['start_to_pickup_distance']
        })
        
        # Update current time (1 hour for loading)
        current_datetime += datetime.timedelta(hours=1)
        
        # Calculate remaining driving time for the day
        hours_used_so_far = driving_time_to_pickup + 1.5  # Pre-trip + driving + loading
        remaining_driving_hours = min(self.max_driving_hours - driving_time_to_pickup, 
                                     self.max_duty_hours - hours_used_so_far)
        
        # Check if a break is needed
        if driving_time_to_pickup >= self.break_required_after:
            # Add a rest stop for the required break
            current_datetime += datetime.timedelta(hours=2)  # 2 hours of driving after pickup
            
            stops.append({
                'type': 'rest',
                'location': 'Rest Area - Highway 70',
                'description': f"Required {self.break_duration * 60}-minute break",
                'arrivalTime': f"Day 1, {current_datetime.time().strftime('%I:%M %p')}",
                'departureTime': f"Day 1, {(current_datetime + datetime.timedelta(hours=self.break_duration)).time().strftime('%I:%M %p')}",
                'duration': f"{int(self.break_duration * 60)} min",
                'mileage': route_data['start_to_pickup_distance'] + 120  # Approximate mileage
            })
            
            # Update current time
            current_datetime += datetime.timedelta(hours=self.break_duration)
            remaining_driving_hours -= 2 + self.break_duration
        
        # Add a fuel stop if needed
        if route_data['total_distance'] > 400:
            # Assume we need fuel after driving about 400 miles
            current_datetime += datetime.timedelta(hours=3)  # 3 more hours of driving
            
            stops.append({
                'type': 'fuel',
                'location': 'Truck Stop - Junction City',
                'description': 'Refueling and meal break',
                'arrivalTime': f"Day 1, {current_datetime.time().strftime('%I:%M %p')}",
                'departureTime': f"Day 1, {(current_datetime + datetime.timedelta(hours=1)).time().strftime('%I:%M %p')}",
                'duration': '1 hour',
                'mileage': route_data['start_to_pickup_distance'] + 240  # Approximate mileage
            })
            
            # Update current time
            current_datetime += datetime.timedelta(hours=1)
            remaining_driving_hours -= 3 + 1
        
        # Add overnight stop
        current_datetime += datetime.timedelta(hours=remaining_driving_hours)
        day_1_end_time = current_datetime.time()
        
        stops.append({
            'type': 'overnight',
            'location': 'Truck Stop - Riverside',
            'description': f"{self.required_rest_hours}-hour rest period",
            'arrivalTime': f"Day 1, {day_1_end_time.strftime('%I:%M %p')}",
            'departureTime': "Day 2, 06:00 AM",
            'duration': f"{self.required_rest_hours} hours",
            'mileage': route_data['start_to_pickup_distance'] + 380  # Approximate mileage
        })
        
        # Day 2 starts at 6:00 AM
        current_datetime = datetime.datetime.combine(current_date.date() + datetime.timedelta(days=1), 
                                                   datetime.time(6, 0))
        
        # Calculate remaining distance to dropoff
        remaining_distance = route_data['total_distance'] - 380  # Approximate distance covered on day 1
        
        # Add a rest break on day 2 if needed
        if remaining_distance > 250:  # If we still have significant driving to do
            current_datetime += datetime.timedelta(hours=4)  # 4 hours of driving
            
            stops.append({
                'type': 'rest',
                'location': 'Rest Area - Highway 40',
                'description': f"Required {self.break_duration * 60}-minute break",
                'arrivalTime': f"Day 2, {current_datetime.time().strftime('%I:%M %p')}",
                'departureTime': f"Day 2, {(current_datetime + datetime.timedelta(hours=self.break_duration)).time().strftime('%I:%M %p')}",
                'duration': f"{int(self.break_duration * 60)} min",
                'mileage': 620  # Approximate mileage
            })
            
            # Update current time
            current_datetime += datetime.timedelta(hours=self.break_duration)
        
        # Add dropoff location
        current_datetime += datetime.timedelta(hours=3)  # Remaining driving time to dropoff
        
        stops.append({
            'type': 'dropoff',
            'location': route_data.get('dropoff_location', 'Dropoff Point'),
            'description': 'Final delivery',
            'arrivalTime': f"Day 2, {current_datetime.time().strftime('%I:%M %p')}",
            'departureTime': f"Day 2, {(current_datetime + datetime.timedelta(hours=1)).time().strftime('%I:%M %p')}",
            'duration': '1 hour',
            'mileage': route_data['total_distance']
        })
        
        return stops
    
    def _generate_logs(self, stops, cycle_hours_used):
        """
        Generate daily logs based on the calculated stops.
        """
        logs = []
        
        # Group stops by day
        day_1_stops = [stop for stop in stops if stop['arrivalTime'].startswith('Day 1')]
        day_2_stops = [stop for stop in stops if stop['arrivalTime'].startswith('Day 2')]
        
        # Generate log for day 1
        if day_1_stops:
            day_1_log = self._create_daily_log(
                date="04/15/2023",
                start_location=day_1_stops[0]['location'],
                end_location=day_1_stops[-1]['location'],
                total_miles=day_1_stops[-1]['mileage'],
                stops=day_1_stops,
                day_number=1
            )
            logs.append(day_1_log)
        
        # Generate log for day 2
        if day_2_stops:
            day_2_log = self._create_daily_log(
                date="04/16/2023",
                start_location=day_2_stops[0]['location'],
                end_location=day_2_stops[-1]['location'],
                total_miles=day_2_stops[-1]['mileage'] - day_1_stops[-1]['mileage'] if day_1_stops else day_2_stops[-1]['mileage'],
                stops=day_2_stops,
                day_number=2
            )
            logs.append(day_2_log)
        
        return logs
    
    def _create_daily_log(self, date, start_location, end_location, total_miles, stops, day_number):
        """
        Create a daily log entry based on stops.
        """
        # Generate remarks based on stops
        remarks = []
        for stop in stops:
            arrival_time = stop['arrivalTime'].split(', ')[1]
            remarks.append(f"{arrival_time} - {stop['description']} at {stop['location']}")
        
        # Generate activities based on stops
        activities = []
        
        if day_number == 1:
            # Off duty until start time
            activities.append({
                'type': 'offDuty',
                'startTime': "00:00",
                'endTime': "08:00",
                'location': start_location
            })
            
            # Pre-trip inspection
            activities.append({
                'type': 'onDutyNotDriving',
                'startTime': "08:00",
                'endTime': "08:30",
                'location': start_location,
                'description': "Pre-trip inspection"
            })
            
            # Driving to pickup
            activities.append({
                'type': 'driving',
                'startTime': "08:30",
                'endTime': "10:30",
                'location': "En route to pickup"
            })
            
            # Loading at pickup
            activities.append({
                'type': 'onDutyNotDriving',
                'startTime': "10:30",
                'endTime': "11:30",
                'location': stops[1]['location'],  # Pickup location
                'description': "Loading cargo"
            })
            
            # Driving after pickup
            activities.append({
                'type': 'driving',
                'startTime': "11:30",
                'endTime': "13:30",
                'location': "En route"
            })
            
            # Rest break
            activities.append({
                'type': 'offDuty',
                'startTime': "13:30",
                'endTime': "14:00",
                'location': stops[2]['location'],  # Rest area
                'description': "Required 30-minute break"
            })
            
            # More driving
            activities.append({
                'type': 'driving',
                'startTime': "14:00",
                'endTime': "16:30",
                'location': "En route"
            })
            
            # Fuel stop
            activities.append({
                'type': 'onDutyNotDriving',
                'startTime': "16:30",
                'endTime': "17:30",
                'location': stops[3]['location'],  # Fuel stop
                'description': "Refueling"
            })
            
            # Final driving for day 1
            activities.append({
                'type': 'driving',
                'startTime': "17:30",
                'endTime': "20:00",
                'location': "En route"
            })
            
            # Sleeper berth for the rest of day 1
            activities.append({
                'type': 'sleeperBerth',
                'startTime': "20:00",
                'endTime': "24:00",
                'location': stops[-1]['location']  # Overnight location
            })
            
        elif day_number == 2:
            # Sleeper berth until morning
            activities.append({
                'type': 'sleeperBerth',
                'startTime': "00:00",
                'endTime': "06:00",
                'location': stops[0]['location']  # Overnight location
            })
            
            # Pre-trip inspection
            activities.append({
                'type': 'onDutyNotDriving',
                'startTime': "06:00",
                'endTime': "06:30",
                'location': stops[0]['location'],
                'description': "Pre-trip inspection"
            })
            
            # Driving
            activities.append({
                'type': 'driving',
                'startTime': "06:30",
                'endTime': "10:00",
                'location': "En route"
            })
            
            # Rest break
            activities.append({
                'type': 'offDuty',
                'startTime': "10:00",
                'endTime': "10:30",
                'location': stops[1]['location'] if len(stops) > 1 else "Rest Area",
                'description': "Required 30-minute break"
            })
            
            # More driving
            activities.append({
                'type': 'driving',
                'startTime': "10:30",
                'endTime': "13:30",
                'location': "En route to delivery"
            })
            
            # Unloading at dropoff
            activities.append({
                'type': 'onDutyNotDriving',
                'startTime': "13:30",
                'endTime': "14:30",
                'location': stops[-1]['location'],  # Dropoff location
                'description': "Unloading cargo"
            })
            
            # Off duty for the rest of day 2
            activities.append({
                'type': 'offDuty',
                'startTime': "14:30",
                'endTime': "24:00",
                'location': stops[-1]['location']
            })
        
        # Calculate total hours by activity type
        off_duty_hours = sum(
            self._calculate_hours(activity['startTime'], activity['endTime'])
            for activity in activities if activity['type'] == 'offDuty'
        )
        
        sleeper_berth_hours = sum(
            self._calculate_hours(activity['startTime'], activity['endTime'])
            for activity in activities if activity['type'] == 'sleeperBerth'
        )
        
        driving_hours = sum(
            self._calculate_hours(activity['startTime'], activity['endTime'])
            for activity in activities if activity['type'] == 'driving'
        )
        
        on_duty_not_driving_hours = sum(
            self._calculate_hours(activity['startTime'], activity['endTime'])
            for activity in activities if activity['type'] == 'onDutyNotDriving'
        )
        
        # Create the log entry
        log = {
            'date': date,
            'startLocation': start_location,
            'endLocation': end_location,
            'totalMiles': total_miles,
            'shippingDocuments': "BOL-12345",
            'remarks': remarks,
            'activities': activities,
            'totalHours': {
                'offDuty': f"{off_duty_hours:.1f}",
                'sleeperBerth': f"{sleeper_berth_hours:.1f}",
                'driving': f"{driving_hours:.1f}",
                'onDutyNotDriving': f"{on_duty_not_driving_hours:.1f}"
            }
        }
        
        return log
    
    def _calculate_hours(self, start_time, end_time):
        """
        Calculate hours between two time strings in format "HH:MM".
        """
        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))
        
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        
        # Handle crossing midnight
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        
        return (end_minutes - start_minutes) / 60

