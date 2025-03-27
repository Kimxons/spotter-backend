class HOSValidator:
    """
    Service for validating Hours of Service (HOS) compliance.
    """
    
    def validate_trip(self, trip_details):
        """
        Validate trip details for HOS compliance.
        
        Args:
            trip_details (dict): Dictionary containing trip details
                - current_location: Starting location
                - pickup_location: Pickup location
                - dropoff_location: Dropoff location
                - cycle_hours_used: Hours already used in the current cycle
                
        Returns:
            dict: Validation result with valid flag and any errors
        """
        cycle_hours_used = float(trip_details['cycle_hours_used'])
        
        # Basic validation
        errors = {}
        
        # Check if cycle hours used is within limits
        if cycle_hours_used < 0 or cycle_hours_used > 70:
            errors['cycle_hours_used'] = "Cycle hours used must be between 0 and 70."
        
        # Check if locations are valid
        if not trip_details['current_location']:
            errors['current_location'] = "Current location is required."
        
        if not trip_details['pickup_location']:
            errors['pickup_location'] = "Pickup location is required."
        
        if not trip_details['dropoff_location']:
            errors['dropoff_location'] = "Dropoff location is required."
        
        # Return validation result
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def check_hos_compliance(self, route_data, cycle_hours_used):
        """
        Check if a route is compliant with HOS regulations.
        
        Args:
            route_data (dict): Route data including stops and logs
            cycle_hours_used (float): Hours already used in the current cycle
            
        Returns:
            dict: Compliance check result
        """
        # Calculate total driving and on-duty hours from logs
        total_driving_hours = 0
        total_on_duty_hours = 0
        
        for log in route_data.get('logs', []):
            total_driving_hours += float(log['totalHours']['driving'])
            total_on_duty_hours += float(log['totalHours']['driving']) + float(log['totalHours']['onDutyNotDriving'])
        
        # Calculate remaining cycle hours
        cycle_hours_remaining = 70 - (cycle_hours_used + total_on_duty_hours)
        
        # Check if the route is compliant
        is_compliant = cycle_hours_remaining >= 0
        
        return {
            'isCompliant': is_compliant,
            'cycleHoursUsed': cycle_hours_used,
            'tripDrivingHours': total_driving_hours,
            'tripOnDutyHours': total_on_duty_hours,
            'cycleHoursRemaining': max(0, cycle_hours_remaining),
            'cycleHoursUsedPercentage': min(100, ((cycle_hours_used + total_on_duty_hours) / 70) * 100)
        }

