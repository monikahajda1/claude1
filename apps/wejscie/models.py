import os
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.bhp.terminy import status_terminu


def sciezka(katalog):
    def _sciezka(instance, filename):
        return f"{katalog}/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()[:10]}"

    return _sciezka


# Funkcje nazwane – Django musi umieć zapisać je w migracjach.
def sciezka_wejscie(instance, filename):
    return sciezka("wejscie")(instance, filename)


def sciezka_firma(instance, filename):
    return sciezka("firma")(instance, filename)


# --- KZM ---------------------------------------------------------------------

class StatusKZM(models.TextChoices):
    PRZYGOTOWANA = "przygotowana", "Przygotowana"
    ZLOZONA = "zlozona", "Złożona do zatwierdzenia"
    ZATWIERDZONA = "zatwierdzona", "Zatwierdzona"
    Z_UWAGAMI = "z_uwagami", "Zatwierdzona z uwagami"
    ODRZUCONA = "odrzucona", "Odrzucona"


KZM_ZATWIERDZONE = [StatusKZM.ZATWIERDZONA, StatusKZM.Z_UWAGAMI]
KOLOR_KZM = {
    StatusKZM.PRZYGOTOWANA: "secondary", StatusKZM.ZLOZONA: "info", StatusKZM.ZATWIERDZONA: "success",
    StatusKZM.Z_UWAGAMI: "success", StatusKZM.ODRZUCONA: "danger",
}


class KZM(models.Model):
    """Karta zatwierdzenia materiału – jedna na materiał na budowie."""

    budowa = models.ForeignKey("budowy.Budowa", on_delete=models.CASCADE, related_name="kzm")
    material = models.ForeignKey("materialy.Material", on_delete=models.PROTECT, related_name="kzm")
    numer = models.CharField("numer", max_length=50, blank=True)
    zastosowanie = models.TextField("zastosowanie na budowie", blank=True)
    status = models.CharField("status", max_length=20, choices=StatusKZM.choices, default=StatusKZM.PRZYGOTOWANA)
    data_zlozenia = models.DateField("data złożenia", null=True, blank=True)
    data_decyzji = models.DateField("data decyzji", null=True, blank=True)
    uwagi_zatwierdzajacego = models.TextField("uwagi zatwierdzającego", blank=True)
    skan = models.FileField("skan podpisanej karty", upload_to=sciezka_wejscie, blank=True)
    utworzono = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "KZM"
        verbose_name_plural = "KZM – karty zatwierdzenia materiałów"
        ordering = ["budowa", "material__nazwa", "-utworzono"]

    def __str__(self):
        return f"{self.numer} {self.material.nazwa}"

    def get_absolute_url(self):
        return reverse("wejscie:kzm", args=[self.pk])

    @property
    def kolor(self):
        return KOLOR_KZM.get(self.status, "secondary")

    @property
    def zatwierdzona(self):
        return self.status in KZM_ZATWIERDZONE

    def save(self, *args, **kwargs):
        if not self.numer:
            nr = KZM.objects.filter(budowa=self.budowa).count() + 1
            self.numer = f"KZM/{self.budowa.numer.replace('B/', '')}/{nr:02d}"
        super().save(*args, **kwargs)


# --- IBWR --------------------------------------------------------------------

class Zagrozenie(models.Model):
    """Biblioteka typowych zagrożeń – do IBWR. Zmieniana w panelu administracyjnym."""

    nazwa = models.CharField("zagrożenie", max_length=200)
    srodki = models.TextField("środki ochrony / sposób postępowania")
    domyslne = models.BooleanField("domyślnie zaznaczone w nowej IBWR", default=True)
    aktywne = models.BooleanField("aktywne", default=True)
    kolejnosc = models.PositiveIntegerField("kolejność", default=100)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "zagrożenie (biblioteka IBWR)"
        verbose_name_plural = "zagrożenia (biblioteka IBWR)"
        ordering = ["kolejnosc", "nazwa"]

    def __str__(self):
        return self.nazwa


class StatusIBWR(models.TextChoices):
    ROBOCZA = "robocza", "Robocza"
    PRZEKAZANA = "przekazana", "Przekazana GW"
    ZATWIERDZONA = "zatwierdzona", "Zatwierdzona"


KOLOR_IBWR = {StatusIBWR.ROBOCZA: "secondary", StatusIBWR.PRZEKAZANA: "info", StatusIBWR.ZATWIERDZONA: "success"}


class IBWR(models.Model):
    budowa = models.OneToOneField("budowy.Budowa", on_delete=models.CASCADE, related_name="ibwr")
    status = models.CharField("status", max_length=20, choices=StatusIBWR.choices, default=StatusIBWR.ROBOCZA)
    zagrozenia = models.ManyToManyField(Zagrozenie, verbose_name="zagrożenia", blank=True)
    dodatkowe_zagrozenia = models.TextField(
        "dodatkowe zagrożenia na tej budowie", blank=True,
        help_text="Każde w osobnej linii, w formie: zagrożenie – środki ochrony",
    )
    procedury_awaryjne = models.TextField(
        "postępowanie w razie wypadku / pożaru", blank=True,
        default="Udzielić pierwszej pomocy, wezwać pomoc (tel. 112), powiadomić kierownika robót i koordynatora GW. "
                "W razie pożaru – ewakuacja drogami oznakowanymi, gaszenie gaśnicą proszkową.",
    )
    data_przekazania = models.DateField("data przekazania GW", null=True, blank=True)
    data_zatwierdzenia = models.DateField("data zatwierdzenia", null=True, blank=True)
    skan = models.FileField("skan podpisanej IBWR", upload_to=sciezka_wejscie, blank=True)
    opracowal = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="opracował(a)", null=True, blank=True, on_delete=models.SET_NULL)
    history = HistoricalRecords(m2m_fields=[zagrozenia])

    class Meta:
        verbose_name = "IBWR"
        verbose_name_plural = "IBWR – instrukcje bezpiecznego wykonywania robót"

    def __str__(self):
        return f"IBWR {self.budowa}"

    @property
    def kolor(self):
        return KOLOR_IBWR.get(self.status, "secondary")

    def lista_dodatkowych(self):
        wynik = []
        for linia in self.dodatkowe_zagrozenia.splitlines():
            linia = linia.strip()
            if not linia:
                continue
            for sep in (" – ", " - ", ":"):
                if sep in linia:
                    nazwa, srodki = linia.split(sep, 1)
                    wynik.append((nazwa.strip(), srodki.strip()))
                    break
            else:
                wynik.append((linia, ""))
        return wynik


# --- Checklista ----------------------------------------------------------------

class PunktChecklisty(models.Model):
    """Punkt „ręczny” checklisty wejścia na budowę (zaznaczany ptaszkiem). Lista ustawiana raz w panelu."""

    nazwa = models.CharField("punkt", max_length=200)
    opis = models.CharField("podpowiedź", max_length=300, blank=True)
    kolejnosc = models.PositiveIntegerField("kolejność", default=100)
    aktywny = models.BooleanField("aktywny", default=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "punkt checklisty (ręczny)"
        verbose_name_plural = "punkty checklisty (ręczne)"
        ordering = ["kolejnosc", "nazwa"]

    def __str__(self):
        return self.nazwa


class OdhaczeniePunktu(models.Model):
    budowa = models.ForeignKey("budowy.Budowa", on_delete=models.CASCADE, related_name="odhaczenia")
    punkt = models.ForeignKey(PunktChecklisty, on_delete=models.CASCADE, related_name="odhaczenia")
    zrobione = models.BooleanField("zrobione", default=False)
    nie_dotyczy = models.BooleanField("nie dotyczy tej budowy", default=False)
    data = models.DateField("data", null=True, blank=True)
    kto = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    uwagi = models.CharField("uwagi", max_length=300, blank=True)
    plik = models.FileField("załącznik", upload_to=sciezka_wejscie, blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "odhaczenie punktu checklisty"
        verbose_name_plural = "odhaczenia punktów checklisty"
        constraints = [models.UniqueConstraint(fields=["budowa", "punkt"], name="punkt_raz_na_budowie")]


# --- Dokumenty firmy -------------------------------------------------------------

class RodzajDokumentuFirmy(models.TextChoices):
    POLISA_OC = "polisa_oc", "Polisa OC"
    KRS = "krs", "Odpis z KRS / CEIDG"
    ZUS = "zus", "Zaświadczenie o niezaleganiu – ZUS"
    US = "us", "Zaświadczenie o niezaleganiu – urząd skarbowy"
    CERTYFIKAT = "certyfikat", "Certyfikat / referencje"
    INNY = "inny", "Inny"


class DokumentFirmy(models.Model):
    rodzaj = models.CharField("rodzaj", max_length=20, choices=RodzajDokumentuFirmy.choices)
    nazwa = models.CharField("nazwa / opis", max_length=200, help_text="np. Polisa OC działalności 2026")
    numer = models.CharField("numer", max_length=100, blank=True)
    data_waznosci = models.DateField("ważny do", null=True, blank=True, help_text="Puste = bezterminowy.")
    plik = models.FileField("plik", upload_to=sciezka_firma, blank=True)
    wymagany_na_budowie = models.BooleanField(
        "wymagany przy wejściu na budowę", default=False,
        help_text="Zaznacz, a checklista każdej budowy sprawdzi, czy ten rodzaj dokumentu jest ważny.",
    )
    uwagi = models.CharField("uwagi", max_length=300, blank=True)
    dodano = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "dokument firmy"
        verbose_name_plural = "dokumenty firmy"
        ordering = ["rodzaj", "-data_waznosci"]

    def __str__(self):
        return self.nazwa

    @property
    def status(self):
        return status_terminu(self.data_waznosci)
