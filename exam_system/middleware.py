from django.shortcuts import render
from django.urls import resolve
from exams.models import SiteSettings

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info.lstrip('/')
        
        # Allow access to admin panel even during maintenance
        if path.startswith('admin/'):
            return self.get_response(request)

        try:
            settings = SiteSettings.load()
            if settings.is_maintenance_mode:
                # Allow superusers / staff to bypass maintenance
                if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
                    return render(request, 'maintenance.html', {'message': settings.maintenance_message}, status=503)
        except Exception:
            # If the database table isn't created yet or another error occurs, ignore
            pass

        response = self.get_response(request)
        return response
