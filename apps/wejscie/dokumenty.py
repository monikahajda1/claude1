"""Dane do szablonów Word: KZM i IBWR. Wszystko pochodzi z danych wpisanych raz w innych modułach."""

from django.utils import timezone

from apps.bhp.alerty import stan_dokumentow
from apps.bhp.models import Dotyczy, TypDokumentu
from apps.materialy.models import KOLEJNOSC_TYPOW
from apps.materialy.operacje import materialy_budowy
from apps.oferty.dokument import liczba


def data(d):
    return d.strftime("%d.%m.%Y") if d else ""


def _naglowek_budowy(b):
    k = b.kierownik
    return {
        "budowa": b.nazwa,
        "numer_budowy": b.numer,
        "adres_budowy": ", ".join(x for x in [b.adres, b.miasto] if x),
        "klient": b.klient.nazwa,
        "kierownik": (k.get_full_name() or k.username) if k else "",
        "kierownik_telefon": getattr(k, "telefon", "") if k else "",
        "termin_od": data(b.data_rozpoczecia),
        "termin_do": data(b.data_zakonczenia),
        "system_posadzki": b.system_posadzki,
        "data": data(timezone.localdate()),
    }


# --- KZM -----------------------------------------------------------------------

def kontekst_kzm(kzm):
    m = kzm.material
    aktualne = m.aktualne_dokumenty()
    zalaczniki = [
        {"lp": i, "nazwa": aktualne[t].get_typ_display() + (f" ({aktualne[t].opis})" if aktualne[t].opis else "")}
        for i, t in enumerate([t for t in KOLEJNOSC_TYPOW if t in aktualne], 1)
    ]
    return {
        **_naglowek_budowy(kzm.budowa),
        "numer_kzm": kzm.numer,
        "data": data(kzm.data_zlozenia or timezone.localdate()),
        "material": m.nazwa,
        "producent": m.producent,
        "rodzaj_materialu": m.get_rodzaj_display(),
        "zastosowanie": kzm.zastosowanie or m.zastosowanie,
        "zalaczniki": zalaczniki,
    }


def kontekst_kzm_przykladowy():
    return {
        "budowa": "Hala magazynowa – posadzka epoksydowa", "numer_budowy": "B/2026/001", "adres_budowy": "ul. Testowa 10, Testowo",
        "klient": "Przykładowy Generalny Wykonawca S.A.", "kierownik": "Jan Przykładowy", "kierownik_telefon": "600 000 000",
        "termin_od": "01.12.2026", "termin_do": "20.12.2026", "system_posadzki": "Posadzka epoksydowa 2 mm",
        "numer_kzm": "KZM/2026/001/01", "data": data(timezone.localdate()), "material": "Grunt epoksydowy GE-Test",
        "producent": "Żywice Przykładowe Sp. z o.o.", "rodzaj_materialu": "Grunt",
        "zastosowanie": "Gruntowanie podłoża betonowego pod posadzkę epoksydową.",
        "zalaczniki": [{"lp": 1, "nazwa": "Karta techniczna"}, {"lp": 2, "nazwa": "Deklaracja właściwości użytkowych (DoP)"},
                       {"lp": 3, "nazwa": "Karta charakterystyki (SDS)"}],
    }


# --- IBWR ------------------------------------------------------------------------

def _data_dokumentu(stan, fraza):
    """Data ważności najnowszego dokumentu, którego nazwa rodzaju zawiera frazę."""
    pasujace = [(t, d) for t, d, _ in stan if d is not None and fraza.lower() in t.nazwa.lower()]
    if not pasujace:
        return "brak"
    # Liczy się dokument z terminem (np. szkolenie okresowe), a nie bezterminowy (np. wstępne).
    daty = [d.data_waznosci for _, d in pasujace if d.data_waznosci]
    return data(max(daty)) if daty else "bezterminowo"


def kontekst_ibwr(ibwr):
    b = ibwr.budowa
    typy_p = list(TypDokumentu.objects.filter(dotyczy=Dotyczy.PRACOWNIK))
    typy_s = list(TypDokumentu.objects.filter(dotyczy=Dotyczy.SPRZET))
    pracownicy = []
    for i, p in enumerate(b.pracownicy.filter(aktywny=True).prefetch_related("dokumenty__typ"), 1):
        stan = stan_dokumentow(p, typy_p)
        inne = [f"{t.nazwa} do {data(d.data_waznosci) or 'bezterm.'}" for t, d, _ in stan
                if d is not None and "badania lekarskie" not in t.nazwa.lower() and "szkolenie bhp" not in t.nazwa.lower()]
        pracownicy.append({
            "lp": i, "imie_nazwisko": f"{p.imie} {p.nazwisko}", "stanowisko": p.stanowisko, "firma": p.firma or "pracownik własny",
            "badania_do": _data_dokumentu(stan, "badania lekarskie"),
            "szkolenie_bhp_do": _data_dokumentu(stan, "szkolenie bhp"),
            "uprawnienia": "; ".join(inne),
        })
    sprzet = []
    for i, s in enumerate(b.sprzet.filter(aktywny=True).prefetch_related("dokumenty__typ"), 1):
        stan = stan_dokumentow(s, typy_s)
        sprzet.append({
            "lp": i, "nazwa": s.nazwa, "numer": s.numer_ewidencyjny,
            "przeglady": "; ".join(f"{t.nazwa} do {data(d.data_waznosci) or 'bezterm.'}" for t, d, _ in stan if d is not None) or "brak",
        })
    materialy = [
        {"lp": i, "nazwa": m.nazwa, "producent": m.producent, "rodzaj": m.get_rodzaj_display(),
         "karta_charakterystyki": "tak" if "sds" in m.aktualne_dokumenty() else "BRAK"}
        for i, m in enumerate([m for m in materialy_budowy(b) if m.chemiczny], 1)
    ]
    zagrozenia = [{"nazwa": z.nazwa, "srodki": z.srodki} for z in ibwr.zagrozenia.filter(aktywne=True)]
    zagrozenia += [{"nazwa": n, "srodki": s} for n, s in ibwr.lista_dodatkowych()]
    for i, z in enumerate(zagrozenia, 1):
        z["lp"] = i
    zakres = [{"lp": i, "nazwa": p.nazwa, "ilosc": liczba(p.ilosc), "jednostka": p.get_jednostka_display()}
              for i, p in enumerate(b.zakres.all(), 1)]
    o = ibwr.opracowal
    return {
        **_naglowek_budowy(b),
        "opracowal": (o.get_full_name() or o.username) if o else "",
        "zakres": zakres,
        "pracownicy": pracownicy,
        "sprzet": sprzet,
        "materialy": materialy,
        "zagrozenia": zagrozenia,
        "procedury_awaryjne": ibwr.procedury_awaryjne,
    }


def kontekst_ibwr_przykladowy():
    return {
        "budowa": "Hala magazynowa – posadzka epoksydowa", "numer_budowy": "B/2026/001", "adres_budowy": "ul. Testowa 10, Testowo",
        "klient": "Przykładowy Generalny Wykonawca S.A.", "kierownik": "Jan Przykładowy", "kierownik_telefon": "600 000 000",
        "termin_od": "01.12.2026", "termin_do": "20.12.2026", "system_posadzki": "Posadzka epoksydowa 2 mm",
        "data": data(timezone.localdate()), "opracowal": "Barbara Przykładowa",
        "zakres": [{"lp": 1, "nazwa": "Szlifowanie podłoża", "ilosc": "1 200", "jednostka": "m²"},
                   {"lp": 2, "nazwa": "Posadzka epoksydowa 2 mm", "ilosc": "1 200", "jednostka": "m²"}],
        "pracownicy": [{"lp": 1, "imie_nazwisko": "Adam Przykładowy", "stanowisko": "posadzkarz", "firma": "pracownik własny",
                        "badania_do": "31.12.2027", "szkolenie_bhp_do": "30.06.2028", "uprawnienia": ""}],
        "sprzet": [{"lp": 1, "nazwa": "Szlifierka do betonu", "numer": "SZL-01", "przeglady": "Przegląd techniczny do 01.06.2027"}],
        "materialy": [{"lp": 1, "nazwa": "Grunt epoksydowy GE-Test", "producent": "Żywice Przykładowe", "rodzaj": "Grunt",
                       "karta_charakterystyki": "tak"}],
        "zagrozenia": [{"lp": 1, "nazwa": "Kontakt z żywicami", "srodki": "Rękawice nitrylowe, okulary"}],
        "procedury_awaryjne": "Udzielić pierwszej pomocy, wezwać pomoc (tel. 112).",
    }


WSPOLNE_POLA = [
    ("budowa", "nazwa budowy"), ("numer_budowy", "numer budowy"), ("adres_budowy", "adres budowy"),
    ("klient", "klient / generalny wykonawca"), ("kierownik", "kierownik robót"), ("kierownik_telefon", "telefon kierownika"),
    ("termin_od", "termin rozpoczęcia"), ("termin_do", "termin zakończenia"), ("system_posadzki", "system posadzki"), ("data", "data dokumentu"),
]

POLA_KZM = [
    ("Budowa", WSPOLNE_POLA),
    ("Materiał", [("numer_kzm", "numer karty"), ("material", "nazwa materiału"), ("producent", "producent"),
                  ("rodzaj_materialu", "rodzaj materiału"), ("zastosowanie", "zastosowanie")]),
    ("Lista załączników – wiersz tabeli w pętli", [("{%tr for z in zalaczniki %}", "początek pętli"), ("z.lp / z.nazwa", "numer i nazwa załącznika"),
                                                   ("{%tr endfor %}", "koniec pętli")]),
]

POLA_IBWR = [
    ("Budowa", WSPOLNE_POLA + [("opracowal", "kto opracował"), ("procedury_awaryjne", "postępowanie w razie wypadku")]),
    ("Tabele (każda w pętli {%tr for … %} … {%tr endfor %})", [
        ("z in zakres → z.lp, z.nazwa, z.ilosc, z.jednostka", "zakres prac (bez cen)"),
        ("p in pracownicy → p.lp, p.imie_nazwisko, p.stanowisko, p.firma, p.badania_do, p.szkolenie_bhp_do, p.uprawnienia", "ekipa"),
        ("s in sprzet → s.lp, s.nazwa, s.numer, s.przeglady", "sprzęt"),
        ("m in materialy → m.lp, m.nazwa, m.producent, m.rodzaj, m.karta_charakterystyki", "materiały chemiczne"),
        ("z in zagrozenia → z.lp, z.nazwa, z.srodki", "zagrożenia i środki ochrony"),
    ]),
]
