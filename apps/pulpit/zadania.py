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


@dataclass
class ZadanieOferty:
    oferta: object
    tekst: str
    kolor: str
    waga: int


def zadania_ofert(oferty, dzis=None):
    """Oferty wymagające kontaktu z klientem oraz takie, którym kończy się ważność."""
    from apps.oferty.models import STATUSY_OTWARTE

    dzis = dzis or timezone.localdate()
    wynik = []
    for o in oferty.filter(aktualna=True, status__in=STATUSY_OTWARTE).select_related("klient", "handlowiec"):
        if o.nastepny_kontakt and o.nastepny_kontakt <= dzis:
            dni = (dzis - o.nastepny_kontakt).days
            od_wyslania = (dzis - o.data_wyslania).days if o.data_wyslania else None
            tekst = "Czas na kontakt z klientem" + (f" (spóźnione o {dni} dni)" if dni else " – dziś")
            if od_wyslania is not None:
                tekst += f". Wysłana {od_wyslania} dni temu."
            wynik.append(ZadanieOferty(o, tekst, "danger" if dni >= 3 else "warning", 0 if dni >= 3 else 1))
        waznosc = o.wazna_do
        if waznosc and 0 <= (waznosc - dzis).days <= 7:
            wynik.append(ZadanieOferty(o, f"Oferta traci ważność za {(waznosc - dzis).days} dni ({waznosc:%d.%m.%Y}).", "info", 2))
    wynik.sort(key=lambda z: (z.waga, z.oferta.nastepny_kontakt or dzis))
    return wynik


DNI_PRZED_KAUCJA_GWARANCJA = 30


def _termin(tekst, data, dzis):
    dni = (data - dzis).days
    if dni < 0:
        return f"{tekst} – termin minął {-dni} dni temu ({data:%d.%m.%Y})", "danger", 0
    if dni == 0:
        return f"{tekst} – termin dziś", "danger", 0
    return f"{tekst} – za {dni} dni ({data:%d.%m.%Y})", "info" if dni > 7 else "warning", 3 if dni > 7 else 1


def zadania_umow(budowy, dzis=None):
    """Umowy: brak danych/skanu, zwrot kaucji, koniec gwarancji (dla osób z dostępem do umów)."""
    from apps.core.templatetags.pomocnicze import zl
    from apps.umowy.models import FormaZabezpieczenia, Umowa

    dzis = dzis or timezone.localdate()
    wynik = []
    umowy = {u.budowa_id: u for u in Umowa.objects.filter(budowa__in=budowy).prefetch_related("aneksy")}
    for b in budowy.select_related("klient"):
        umowa = umowy.get(b.pk)
        if umowa is None:
            if b.etap in ETAPY_AKTYWNE:
                wynik.append(ZadanieBudowy(b, "Brak danych umowy – uzupełnij (terminy, gwarancja, kaucja).", "warning", 2))
            continue
        if not umowa.skan and b.etap != Etap.ZAKONCZONA:
            wynik.append(ZadanieBudowy(b, "Brak skanu podpisanej umowy.", "warning", 2))
        if umowa.zabezpieczenie_forma != FormaZabezpieczenia.BRAK and umowa.zabezpieczenie_procent:
            for nr, data, zwrocono, kwota in (
                (1, umowa.zwrot1_data, umowa.zwrot1_zwrocono, umowa.zwrot1_kwota),
                (2, umowa.zwrot2_data, umowa.zwrot2_zwrocono, umowa.zwrot2_kwota),
            ):
                if data and not zwrocono and (data - dzis).days <= DNI_PRZED_KAUCJA_GWARANCJA:
                    tekst, kolor, waga = _termin(f"Zwrot zabezpieczenia cz. {nr} ({zl(kwota)})", data, dzis)
                    wynik.append(ZadanieBudowy(b, tekst + " – upomnij się u klienta.", kolor, waga))
        koniec = umowa.koniec_gwarancji
        if koniec and 0 <= (koniec - dzis).days <= DNI_PRZED_KAUCJA_GWARANCJA:
            tekst, kolor, waga = _termin("Koniec gwarancji", koniec, dzis)
            wynik.append(ZadanieBudowy(b, tekst + " – zaplanuj przegląd gwarancyjny.", kolor, waga))
    wynik.sort(key=lambda z: z.waga)
    return wynik
