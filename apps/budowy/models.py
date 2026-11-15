from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from simple_history.models import HistoricalRecords


class Klient(models.Model):
    nazwa = models.CharField("nazwa firmy", max_length=200)
    nip = models.CharField("NIP", max_length=20, blank=True)
    adres = models.CharField("adres", max_length=300, blank=True)
    osoba_kontaktowa = models.CharField("osoba kontaktowa", max_length=150, blank=True)
    telefon = models.CharField("telefon", max_length=30, blank=True)
    email = models.EmailField("e-mail", blank=True)
    uwagi = models.TextField("uwagi", blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "klient"
        verbose_name_plural = "klienci"
        ordering = ["nazwa"]

    def __str__(self):
        return self.nazwa

    def get_absolute_url(self):
        return reverse("budowy:klient_edytuj", args=[self.pk])


class Etap(models.TextChoices):
    """Etapy budowy – kolejność ma znaczenie. Oferty są osobną kartoteką (moduł Oferty)."""

    UMOWA = "umowa", "Umowa podpisana"
    PRZYGOTOWANIE = "przygotowanie", "Przygotowanie (BHP, wejście na budowę)"
    REALIZACJA = "realizacja", "W realizacji"
    ROZLICZENIE = "rozliczenie", "Odbiory i rozliczenie"
    DOKUMENTACJA = "dokumentacja", "Dokumentacja powykonawcza"
    ZAKONCZONA = "zakonczona", "Zakończona"
    WSTRZYMANA = "wstrzymana", "Wstrzymana"


# Etapy, w których budowa jest „aktywna” (ludzie i sprzęt są potrzebni).
ETAPY_AKTYWNE = [Etap.UMOWA, Etap.PRZYGOTOWANIE, Etap.REALIZACJA, Etap.ROZLICZENIE]

KOLOR_ETAPU = {
    Etap.UMOWA: "info",
    Etap.PRZYGOTOWANIE: "warning",
    Etap.REALIZACJA: "primary",
    Etap.ROZLICZENIE: "primary",
    Etap.DOKUMENTACJA: "dark",
    Etap.ZAKONCZONA: "success",
    Etap.WSTRZYMANA: "danger",
}


class Budowa(models.Model):
    numer = models.CharField("numer", max_length=30, unique=True, blank=True, help_text="Nadawany automatycznie, np. B/2026/001.")
    nazwa = models.CharField("nazwa budowy", max_length=200)
    klient = models.ForeignKey(Klient, verbose_name="klient (inwestor / generalny wykonawca)", on_delete=models.PROTECT, related_name="budowy")
    adres = models.CharField("adres budowy", max_length=300)
    miasto = models.CharField("miasto", max_length=100, blank=True)
    etap = models.CharField("etap", max_length=20, choices=Etap.choices, default=Etap.UMOWA)
    kierownik = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="kierownik robót",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="budowy_kierowane",
    )
    system_posadzki = models.CharField("system posadzki", max_length=200, blank=True, help_text="np. epoksydowa samopoziomująca 2 mm")
    powierzchnia_m2 = models.DecimalField("powierzchnia [m²]", max_digits=10, decimal_places=2, null=True, blank=True)
    wartosc_netto = models.DecimalField("wartość netto [zł]", max_digits=12, decimal_places=2, null=True, blank=True)
    data_rozpoczecia = models.DateField("planowany start", null=True, blank=True)
    data_zakonczenia = models.DateField("planowane zakończenie", null=True, blank=True)
    pracownicy = models.ManyToManyField("bhp.Pracownik", verbose_name="pracownicy na budowie", blank=True, related_name="budowy")
    sprzet = models.ManyToManyField("bhp.Sprzet", verbose_name="sprzęt na budowie", blank=True, related_name="budowy")
    uwagi = models.TextField("uwagi", blank=True)
    utworzono = models.DateTimeField("utworzono", auto_now_add=True)
    history = HistoricalRecords(m2m_fields=[pracownicy, sprzet])

    class Meta:
        verbose_name = "budowa"
        verbose_name_plural = "budowy"
        ordering = ["-utworzono"]

    def __str__(self):
        return f"{self.numer} {self.nazwa}"

    def get_absolute_url(self):
        return reverse("budowy:szczegoly", args=[self.pk])

    @property
    def kolor_etapu(self):
        return KOLOR_ETAPU.get(self.etap, "secondary")

    @property
    def aktywna(self):
        return self.etap in ETAPY_AKTYWNE

    def save(self, *args, **kwargs):
        if not self.numer:
            self.numer = self._nastepny_numer()
        super().save(*args, **kwargs)

    @staticmethod
    def _nastepny_numer():
        rok = timezone.localdate().year
        prefiks = f"B/{rok}/"
        ostatnie = Budowa.objects.filter(numer__startswith=prefiks).values_list("numer", flat=True)
        nr = max((int(n.rsplit("/", 1)[1]) for n in ostatnie if n.rsplit("/", 1)[1].isdigit()), default=0)
        return f"{prefiks}{nr + 1:03d}"
