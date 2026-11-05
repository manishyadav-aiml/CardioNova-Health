from django.apps import AppConfig


class PredictionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prediction"

    def ready(self):
        from . import signals  # noqa: F401  (creates a Profile for every new user)
