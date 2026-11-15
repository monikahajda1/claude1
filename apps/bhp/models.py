import os
import uuid

from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from .terminy import status_terminu


class Dotyczy(models.TextChoices):
    PRACOWNIK = "pracownik", "Pracownik"
    SPRZET = "sprzet", "Sprzęt"


class TypDokumentu(models.Model):
    """Słownik rodzajów dokumentów (badania, szkolenia, przeglądy UDT...).

    Listę można rozbudowywać w panelu administracyjnym – bez programisty.
    """

    nazwa = models.CharField("nazwa", max_length=150)
    dotyczy = models.CharField("dotyczy", max_length=20, choices=Dotyczy.choices)
    wymagany = models.BooleanField(
        "wymagany zawsze",
        default=False,
        help_text="Jeśli zaznaczone – brak tego dokumentu będzie pokazany jako alert.",
    )
    okres_miesiecy = models.PositiveIntegerField(
        "typowy okres ważności [mies.]", null=True, blank=True, help_text="Podpowiedź przy wpisywaniu daty ważności."
    )
    kolejnosc = models.PositiveIntegerField("kolejność", default=100)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "typ dokumentu"
        verbose_name_plural = "typy dokumentów"
        ordering = ["dotyczy", "kolejnosc", "nazwa"]
        constraints = [models.UniqueConstraint(fields=["nazwa", "dotyczy"], name="unikalny_typ_dokumentu")]

    def __str__(self):
        return self.nazwa


class Pracownik(models.Model):
    imie = models.CharField("imię", max_length=80)
    nazwisko = models.CharField("nazwisko", max_length=120)
    stanowisko = models.CharField("stanowisko", max_length=120, blank=True, help_text="np. posadzkarz, brygadzista")
    firma = models.CharField(
        "firma", max_length=200, blank=True, help_text="Puste = pracownik własny. Wpisz nazwę, jeśli to podwykonawca."
    )
    telefon = models.CharField("telefon", max_length=30, blank=True)
    aktywny = models.BooleanField("aktywny", default=True, help_text="Odznacz, gdy pracownik już u nas nie pracuje.")
    uwagi = models.TextField("uwagi", blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "pracownik"
        verbose_name_plural = "pracownicy"
        ordering = ["nazwisko", "imie"]

    def __str__(self):
        return f"{self.nazwisko} {self.imie}"

    def get_absolute_url(self):
        return reverse("bhp:pracownik", args=[self.pk])

    @property
    def podwykonawca(self):
        return bool(self.firma)


class Sprzet(models.Model):
    nazwa = models.CharField("nazwa", max_length=150, help_text="np. szlifierka do betonu, podest ruchomy")
    numer_ewidencyjny = models.CharField("nr ewidencyjny / seryjny", max_length=80, blank=True)
    producent_model = models.CharField("producent i model", max_length=150, blank=True)
    aktywny = models.BooleanField("aktywny", default=True, help_text="Odznacz, gdy sprzęt sprzedany lub zezłomowany.")
    uwagi = models.TextField("uwagi", blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "sprzęt"
        verbose_name_plural = "sprzęt"
        ordering = ["nazwa", "numer_ewidencyjny"]

    def __str__(self):
        return f"{self.nazwa} ({self.numer_ewidencyjny})" if self.numer_ewidencyjny else self.nazwa

    def get_absolute_url(self):
        return reverse("bhp:sprzet", args=[self.pk])


def sciezka_pliku(instance, filename):
    """Pliki zapisujemy pod losową nazwą – nie zdradza ona, czego dotyczy dokument."""
    rozszerzenie = os.path.splitext(filename)[1].lower()[:10]
    return f"bhp/{instance.__class__.__name__.lower()}/{uuid.uuid4().hex}{rozszerzenie}"


class DokumentBazowy(models.Model):
    typ = models.ForeignKey(TypDokumentu, verbose_name="rodzaj dokumentu", on_delete=models.PROTECT)
    numer = models.CharField("numer dokumentu", max_length=100, blank=True)
    data_wydania = models.DateField("data wydania / wykonania", null=True, blank=True)
    data_waznosci = models.DateField("ważny do", null=True, blank=True, help_text="Puste = bezterminowy.")
    plik = models.FileField("skan / zdjęcie", upload_to=sciezka_pliku, blank=True)
    uwagi = models.CharField("uwagi", max_length=300, blank=True)

    class Meta:
        abstract = True
        ordering = ["typ__kolejnosc", "-data_waznosci"]

    def __str__(self):
        return f"{self.typ} – {self.data_waznosci or 'bezterminowo'}"

    @property
    def status(self):
        return status_terminu(self.data_waznosci)


class DokumentPracownika(DokumentBazowy):
    pracownik = models.ForeignKey(Pracownik, on_delete=models.CASCADE, related_name="dokumenty")
    history = HistoricalRecords()

    class Meta(DokumentBazowy.Meta):
        verbose_name = "dokument pracownika"
        verbose_name_plural = "dokumenty pracowników"

    @property
    def wlasciciel(self):
        return self.pracownik


class DokumentSprzetu(DokumentBazowy):
    sprzet = models.ForeignKey(Sprzet, on_delete=models.CASCADE, related_name="dokumenty")
    history = HistoricalRecords()

    class Meta(DokumentBazowy.Meta):
        verbose_name = "dokument sprzętu"
        verbose_name_plural = "dokumenty sprzętu"

    @property
    def wlasciciel(self):
        return self.sprzet
