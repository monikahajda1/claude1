"""Fikcyjne umowy, zakresy prac i aneksy – używane przez komendę `dane_testowe`."""

from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile

from apps.budowy.models import Budowa, Etap
from apps.oferty.models import Oferta, PozycjaCennika, Status

from .models import Aneks, FormaZabezpieczenia, PozycjaZakresu, SposobRozliczenia, Umowa
from .operacje import utworz_budowe_z_oferty, zapisz_aneks

FIKCYJNY_PDF = b"%PDF-1.4\n% fikcyjny skan umowy - dane testowe\n"


def _zakres(budowa):
    """Prosty zakres z cennika: system na całą powierzchnię + gruntowanie + cokolik."""
    m2 = budowa.powierzchnia_m2 or Decimal("500")
    pozycje = [
        ("Szlifowanie podłoża betonowego", m2),
        ("Gruntowanie żywicą epoksydową", m2),
        ("Posadzka epoksydowa samopoziomująca 3 mm", m2),
        ("Cokolik żywiczny h=10 cm", Decimal(int(m2 ** Decimal("0.5") * 3))),
    ]
    for i, (nazwa, ilosc) in enumerate(pozycje, 1):
        c = PozycjaCennika.objects.get(nazwa=nazwa)
        PozycjaZakresu.objects.create(budowa=budowa, pozycja_cennika=c, nazwa=c.nazwa, jednostka=c.jednostka,
                                      ilosc=ilosc, cena_netto=c.cena_netto, kolejnosc=i)
    return sum((p.wartosc for p in budowa.zakres.all()), Decimal("0"))


def umowy_dla_budow(dzis):
    """Umowy dla budów z danych testowych (bez ofert). Różne scenariusze przypomnień."""
    for b in Budowa.objects.filter(oferty=None).order_by("pk"):
        if b.nazwa.startswith("Biurowiec"):
            continue  # celowo bez umowy → alert „Brak danych umowy”
        wartosc = _zakres(b)
        start = b.data_rozpoczecia or dzis
        umowa = Umowa(
            budowa=b, numer=f"GW/{b.pk:03d}/2026 (test)", data_podpisania=start - timedelta(days=21),
            wartosc_netto=wartosc, gwarancja_miesiecy=36, kary_umowne="0,2% za dzień zwłoki, maks. 10%",
            zabezpieczenie_forma=FormaZabezpieczenia.KAUCJA, zabezpieczenie_procent=Decimal("5"),
        )
        if b.nazwa.startswith("Szpital"):
            umowa.sposob_rozliczenia = SposobRozliczenia.RYCZALT
        if b.etap in (Etap.DOKUMENTACJA, Etap.ZAKONCZONA):
            umowa.data_odbioru_koncowego = b.data_zakonczenia
            umowa.zwrot1_data = b.data_zakonczenia + timedelta(days=30)
        if b.nazwa.startswith("Magazyn chłodniczy"):
            umowa.zwrot1_data = dzis - timedelta(days=5)  # kaucja po terminie – nie zwrócona
        if b.nazwa.startswith("Archiwum"):
            # Gwarancja kończy się za ~3 tygodnie, część 2 kaucji do odebrania.
            umowa.gwarancja_miesiecy = 12
            umowa.data_odbioru_koncowego = dzis - timedelta(days=365 - 21)
            umowa.zwrot1_data = umowa.data_odbioru_koncowego + timedelta(days=30)
            umowa.zwrot1_zwrocono = True
            umowa.zwrot2_data = dzis + timedelta(days=25)
        if not b.nazwa.startswith(("Mleczarnia", "Pralnia")):
            umowa.skan.save("umowa.pdf", ContentFile(FIKCYJNY_PDF), save=False)
        umowa.save()
        umowa.synchronizuj_budowe()
        if b.nazwa.startswith("Hala magazynowa A"):
            zapisz_aneks(Aneks(umowa=umowa, numer="1", data=dzis - timedelta(days=10),
                               opis="Roboty dodatkowe: naprawa rys i dodatkowe 120 mb cokolików.",
                               zmiana_wartosci=Decimal("12400"), nowy_termin_zakonczenia=b.data_zakonczenia + timedelta(days=14)))


def budowy_z_ofert(kierownicy, dzis, ile=3):
    """Kilka ostatnich wygranych ofert zamieniamy w budowy – tak jak zrobiłby to handlowiec."""
    etapy = [Etap.REALIZACJA, Etap.PRZYGOTOWANIE, Etap.UMOWA]
    wygrane = Oferta.objects.filter(status=Status.WYGRANA, aktualna=True, budowa=None).order_by("-data_rozstrzygniecia")[:ile]
    for i, oferta in enumerate(wygrane):
        start = dzis + timedelta(days=[-10, 5, 20][i % 3])
        budowa = Budowa(
            nazwa=oferta.nazwa, adres=oferta.adres_budowy or "ul. Testowa 1", miasto=oferta.miasto, etap=etapy[i % 3],
            kierownik=kierownicy[i % len(kierownicy)] if kierownicy else None, powierzchnia_m2=oferta.powierzchnia_m2,
            data_rozpoczecia=start, data_zakonczenia=start + timedelta(days=30),
        )
        w = oferta.wariant_glowny()
        umowa = Umowa(
            numer=f"ZL/{oferta.numer[-4:]}/2026 (test)", data_podpisania=oferta.data_rozstrzygniecia,
            wartosc_netto=w.podsumowanie()["netto"], vat_procent=oferta.vat_procent, gwarancja_miesiecy=60,
            zabezpieczenie_forma=FormaZabezpieczenia.KAUCJA if i != 2 else FormaZabezpieczenia.BRAK,
            zabezpieczenie_procent=Decimal("5") if i != 2 else 0,
        )
        utworz_budowe_z_oferty(oferta, budowa, umowa)
