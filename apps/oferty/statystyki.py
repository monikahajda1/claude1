"""Statystyki skuteczności ofert (liczone z aktualnych wersji ofert)."""

from collections import OrderedDict
from decimal import Decimal

from .models import PowodPrzegranej, RodzajPozycji, Status, zaokr

MIESIACE = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]
WYSLANE = {Status.WYSLANA, Status.NEGOCJACJE, Status.WYGRANA, Status.PRZEGRANA}


def system_glowny(oferta):
    """Nazwa najdroższej pozycji typu „system posadzki” w wariancie głównym."""
    w = oferta.wariant_glowny()
    if not w:
        return "—"
    systemy = [p for p in w.pozycje.all() if p.pozycja_cennika and p.pozycja_cennika.rodzaj == RodzajPozycji.SYSTEM]
    if not systemy:
        return "inne / bez systemu z cennika"
    return max(systemy, key=lambda p: p.wartosc).pozycja_cennika.nazwa


class Licznik:
    def __init__(self):
        self.wyslane = self.wygrane = self.przegrane = self.w_toku = 0
        self.w_wyslane = self.w_wygrane = self.w_przegrane = Decimal("0")

    def dodaj(self, oferta, wartosc):
        if oferta.status not in WYSLANE:
            return
        self.wyslane += 1
        self.w_wyslane += wartosc
        if oferta.status == Status.WYGRANA:
            self.wygrane += 1
            self.w_wygrane += wartosc
        elif oferta.status == Status.PRZEGRANA:
            self.przegrane += 1
            self.w_przegrane += wartosc
        else:
            self.w_toku += 1

    @property
    def skutecznosc(self):
        """% wygranych wśród rozstrzygniętych (bez ofert wciąż w toku)."""
        n = self.wygrane + self.przegrane
        return zaokr(Decimal(self.wygrane) / n * 100) if n else None

    @property
    def skutecznosc_wartosciowa(self):
        n = self.w_wygrane + self.w_przegrane
        return zaokr(self.w_wygrane / n * 100) if n else None


def policz(oferty):
    """oferty: lista ofert z pobranymi wariantami i pozycjami (prefetch)."""
    razem = Licznik()
    miesiace = OrderedDict((i, Licznik()) for i in range(1, 13))
    handlowcy, systemy = {}, {}
    powody = OrderedDict((k, {"nazwa": n, "liczba": 0, "wartosc": Decimal("0")}) for k, n in PowodPrzegranej.choices)
    dni_do_decyzji = []
    for o in oferty:
        wartosc = o.wartosc_netto
        razem.dodaj(o, wartosc)
        miesiace[o.data_wystawienia.month].dodaj(o, wartosc)
        handlowcy.setdefault(str(o.handlowiec or "— bez handlowca —"), Licznik()).dodaj(o, wartosc)
        systemy.setdefault(system_glowny(o), Licznik()).dodaj(o, wartosc)
        if o.status == Status.PRZEGRANA and o.powod_przegranej in powody:
            powody[o.powod_przegranej]["liczba"] += 1
            powody[o.powod_przegranej]["wartosc"] += wartosc
        if o.status in (Status.WYGRANA, Status.PRZEGRANA) and o.data_wyslania and o.data_rozstrzygniecia:
            dni_do_decyzji.append((o.data_rozstrzygniecia - o.data_wyslania).days)
    sortuj = lambda d: sorted(d.items(), key=lambda kv: -kv[1].w_wyslane)  # noqa: E731
    return {
        "razem": razem,
        "miesiace": [(MIESIACE[m - 1], l) for m, l in miesiace.items()],
        "handlowcy": sortuj(handlowcy),
        "systemy": sortuj(systemy),
        "powody": [p for p in powody.values() if p["liczba"]],
        "sredni_czas": round(sum(dni_do_decyzji) / len(dni_do_decyzji)) if dni_do_decyzji else None,
    }
