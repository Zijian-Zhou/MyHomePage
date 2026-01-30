from django.apps import AppConfig


class MyhomepageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myHomePage'

    def ready(self):
        # Register auth signal handlers
        from . import signals  # noqa: F401
