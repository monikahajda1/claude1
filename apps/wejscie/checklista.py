"""Checklista „czego brakuje” przy wejściu na budowę.

Punkty automatyczne program sprawdza sam na podstawie danych z innych modułów
(wpisanych raz). Punkty ręczne zaznacza się ptaszkiem.
"""

from dataclasses import dataclass

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils import timezone

from apps.bhp.alerty import alerty_bhp
from apps.materialy.operacje import materialy_budowy

from .models import KZM_ZATWIERDZONE, DokumentFirmy, OdhaczeniePunktu, PunktChecklisty, RodzajDokumentuFirmy, StatusIBWR


@dataclass
class Punkt:
    nazwa: str
    ok: bool
    szczegoly: str = ""
    link: str = ""
    reczny: bool = False
    punkt_id: int | None = None
    odhaczenie: object = None
    nie_dotyczy: bool = False


def _problemy(alerty, rodzaj):
    zle = [a for a in alerty if a.rodzaj == rodzaj and a.status.kod in ("wygasl", "brak")]
    return "; ".join(f"{a.obiekt}: {a.typ} – {a.status.opis}" for a in zle[:6]) + (" …" if len(zle) > 6 else ""), bool(zle)


def checklista(budowa, dzis=None, user=None):
    """user (opcjonalnie) – linki „przejdź” tylko do stron, które ta osoba może otworzyć."""
    from apps.konta import uprawnienia as u

    dzis = dzis or timezone.localdate()

    def moze(modul, edycja=False):
        if user is None:
            return True
        return u.moze_edytowac(user, modul) if edycja else u.moze_widziec(user, modul)

    url_budowy = budowa.get_absolute_url()
    url_wejscia = reverse("wejscie:budowa", args=[budowa.pk])
    punkty = []

    # 1. Umowa
    try:
        umowa = budowa.umowa
    except ObjectDoesNotExist:
        umowa = None
    punkty.append(Punkt("Umowa wpisana, ze skanem podpisanej umowy", bool(umowa and umowa.skan),
                        "" if umowa and umowa.skan else ("brak skanu" if umowa else "brak danych umowy"), url_budowy))

    # 2–3. Kierownik i ekipa
    punkty.append(Punkt("Kierownik robót przypisany", budowa.kierownik_id is not None, "", url_budowy))
    pracownicy = list(budowa.pracownicy.filter(aktywny=True))
    sprzet = list(budowa.sprzet.filter(aktywny=True))
    punkty.append(Punkt("Ekipa przypisana do budowy", bool(pracownicy), f"{len(pracownicy)} os." if pracownicy else "nikt nie jest przypisany",
                        reverse("budowy:ekipa", args=[budowa.pk]) if moze("bhp", edycja=True) else url_budowy))

    # 4–5. Dokumenty ekipy i sprzętu (te same dane co w module BHP)
    alerty = alerty_bhp(dzis, pracownicy=budowa.pracownicy.filter(aktywny=True), sprzet=budowa.sprzet.filter(aktywny=True))
    opis, zle = _problemy(alerty, "pracownik")
    punkty.append(Punkt("Badania i szkolenia ekipy ważne", bool(pracownicy) and not zle, opis or ("" if pracownicy else "brak ekipy"), url_budowy))
    opis, zle = _problemy(alerty, "sprzet")
    punkty.append(Punkt("Sprzęt przypisany, przeglądy ważne", bool(sprzet) and not zle, opis or ("" if sprzet else "brak przypisanego sprzętu"), url_budowy))

    # 6. Materiały: dokumenty i KZM
    materialy = materialy_budowy(budowa)
    braki = [f"{m.nazwa}: brak {', '.join(m.brakujace_typy())}" for m in materialy if m.brakujace_typy()]
    punkty.append(Punkt("Dokumenty materiałów kompletne (karta techn., DoP, karta charakterystyki)",
                        bool(materialy) and not braki, "; ".join(braki) if braki else ("" if materialy else "brak materiałów na liście"), url_wejscia))
    zatwierdzone = set(budowa.kzm.filter(status__in=KZM_ZATWIERDZONE).values_list("material_id", flat=True))
    bez_kzm = [m.nazwa for m in materialy if m.pk not in zatwierdzone]
    punkty.append(Punkt("KZM zatwierdzone dla wszystkich materiałów", bool(materialy) and not bez_kzm,
                        ("brak zatwierdzenia: " + ", ".join(bez_kzm)) if bez_kzm else "", url_wejscia))

    # 7. IBWR
    try:
        ibwr = budowa.ibwr
    except ObjectDoesNotExist:
        ibwr = None
    punkty.append(Punkt("IBWR zatwierdzona", bool(ibwr and ibwr.status == StatusIBWR.ZATWIERDZONA),
                        ibwr.get_status_display() if ibwr else "nie utworzono", reverse("wejscie:ibwr", args=[budowa.pk]) if moze("ibwr") else ""))

    # 8. Dokumenty firmy wymagane na budowie (np. polisa OC)
    rodzaje = DokumentFirmy.objects.filter(wymagany_na_budowie=True).values_list("rodzaj", flat=True).distinct()
    for rodzaj in rodzaje:
        najnowszy = DokumentFirmy.objects.filter(rodzaj=rodzaj).order_by("-data_waznosci").first()
        ok = najnowszy is not None and najnowszy.status.kod not in ("wygasl",)
        termin = budowa.data_zakonczenia
        uwaga = ""
        if ok and najnowszy.data_waznosci and termin and najnowszy.data_waznosci < termin:
            uwaga = f"ważny do {najnowszy.data_waznosci:%d.%m.%Y} – wygaśnie przed końcem budowy"
        punkty.append(Punkt(f"{RodzajDokumentuFirmy(rodzaj).label} ważny(a)", ok,
                            uwaga or (najnowszy.status.opis if najnowszy else "brak"), reverse("wejscie:firma") if moze("firma") else ""))

    # Punkty ręczne
    odhaczenia = {o.punkt_id: o for o in OdhaczeniePunktu.objects.filter(budowa=budowa)}
    for p in PunktChecklisty.objects.filter(aktywny=True):
        o = odhaczenia.get(p.pk)
        nie_dotyczy = bool(o and o.nie_dotyczy)
        punkty.append(Punkt(p.nazwa, bool(o and (o.zrobione or o.nie_dotyczy)),
                            p.opis if not o else (o.uwagi or ""), "", reczny=True, punkt_id=p.pk, odhaczenie=o, nie_dotyczy=nie_dotyczy))
    return punkty


def podsumowanie(punkty):
    zrobione = sum(1 for p in punkty if p.ok)
    return {"zrobione": zrobione, "wszystkie": len(punkty), "brakuje": len(punkty) - zrobione, "komplet": zrobione == len(punkty)}
