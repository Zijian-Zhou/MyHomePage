from django.conf import settings


def app_info(request):
    """Expose the application version to every template (public site and admin)."""
    return {'app_version': settings.APP_VERSION}
