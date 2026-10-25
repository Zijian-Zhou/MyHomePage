import os

from django.apps import AppConfig


class MyhomepageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myHomePage'

    def ready(self):
        # Register auth signal handlers
        from . import signals  # noqa: F401
        if os.getenv('ENABLE_RESOURCE_MONITOR', 'True').lower() in {'1', 'true', 'yes', 'on'}:
            from .resource_monitor import start_monitor_thread
            start_monitor_thread()
