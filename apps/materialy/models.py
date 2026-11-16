import os
import uuid

from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.bhp.terminy import status_terminu


class RodzajMaterialu(models.TextChoices):
    GRUNT = "grunt", "Grunt"
    ZYWICA = "zywica", "Żywica / warstwa zasadnicza"
    ZAMKNIECIE = "zamkniecie", "Warstwa zamykająca / lakier"
    POSYPKA = "posypka", "Posypka / wypełniacz"
    MASA = "masa", "Masa / zaprawa naprawcza"
    COKOL = "cokol", "Cokoły / dylatacje"
    INNY = "inny", "Inny"


class Material(models.Model):
    """Materiał z biblioteki – dokumenty wgrywa się RAZ i używa na wszystkich budowach."""

    nazwa = models.CharField("nazwa handlowa", max_length=200)
    producent = models.CharField("producent", max_length=200)
    rodzaj = models.CharField("rodzaj", max_length=20, choices=RodzajMaterialu.choices, default=RodzajMaterialu.ZYWICA)
    zastosowanie = models.TextField("zastosowanie / opis", blank=True, help_text="Trafia do KZM jako opis zastosowania.")
    chemiczny = models.BooleanField(
        "materiał chemiczny (wymaga karty charakterystyki)", default=True,
        help_text="Takie materiały trafiają do IBWR jako substancje niebezpieczne.",
    )
    systemy = models.ManyToManyField(
        "oferty.PozycjaCennika", verbose_name="używany w pozycjach cennika", blank=True, related_name="materialy",
        help_text="Zaznacz systemy/prace z cennika, w których stosujesz ten materiał. Budowa sama „pozna” swoje materiały z zakresu prac.",
    )
    aktywny = models.BooleanField("aktywny", default=True)
    history = HistoricalRecords(m2m_fields=[systemy])

    class Meta:
        verbose_name = "materiał"
        verbose_name_plural = "materiały"
        ordering = ["rodzaj", "nazwa"]

    def __str__(self):
        return f"{self.nazwa} ({self.producent})"

    def get_absolute_url(self):
        return reverse("materialy:szczegoly", args=[self.pk])

    def aktualne_dokumenty(self):
        """Słownik typ -> najnowszy dokument danego typu."""
        wynik = {}
        for d in sorted(self.dokumenty.all(), key=lambda d: (d.dodano, d.pk)):
            wynik[d.typ] = d
        return wynik

    def brakujace_typy(self):
        """Dokumenty, których brakuje (karta techniczna i DoP zawsze, SDS dla chemii)."""
        wymagane = [TypDokumentuMaterialu.KARTA_TECHNICZNA, TypDokumentuMaterialu.DOP]
        if self.chemiczny:
            wymagane.append(TypDokumentuMaterialu.SDS)
        aktualne = self.aktualne_dokumenty()
        return [TypDokumentuMaterialu(t).label for t in wymagane if t not in aktualne]


class TypDokumentuMaterialu(models.TextChoices):
    KARTA_TECHNICZNA = "karta_techniczna", "Karta techniczna"
    DOP = "dop", "Deklaracja właściwości użytkowych (DoP)"
    SDS = "sds", "Karta charakterystyki (SDS)"
    ATEST = "atest", "Atest higieniczny (PZH)"
    INNY = "inny", "Inny dokument"


KOLEJNOSC_TYPOW = list(TypDokumentuMaterialu.values)


def sciezka_dokumentu(instance, filename):
    return f"materialy/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()[:10]}"


class DokumentMaterialu(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="dokumenty")
    typ = models.CharField("rodzaj dokumentu", max_length=20, choices=TypDokumentuMaterialu.choices)
    opis = models.CharField("opis (opcjonalnie)", max_length=200, blank=True, help_text="np. wersja 03/2026")
    plik = models.FileField("plik (PDF)", upload_to=sciezka_dokumentu)
    data_waznosci = models.DateField("ważny do", null=True, blank=True, help_text="Puste = bezterminowy (np. karta techniczna).")
    dodano = models.DateTimeField("dodano", auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "dokument materiału"
        verbose_name_plural = "dokumenty materiałów"
        ordering = ["typ", "-dodano"]

    def __str__(self):
        return f"{self.get_typ_display()} – {self.material.nazwa}"

    @property
    def status(self):
        return status_terminu(self.data_waznosci)

    def nazwa_pliku(self, nr=None):
        """Czytelna nazwa do paczki ZIP, np. 01_Karta_techniczna_Grunt-X.pdf."""
        import re

        rozszerzenie = os.path.splitext(self.plik.name)[1] or ".pdf"
        czesci = [self.get_typ_display().split(" (")[0], self.material.nazwa]
        tekst = "_".join(re.sub(r"[^\w\-]+", "-", c, flags=re.UNICODE).strip("-") for c in czesci)
        return (f"{nr:02d}_" if nr else "") + tekst + rozszerzenie


class MaterialBudowy(models.Model):
    """Materiał użyty na budowie. Lista uzupełnia się z zakresu prac; można dodać/wykluczyć ręcznie."""

    budowa = models.ForeignKey("budowy.Budowa", on_delete=models.CASCADE, related_name="materialy")
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name="na_budowach")
    dodany_recznie = models.BooleanField("dodany ręcznie", default=False)
    wykluczony = models.BooleanField("nie używany na tej budowie", default=False)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "materiał na budowie"
        verbose_name_plural = "materiały na budowach"
        constraints = [models.UniqueConstraint(fields=["budowa", "material"], name="material_raz_na_budowie")]
        ordering = ["material__rodzaj", "material__nazwa"]

    def __str__(self):
        return f"{self.material} @ {self.budowa}"
