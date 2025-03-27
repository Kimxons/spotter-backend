from django.core.management.base import BaseCommand
from routes.models import HOSRegulation

class Command(BaseCommand):
    help = 'Seeds the database with default HOS regulations'

    def handle(self, *args, **options):
        # Deactivate any existing regulations
        HOSRegulation.objects.all().update(is_active=False)
        
        # Create default property-carrying HOS regulation
        regulation = HOSRegulation.objects.create(
            name="Property-Carrying 70-Hour/8-Day",
            description="Standard Hours of Service regulations for property-carrying drivers operating on a 70-hour/8-day schedule.",
            max_driving_hours=11.0,
            max_duty_hours=14.0,
            required_rest_hours=10.0,
            cycle_hours=70.0,
            cycle_days=8,
            break_required_after=8.0,
            break_duration=0.5,
            is_active=True
        )
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created HOS regulation: {regulation.name}'))

