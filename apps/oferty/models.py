from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from simple_history.models import HistoricalRecords

GROSZ = Decimal("0.01")
DNI_DO_KONTAKTU = 7


def zaokr(kwota):
    return Decimal(kwota).quantize(GROSZ, rounding=ROUND_HALF_UP)


class Jednostka(models.TextChoices):
    M2 = "m2", "m²"
    MB = "mb", "mb"
    SZT = "szt", "szt."
    KPL = "kpl", "kpl."
    RYCZALT = "ryczalt", "ryczałt"


class RodzajPozycji(models.TextChoices):
    SYSTEM = "system", "System posadzki"
    PRZYGOTOWANIE = "przygotowanie", "Przygotowanie podłoża"
    DODATKOWA = "dodatkowa", "Pozycja dodatkowa"


class PozycjaCennika(models.Model):
    """Pozycja cennika – system posadzki albo prace dodatkowe (gruntowanie, cokoliki…)."""

    nazwa = models.CharField("nazwa", max_length=200)
    rodzaj = models.CharField("rodzaj", max_length=20, choices=RodzajPozycji.choices, default=RodzajPozycji.SYSTEM)
    jednostka = models.CharField("jednostka", max_length=10, choices=Jednostka.choices, default=Jednostka.M2)
    cena_netto = models.DecimalField("cena netto [zł / jedn.]", max_digits=12, decimal_places=2)
    koszt = models.DecimalField(
        "koszt własny [zł / jedn.]", max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Opcjonalnie. Służy tylko do liczenia marży w aplikacji – nigdy nie trafia do oferty dla klienta.",
    )
    opis = models.TextField(
        "opis do oferty", blank=True, help_text="np. układ warstw, grubość, wykończenie – pojawi się w dokumencie oferty."
    )
    aktywna = models.BooleanField("aktywna", default=True, help_text="Nieaktywne pozycje nie pojawiają się w kalkulatorze.")
    kolejnosc = models.PositiveIntegerField("kolejność", default=100)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "pozycja cennika"
        verbose_name_plural = "cennik"
        ordering = ["rodzaj", "kolejnosc", "nazwa"]

    def __str__(self):
        return self.nazwa

    @property
    def marza_procent(self):
        if self.koszt is None or not self.cena_netto:
            return None
        return zaokr((self.cena_netto - self.koszt) / self.cena_netto * 100)


class Status(models.TextChoices):
    ROBOCZA = "robocza", "Robocza"
    WYSLANA = "wyslana", "Wysłana"
    NEGOCJACJE = "negocjacje", "Negocjacje"
    WYGRANA = "wygrana", "Wygrana"
    PRZEGRANA = "przegrana", "Przegrana"
    ANULOWANA = "anulowana", "Anulowana"


STATUSY_OTWARTE = [Status.WYSLANA, Status.NEGOCJACJE]
STATUSY_ROZSTRZYGNIETE = [Status.WYGRANA, Status.PRZEGRANA]

KOLOR_STATUSU = {
    Status.ROBOCZA: "secondary",
    Status.WYSLANA: "info",
    Status.NEGOCJACJE: "warning",
    Status.WYGRANA: "success",
    Status.PRZEGRANA: "danger",
    Status.ANULOWANA: "dark",
}


class PowodPrzegranej(models.TextChoices):
    CENA = "cena", "Cena"
    TERMIN = "termin", "Termin realizacji"
    KONKURENCJA = "konkurencja", "Wybrano konkurencję (inne powody)"
    REZYGNACJA = "rezygnacja", "Inwestor zrezygnował / przesunął inwestycję"
    TECHNOLOGIA = "technologia", "Wybrano inną technologię"
    BRAK_ODPOWIEDZI = "brak_odpowiedzi", "Brak odpowiedzi klienta"
    INNY = "inny", "Inny"


class Oferta(models.Model):
    numer = models.CharField("numer", max_length=30, blank=True, help_text="Nadawany automatycznie, np. OF/2026/0001.")
    wersja = models.PositiveIntegerField("wersja", default=1)
    aktualna = models.BooleanField("aktualna wersja", default=True)
    poprzednia = models.ForeignKey(
        "self", verbose_name="poprzednia wersja", null=True, blank=True, on_delete=models.SET_NULL, related_name="nastepne"
    )
    klient = models.ForeignKey("budowy.Klient", verbose_name="klient", on_delete=models.PROTECT, related_name="oferty")
    nazwa = models.CharField("inwestycja / obiekt", max_length=200, help_text="np. Hala magazynowa – posadzka epoksydowa")
    adres_budowy = models.CharField("adres budowy", max_length=300, blank=True)
    miasto = models.CharField("miasto", max_length=100, blank=True)
    powierzchnia_m2 = models.DecimalField("powierzchnia [m²]", max_digits=10, decimal_places=2, null=True, blank=True)
    handlowiec = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="handlowiec", null=True, blank=True, on_delete=models.SET_NULL, related_name="oferty"
    )
    status = models.CharField("status", max_length=20, choices=Status.choices, default=Status.ROBOCZA)
    data_wystawienia = models.DateField("data wystawienia", default=timezone.localdate)
    data_wyslania = models.DateField("data wysłania", null=True, blank=True)
    data_rozstrzygniecia = models.DateField("data wygranej / przegranej", null=True, blank=True)
    waznosc_dni = models.PositiveIntegerField("ważność oferty [dni]", default=30)
    termin_realizacji = models.CharField("termin realizacji", max_length=200, blank=True, default="do uzgodnienia")
    warunki_platnosci = models.CharField("warunki płatności", max_length=300, blank=True, default="przelew 30 dni od daty wystawienia faktury")
    uwagi = models.TextField(
        "uwagi i wyłączenia",
        blank=True,
        default="Oferta nie obejmuje: zapewnienia mediów (prąd 400 V, woda), ogrzewania obiektu, przygotowania podłoża przez GW.",
    )
    rabat_procent = models.DecimalField("rabat [%]", max_digits=5, decimal_places=2, default=0)
    vat_procent = models.PositiveIntegerField("VAT [%]", default=23, choices=[(23, "23%"), (8, "8%"), (0, "0% / odwrotne obciążenie")])
    nastepny_kontakt = models.DateField("następny kontakt z klientem", null=True, blank=True)
    powod_przegranej = models.CharField("powód przegranej", max_length=20, choices=PowodPrzegranej.choices, blank=True)
    powod_opis = models.CharField("szczegóły (np. cena konkurencji)", max_length=300, blank=True)
    notatki_wewnetrzne = models.TextField("notatki wewnętrzne", blank=True, help_text="Nie trafiają do dokumentu dla klienta.")
    # Etap 3: wygrana oferta zamieni się w budowę.
    budowa = models.ForeignKey("budowy.Budowa", null=True, blank=True, on_delete=models.SET_NULL, related_name="oferty")
    utworzono = models.DateTimeField("utworzono", auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "oferta"
        verbose_name_plural = "oferty"
        ordering = ["-data_wystawienia", "-numer", "-wersja"]
        constraints = [models.UniqueConstraint(fields=["numer", "wersja"], name="unikalny_numer_wersji_oferty")]

    def __str__(self):
        return f"{self.pelny_numer} {self.nazwa}"

    def get_absolute_url(self):
        return reverse("oferty:szczegoly", args=[self.pk])

    @property
    def pelny_numer(self):
        return self.numer if self.wersja == 1 else f"{self.numer}/v{self.wersja}"

    @property
    def kolor_statusu(self):
        return KOLOR_STATUSU.get(self.status, "secondary")

    @property
    def otwarta(self):
        return self.status in STATUSY_OTWARTE

    @property
    def wazna_do(self):
        baza = self.data_wyslania or self.data_wystawienia
        return baza + timedelta(days=self.waznosc_dni) if baza else None

    def save(self, *args, **kwargs):
        if not self.numer:
            self.numer = self._nastepny_numer()
        super().save(*args, **kwargs)

    def _nastepny_numer(self):
        rok = (self.data_wystawienia or timezone.localdate()).year
        prefiks = f"OF/{rok}/"
        numery = Oferta.objects.filter(numer__startswith=prefiks).values_list("numer", flat=True)
        nr = max((int(n.rsplit("/", 1)[1]) for n in numery if n.rsplit("/", 1)[1].isdigit()), default=0)
        return f"{prefiks}{nr + 1:04d}"

    # --- Wartości ---
    def wariant_glowny(self):
        """Wariant liczony do statystyk: wybrany przy wygranej, a jeśli żaden – pierwszy."""
        warianty = list(self.warianty.all())
        for w in warianty:
            if w.wybrany:
                return w
        return warianty[0] if warianty else None

    @property
    def wartosc_netto(self):
        w = self.wariant_glowny()
        return w.podsumowanie()["netto"] if w else Decimal("0")


class Wariant(models.Model):
    oferta = models.ForeignKey(Oferta, on_delete=models.CASCADE, related_name="warianty")
    nazwa = models.CharField("nazwa wariantu", max_length=150, default="Wariant A")
    opis = models.TextField("opis wariantu", blank=True)
    kolejnosc = models.PositiveIntegerField("kolejność", default=1)
    wybrany = models.BooleanField("wybrany przez klienta", default=False)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "wariant oferty"
        verbose_name_plural = "warianty oferty"
        ordering = ["kolejnosc", "pk"]

    def __str__(self):
        return f"{self.oferta.pelny_numer} – {self.nazwa}"

    def podsumowanie(self):
        """Sumy wariantu. Rabat i VAT są wspólne dla całej oferty."""
        pozycje = list(self.pozycje.all())
        przed_rabatem = sum((p.wartosc for p in pozycje), Decimal("0"))
        rabat = zaokr(przed_rabatem * self.oferta.rabat_procent / 100)
        netto = przed_rabatem - rabat
        vat = zaokr(netto * self.oferta.vat_procent / 100)
        koszt = sum((p.koszt_razem for p in pozycje if p.koszt_razem is not None), Decimal("0"))
        pelny_koszt = all(p.koszt_razem is not None for p in pozycje) and bool(pozycje)
        marza = netto - koszt if pelny_koszt else None
        return {
            "przed_rabatem": przed_rabatem,
            "rabat": rabat,
            "netto": netto,
            "vat": vat,
            "brutto": netto + vat,
            "koszt": koszt if pelny_koszt else None,
            "marza": marza,
            "marza_procent": zaokr(marza / netto * 100) if marza is not None and netto else None,
        }


class PozycjaOferty(models.Model):
    wariant = models.ForeignKey(Wariant, on_delete=models.CASCADE, related_name="pozycje")
    pozycja_cennika = models.ForeignKey(
        PozycjaCennika, verbose_name="z cennika", null=True, blank=True, on_delete=models.SET_NULL
    )
    nazwa = models.CharField("nazwa", max_length=200)
    opis = models.TextField("opis", blank=True)
    jednostka = models.CharField("jedn.", max_length=10, choices=Jednostka.choices, default=Jednostka.M2)
    ilosc = models.DecimalField("ilość", max_digits=12, decimal_places=2, default=0)
    cena_netto = models.DecimalField("cena netto", max_digits=12, decimal_places=2, default=0)
    koszt_jednostkowy = models.DecimalField("koszt / jedn.", max_digits=12, decimal_places=2, null=True, blank=True)
    kolejnosc = models.PositiveIntegerField("kolejność", default=0)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "pozycja oferty"
        verbose_name_plural = "pozycje oferty"
        ordering = ["kolejnosc", "pk"]

    def __str__(self):
        return self.nazwa

    @property
    def wartosc(self):
        return zaokr(self.ilosc * self.cena_netto)

    @property
    def koszt_razem(self):
        return zaokr(self.ilosc * self.koszt_jednostkowy) if self.koszt_jednostkowy is not None else None


class FormaKontaktu(models.TextChoices):
    TELEFON = "telefon", "Telefon"
    EMAIL = "email", "E-mail"
    SPOTKANIE = "spotkanie", "Spotkanie"
    INNE = "inne", "Inne"


class Kontakt(models.Model):
    """Notatka z kontaktu z klientem w sprawie oferty (follow-up)."""

    oferta = models.ForeignKey(Oferta, on_delete=models.CASCADE, related_name="kontakty")
    data = models.DateField("data", default=timezone.localdate)
    forma = models.CharField("forma", max_length=20, choices=FormaKontaktu.choices, default=FormaKontaktu.TELEFON)
    notatka = models.TextField("notatka")
    kto = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "kontakt w sprawie oferty"
        verbose_name_plural = "kontakty w sprawie ofert"
        ordering = ["-data", "-pk"]

    def __str__(self):
        return f"{self.data} {self.get_forma_display()}"
