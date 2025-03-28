from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Route, HOSRegulation
from .serializers import (
    RouteSerializer, TripDetailsSerializer, HOSRegulationSerializer
)
from .services.route_calculator import RouteCalculator
from .services.hos_validator import HOSValidator
from drf_yasg.utils import swagger_auto_schema

class RouteViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing routes.
    """
    serializer_class = RouteSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """
        This view returns a list of all routes for the currently authenticated user.
        """
        return Route.objects.filter(user=self.request.user)
    
    @swagger_auto_schema(
        request_body=TripDetailsSerializer,
        responses={
            200: RouteSerializer,
            400: 'Bad Request',
            500: 'Internal Server Error'
        },
        operation_description="Calculate a route based on trip details"
    )
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        Calculate a route based on trip details.
        """
        serializer = TripDetailsSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Initialize the route calculator service
                calculator = RouteCalculator()
                
                # Calculate the route
                route_data = calculator.calculate_route(serializer.validated_data)
                
                # Return the calculated route
                return Response(route_data)
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        request_body=TripDetailsSerializer,
        responses={
            200: 'Validation Result',
            400: 'Bad Request'
        },
        operation_description="Validate trip details before calculation"
    )
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """
        Validate trip details before calculation.
        """
        serializer = TripDetailsSerializer(data=request.data)
        if serializer.is_valid():
            validator = HOSValidator()
            
            validation_result = validator.validate_trip(serializer.validated_data)
            
            return Response(validation_result)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        request_body=RouteSerializer,
        responses={
            201: RouteSerializer,
            400: 'Bad Request'
        },
        operation_description="Save a calculated route"
    )
    @action(detail=False, methods=['post'])
    def save(self, request):
        """
        Save a calculated route.
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HOSRegulationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving HOS regulations.
    """
    queryset = HOSRegulation.objects.filter(is_active=True)
    serializer_class = HOSRegulationSerializer
    # permission_classes = [permissions.IsAuthenticated]
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get the current active HOS regulation.
        """
        regulation = get_object_or_404(HOSRegulation, is_active=True)
        serializer = self.get_serializer(regulation)
        return Response(serializer.data)

