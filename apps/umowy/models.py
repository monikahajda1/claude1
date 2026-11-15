import calendar
import os
import uuid
from decimal import Decimal

from django.db import models
from simple_history.models import HistoricalRecords

from apps.oferty.models import Jednostka, zaokr


def sciezka_skanu(instance, filename):
    """Losowa nazwa pliku – nie zdradza klienta ani kwot."""
    return f"umowy/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()[:10]}"


class SposobRozliczenia(models.TextChoices):
    OBMIAR = "obmiar", "Obmiar (faktycznie wykonane ilości × ceny)"
    RYCZALT = "ryczalt", "Ryczałt (kwota stała, fakturowana wg % zaawansowania)"


class FormaZabezpieczenia(models.TextChoices):
    BRAK = "brak", "Brak zabezpieczenia"
    KAUCJA = "kaucja", "Kaucja potrącana z faktur"
    GWARANCJA_BANKOWA = "bankowa", "Gwarancja bankowa"
    GWARANCJA_UBEZPIECZENIOWA = "ubezpieczeniowa", "Gwarancja ubezpieczeniowa"


class Umowa(models.Model):
    budowa = models.OneToOneField("budowy.Budowa", on_delete=models.CASCADE, related_name="umowa")
    numer = models.CharField("numer umowy", max_length=100, blank=True, help_text="Numer nadany przez klienta / GW.")
    data_podpisania = models.DateField("data podpisania", null=True, blank=True)
    wartosc_netto = models.DecimalField(
        "wartość netto z umowy [zł]", max_digits=12, decimal_places=2,
        help_text="Wartość pierwotna. Zmiany wprowadzaj aneksami – wartość aktualna przeliczy się sama.",
    )
    vat_procent = models.PositiveIntegerField("VAT [%]", default=23, choices=[(23, "23%"), (8, "8%"), (0, "0% / odwrotne obciążenie")])
    sposob_rozliczenia = models.CharField("sposób rozliczenia", max_length=20, choices=SposobRozliczenia.choices, default=SposobRozliczenia.OBMIAR)
    termin_platnosci_dni = models.PositiveIntegerField("termin płatności faktur [dni]", default=30)
    kary_umowne = models.CharField("kary umowne", max_length=300, blank=True, help_text="np. 0,2% za dzień zwłoki, maks. 10%")

    # Odbiór i gwarancja
    data_odbioru_koncowego = models.DateField("data odbioru końcowego", null=True, blank=True, help_text="Od tej daty liczy się gwarancja.")
    gwarancja_miesiecy = models.PositiveIntegerField("okres gwarancji [mies.]", null=True, blank=True, default=36)

    # Zabezpieczenie należytego wykonania (kaucja)
    zabezpieczenie_forma = models.CharField("forma zabezpieczenia", max_length=20, choices=FormaZabezpieczenia.choices, default=FormaZabezpieczenia.BRAK)
    zabezpieczenie_procent = models.DecimalField("zabezpieczenie [% wartości]", max_digits=5, decimal_places=2, default=0)
    zwrot1_procent = models.DecimalField(
        "część 1 do zwrotu [% zabezpieczenia]", max_digits=5, decimal_places=2, default=70,
        help_text="Zwykle 70% po odbiorze końcowym; reszta po okresie gwarancji/rękojmi.",
    )
    zwrot1_data = models.DateField("termin zwrotu części 1", null=True, blank=True)
    zwrot1_zwrocono = models.BooleanField("część 1 zwrócona", default=False)
    zwrot2_data = models.DateField("termin zwrotu części 2", null=True, blank=True)
    zwrot2_zwrocono = models.BooleanField("część 2 zwrócona", default=False)

    skan = models.FileField("skan podpisanej umowy (PDF)", upload_to=sciezka_skanu, blank=True)
    uwagi = models.TextField("uwagi", blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "umowa"
        verbose_name_plural = "umowy"

    def __str__(self):
        return f"Umowa {self.numer or 'b/n'} – {self.budowa}"

    # --- Wartości wyliczane ---
    @property
    def suma_aneksow(self):
        return sum((a.zmiana_wartosci for a in self.aneksy.all()), Decimal("0"))

    @property
    def wartosc_aktualna(self):
        return self.wartosc_netto + self.suma_aneksow

    @property
    def wartosc_brutto(self):
        return self.wartosc_aktualna + zaokr(self.wartosc_aktualna * self.vat_procent / 100)

    @property
    def zabezpieczenie_kwota(self):
        return zaokr(self.wartosc_aktualna * self.zabezpieczenie_procent / 100)

    @property
    def zwrot1_kwota(self):
        return zaokr(self.zabezpieczenie_kwota * self.zwrot1_procent / 100)

    @property
    def zwrot2_kwota(self):
        return self.zabezpieczenie_kwota - self.zwrot1_kwota

    @property
    def koniec_gwarancji(self):
        if not self.data_odbioru_koncowego or not self.gwarancja_miesiecy:
            return None
        d = self.data_odbioru_koncowego
        miesiac = d.month - 1 + self.gwarancja_miesiecy
        rok, miesiac = d.year + miesiac // 12, miesiac % 12 + 1
        dzien = min(d.day, calendar.monthrange(rok, miesiac)[1])
        return d.replace(year=rok, month=miesiac, day=dzien)

    def synchronizuj_budowe(self):
        """Wartość na budowie zawsze = aktualna wartość z umowy (wpisujemy raz)."""
        b = self.budowa
        if b.wartosc_netto != self.wartosc_aktualna:
            b.wartosc_netto = self.wartosc_aktualna
            b.save(update_fields=["wartosc_netto"])


class PozycjaZakresu(models.Model):
    """Zakres prac z umowy – podstawa rozliczeń miesięcznych (etap 5)."""

    budowa = models.ForeignKey("budowy.Budowa", on_delete=models.CASCADE, related_name="zakres")
    pozycja_cennika = models.ForeignKey("oferty.PozycjaCennika", null=True, blank=True, on_delete=models.SET_NULL, verbose_name="z cennika")
    nazwa = models.CharField("nazwa", max_length=200)
    opis = models.TextField("opis", blank=True)
    jednostka = models.CharField("jedn.", max_length=10, choices=Jednostka.choices, default=Jednostka.M2)
    ilosc = models.DecimalField("ilość", max_digits=12, decimal_places=2, default=0)
    cena_netto = models.DecimalField("cena netto", max_digits=12, decimal_places=2, default=0)
    kolejnosc = models.PositiveIntegerField("kolejność", default=0)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "pozycja zakresu prac"
        verbose_name_plural = "zakres prac"
        ordering = ["kolejnosc", "pk"]

    def __str__(self):
        return self.nazwa

    @property
    def wartosc(self):
        return zaokr(self.ilosc * self.cena_netto)


def sciezka_aneksu(instance, filename):
    return f"umowy/aneksy/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()[:10]}"


class Aneks(models.Model):
    umowa = models.ForeignKey(Umowa, on_delete=models.CASCADE, related_name="aneksy")
    numer = models.CharField("numer aneksu", max_length=50)
    data = models.DateField("data aneksu")
    opis = models.TextField("czego dotyczy")
    zmiana_wartosci = models.DecimalField(
        "zmiana wartości netto [zł]", max_digits=12, decimal_places=2, default=0,
        help_text="Kwota dodatnia – zwiększenie, ujemna (z minusem) – zmniejszenie. 0 – bez zmiany.",
    )
    nowy_termin_zakonczenia = models.DateField("nowy termin zakończenia", null=True, blank=True)
    skan = models.FileField("skan aneksu", upload_to=sciezka_aneksu, blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "aneks"
        verbose_name_plural = "aneksy"
        ordering = ["data", "pk"]

    def __str__(self):
        return f"Aneks {self.numer} z {self.data:%d.%m.%Y}"
