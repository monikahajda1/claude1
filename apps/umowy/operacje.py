"""Zamiana wygranej oferty w budowę z umową oraz obsługa aneksów."""

from decimal import Decimal

from django.db import transaction

from apps.oferty.models import zaokr
from apps.oferty.statystyki import system_glowny

from .models import PozycjaZakresu


def dane_poczatkowe_z_oferty(oferta):
    """Wartości do podpowiedzenia w formularzu „Utwórz budowę”."""
    wariant = oferta.wariant_glowny()
    netto = wariant.podsumowanie()["netto"] if wariant else Decimal("0")
    system = system_glowny(oferta)
    return {
        "budowa": {
            "nazwa": oferta.nazwa,
            "adres": oferta.adres_budowy,
            "miasto": oferta.miasto,
            "system_posadzki": "" if system in ("—", "inne / bez systemu z cennika") else system,
            "powierzchnia_m2": oferta.powierzchnia_m2,
        },
        "umowa": {"wartosc_netto": netto, "vat_procent": oferta.vat_procent},
    }


def kopiuj_zakres(oferta, budowa):
    """Pozycje wybranego wariantu → zakres prac budowy. Rabat oferty wliczamy w ceny jednostkowe."""
    wariant = oferta.wariant_glowny()
    if not wariant:
        return
    mnoznik = (Decimal("100") - oferta.rabat_procent) / Decimal("100")
    for i, p in enumerate(wariant.pozycje.all(), 1):
        PozycjaZakresu.objects.create(
            budowa=budowa, pozycja_cennika=p.pozycja_cennika, nazwa=p.nazwa, opis=p.opis,
            jednostka=p.jednostka, ilosc=p.ilosc, cena_netto=zaokr(p.cena_netto * mnoznik), kolejnosc=i,
        )


@transaction.atomic
def utworz_budowe_z_oferty(oferta, budowa, umowa):
    """budowa i umowa – niezapisane obiekty z formularzy."""
    budowa.klient = oferta.klient
    budowa.save()
    umowa.budowa = budowa
    umowa.save()
    kopiuj_zakres(oferta, budowa)
    oferta.budowa = budowa
    oferta.save(update_fields=["budowa"])
    umowa.synchronizuj_budowe()
    return budowa


@transaction.atomic
def zapisz_aneks(aneks):
    aneks.save()
    umowa = aneks.umowa
    budowa = umowa.budowa
    if aneks.nowy_termin_zakonczenia:
        # Obowiązuje termin z najnowszego aneksu, który go zmienia.
        ostatni = umowa.aneksy.exclude(nowy_termin_zakonczenia=None).order_by("-data", "-pk").first()
        if ostatni and budowa.data_zakonczenia != ostatni.nowy_termin_zakonczenia:
            budowa.data_zakonczenia = ostatni.nowy_termin_zakonczenia
            budowa.save(update_fields=["data_zakonczenia"])
    umowa.synchronizuj_budowe()
    return aneks


def suma_zakresu(budowa):
    return sum((p.wartosc for p in budowa.zakres.all()), Decimal("0"))
