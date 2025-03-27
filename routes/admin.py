from django.contrib import admin
from .models import Route, RouteStop, LogDay, LogActivity, HOSRegulation

class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 0

class LogActivityInline(admin.TabularInline):
    model = LogActivity
    extra = 0

class LogDayInline(admin.TabularInline):
    model = LogDay
    extra = 0
    show_change_link = True

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'start_location', 'end_location', 'total_distance', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('start_location', 'end_location', 'user__username')
    inlines = [RouteStopInline, LogDayInline]
    date_hierarchy = 'created_at'

@admin.register(LogDay)
class LogDayAdmin(admin.ModelAdmin):
    list_display = ('id', 'route', 'date', 'start_location', 'end_location', 'total_miles')
    list_filter = ('date',)
    search_fields = ('start_location', 'end_location', 'route__id')
    inlines = [LogActivityInline]

@admin.register(HOSRegulation)
class HOSRegulationAdmin(admin.ModelAdmin):
    list_display = ('name', 'cycle_hours', 'cycle_days', 'is_active', 'updated_at')
    list_filter = ('is_active', 'updated_at')
    search_fields = ('name', 'description')

