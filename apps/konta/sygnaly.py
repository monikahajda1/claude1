from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .uprawnienia import ROLE


@receiver(post_migrate)
def utworz_role(sender, **kwargs):
    """Po każdej aktualizacji bazy upewniamy się, że istnieją grupy-role."""
    if sender.name != "apps.konta":
        return
    from django.contrib.auth.models import Group

    for nazwa in ROLE:
        Group.objects.get_or_create(name=nazwa)
