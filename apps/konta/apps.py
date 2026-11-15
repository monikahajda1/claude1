from django.apps import AppConfig


class KontaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.konta"
    verbose_name = "Konta i uprawnienia"

    def ready(self):
        from . import sygnaly  # noqa: F401  (rejestracja sygnałów)
