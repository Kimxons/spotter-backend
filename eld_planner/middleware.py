import logging
import json

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.info(f"Request: {request.method} {request.path}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        if request.method in ['POST', 'PUT', 'PATCH'] and request.content_type == 'application/json':
            try:
                body = json.loads(request.body)
                logger.info(f"Request Body: {json.dumps(body, indent=2)}")
            except Exception as e:
                logger.warning(f"Could not parse request body: {e}")
        
        response = self.get_response(request)
        
        logger.info(f"Response: {response.status_code}")
        
        return response