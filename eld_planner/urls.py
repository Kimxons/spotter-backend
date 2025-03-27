from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# API docs schema
schema_view = get_schema_view(
    openapi.Info(
        title="ELD Trip Planner API",
        default_version='v1',
        description="API for ELD Trip Planner application",
        terms_of_service="https://www.eldtripplanner.com/terms/",
        contact=openapi.Contact(email="contact@eldtripplanner.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('routes.urls')),
    path('api/users/', include('users.urls')),
    
    # API doc
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

