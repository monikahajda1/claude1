"""Alerty dotyczące budów (terminy, braki w obsadzie) do ekranu „Co dziś?”."""

from dataclasses import dataclass

from django.utils import timezone

from apps.budowy.models import ETAPY_AKTYWNE, Etap

DNI_PRZED_STARTEM = 14


@dataclass
class ZadanieBudowy:
    budowa: object
    tekst: str
    kolor: str  # danger / warning / info
    waga: int


def zadania_budow(budowy, dzis=None, z_bhp=False):
    dzis = dzis or timezone.localdate()
    wynik = []
    for b in budowy.prefetch_related("pracownicy").select_related("klient", "kierownik"):
        aktywna = b.etap in ETAPY_AKTYWNE
        if aktywna and b.data_zakonczenia and b.data_zakonczenia < dzis:
            dni = (dzis - b.data_zakonczenia).days
            wynik.append(ZadanieBudowy(b, f"Minął planowany termin zakończenia ({dni} dni temu).", "danger", 0))
        if b.etap in (Etap.UMOWA, Etap.PRZYGOTOWANIE) and b.data_rozpoczecia:
            dni = (b.data_rozpoczecia - dzis).days
            if dni < 0:
                wynik.append(ZadanieBudowy(b, f"Planowany start był {-dni} dni temu, a budowa nie jest jeszcze „w realizacji”.", "warning", 2))
            elif dni <= DNI_PRZED_STARTEM:
                tekst = "Start dziś!" if dni == 0 else f"Start za {dni} dni – sprawdź dokumenty wejścia na budowę."
                wynik.append(ZadanieBudowy(b, tekst, "danger" if dni <= 3 else "info", 1 if dni <= 3 else 3))
        if aktywna and b.kierownik_id is None:
            wynik.append(ZadanieBudowy(b, "Brak przypisanego kierownika robót.", "warning", 2))
        if z_bhp and b.etap in (Etap.PRZYGOTOWANIE, Etap.REALIZACJA) and not b.pracownicy.all():
            wynik.append(ZadanieBudowy(b, "Brak przypisanych pracowników (ekipy).", "warning", 2))
    wynik.sort(key=lambda z: (z.waga, z.budowa.data_rozpoczecia or dzis))
    return wynik
