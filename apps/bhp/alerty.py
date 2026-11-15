"""Zbieranie alertów o dokumentach pracowników i sprzętu.

Zasada: dla każdej osoby/sprzętu i każdego rodzaju dokumentu liczy się
NAJNOWSZY dokument. Jeśli ktoś zrobił nowe badania, stare (wygasłe)
już nie generują alarmu.
"""

from dataclasses import dataclass, field

from django.db.models import Prefetch

from apps.budowy.models import ETAPY_AKTYWNE, Budowa

from .models import Dotyczy, Pracownik, Sprzet, TypDokumentu
from .terminy import BRAK, Status, status_terminu


@dataclass
class Alert:
    rodzaj: str  # "pracownik" / "sprzet"
    obiekt: object
    typ: TypDokumentu
    dokument: object | None
    status: Status
    budowy: list = field(default_factory=list)


def _lepszy(a, b):
    """Który z dwóch dokumentów tego samego rodzaju jest aktualny."""
    if a is None:
        return b
    if a.data_waznosci is None:
        return a
    if b.data_waznosci is None:
        return b
    return a if a.data_waznosci >= b.data_waznosci else b


def aktualne_dokumenty(obiekt):
    """Słownik: typ_id -> najnowszy dokument danego rodzaju."""
    wynik = {}
    for dok in obiekt.dokumenty.all():
        wynik[dok.typ_id] = _lepszy(wynik.get(dok.typ_id), dok)
    return wynik


def stan_dokumentow(obiekt, typy, dzis=None):
    """Lista (typ, dokument|None, status) dla wszystkich rodzajów, które obiekt ma lub powinien mieć."""
    aktualne = aktualne_dokumenty(obiekt)
    wiersze = []
    for typ in typy:
        dok = aktualne.get(typ.pk)
        if dok is not None:
            wiersze.append((typ, dok, status_terminu(dok.data_waznosci, dzis)))
        elif typ.wymagany:
            wiersze.append((typ, None, BRAK))
    return wiersze


def _aktywne_budowy_prefetch():
    return Prefetch("budowy", queryset=Budowa.objects.filter(etap__in=ETAPY_AKTYWNE), to_attr="budowy_aktywne")


def _zbierz(rodzaj, queryset, typy, dzis):
    alerty = []
    for obiekt in queryset:
        for typ, dok, status in stan_dokumentow(obiekt, typy, dzis):
            if status.alert:
                alerty.append(Alert(rodzaj, obiekt, typ, dok, status, obiekt.budowy_aktywne))
    return alerty


def alerty_bhp(dzis=None, pracownicy=None, sprzet=None):
    """Wszystkie alerty, od najpilniejszych. Można zawęzić do podanych pracowników/sprzętu."""
    typy_p = list(TypDokumentu.objects.filter(dotyczy=Dotyczy.PRACOWNIK))
    typy_s = list(TypDokumentu.objects.filter(dotyczy=Dotyczy.SPRZET))
    if pracownicy is None:
        pracownicy = Pracownik.objects.filter(aktywny=True)
    if sprzet is None:
        sprzet = Sprzet.objects.filter(aktywny=True)
    pracownicy = pracownicy.prefetch_related("dokumenty", _aktywne_budowy_prefetch())
    sprzet = sprzet.prefetch_related("dokumenty", _aktywne_budowy_prefetch())
    alerty = _zbierz("pracownik", pracownicy, typy_p, dzis) + _zbierz("sprzet", sprzet, typy_s, dzis)
    alerty.sort(key=lambda a: (a.status.waga, a.status.dni if a.status.dni is not None else -99999, str(a.obiekt)))
    return alerty
