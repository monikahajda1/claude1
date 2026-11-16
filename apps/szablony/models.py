import os
import uuid

from django.db import models
from simple_history.models import HistoricalRecords


class Rodzaj(models.TextChoices):
    """Rodzaje dokumentów generowanych z szablonów Word. Kolejne dojdą w następnych etapach."""

    OFERTA = "oferta", "Oferta"
    KZM = "kzm", "KZM – karta zatwierdzenia materiału"
    IBWR = "ibwr", "IBWR – instrukcja bezpiecznego wykonywania robót"


def sciezka_szablonu(instance, filename):
    return f"szablony/{instance.rodzaj}_{uuid.uuid4().hex[:8]}{os.path.splitext(filename)[1].lower()}"


class SzablonDokumentu(models.Model):
    """Własny szablon Word. Jeśli nie ma aktywnego, używany jest szablon wbudowany."""

    rodzaj = models.CharField("rodzaj dokumentu", max_length=30, choices=Rodzaj.choices)
    nazwa = models.CharField("nazwa", max_length=150, help_text="np. „Oferta – wzór 2026”")
    plik = models.FileField("plik Word (.docx)", upload_to=sciezka_szablonu)
    aktywny = models.BooleanField("aktywny", default=True, help_text="Używany jest najnowszy aktywny szablon danego rodzaju.")
    uwagi = models.CharField("uwagi", max_length=300, blank=True)
    dodano = models.DateTimeField("dodano", auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "szablon dokumentu"
        verbose_name_plural = "szablony dokumentów"
        ordering = ["rodzaj", "-dodano"]

    def __str__(self):
        return f"{self.get_rodzaj_display()}: {self.nazwa}"
