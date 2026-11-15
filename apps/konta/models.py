from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords


class Uzytkownik(AbstractUser):
    """Konto osoby korzystającej z aplikacji.

    Role (Administrator, Handlowiec, BHP, Kierownik robót) to grupy Django –
    jedna osoba może mieć kilka ról. Szczegóły w pliku uprawnienia.py.
    """

    tylko_podglad = models.BooleanField(
        "tylko podgląd",
        default=False,
        help_text="Zaznacz, jeśli ta osoba ma tylko oglądać dane, bez możliwości zmian.",
    )
    telefon = models.CharField("telefon", max_length=30, blank=True)
    # Dziennik zmian kont (bez skrótu hasła i daty logowania).
    history = HistoricalRecords(excluded_fields=["password", "last_login"])

    class Meta:
        verbose_name = "użytkownik"
        verbose_name_plural = "użytkownicy"
        ordering = ["last_name", "first_name", "username"]

    def __str__(self):
        return self.get_full_name() or self.username
