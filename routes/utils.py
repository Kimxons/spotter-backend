from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Custom exception handler for REST framework that improves the
    default error responses with more detailed information.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # If response is None, there was an unhandled exception
    if response is None:
        logger.error(f"Unhandled exception: {exc}")
        return Response(
            {
                'error': 'An unexpected error occurred.',
                'detail': str(exc)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Add more context to the error response
    if response.status_code == 400:
        response.data = {
            'error': 'Invalid input data.',
            'detail': response.data
        }
    elif response.status_code == 401:
        response.data = {
            'error': 'Authentication credentials were not provided or are invalid.',
            'detail': response.data
        }
    elif response.status_code == 403:
        response.data = {
            'error': 'You do not have permission to perform this action.',
            'detail': response.data
        }
    elif response.status_code == 404:
        response.data = {
            'error': 'The requested resource was not found.',
            'detail': response.data
        }
    elif response.status_code == 405:
        response.data = {
            'error': 'Method not allowed.',
            'detail': response.data
        }
    elif response.status_code == 429:
        response.data = {
            'error': 'Request was throttled.',
            'detail': response.data
        }
    
    return response

