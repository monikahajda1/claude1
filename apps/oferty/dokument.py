"""Dane przekazywane do szablonu Word oferty.

Wszystkie kwoty są już sformatowane po polsku (np. „12 345,67”), więc w szablonie
wystarczy wpisać {{ netto }} – bez żadnych dodatkowych ustawień.
"""

from decimal import Decimal

from django.utils import timezone
from num2words import num2words

from .models import Jednostka, zaokr

ETYKIETY_JEDNOSTEK = dict(Jednostka.choices)


def kwota(x):
    return f"{Decimal(x):,.2f}".replace(",", " ").replace(".", ",")


def liczba(x):
    """Ilość bez zbędnych zer: 120 / 12,5 / 0,75."""
    tekst = f"{Decimal(x):,.2f}".replace(",", " ").replace(".", ",")
    return tekst.rstrip("0").rstrip(",") if "," in tekst else tekst


def slownie(x):
    return num2words(Decimal(x), lang="pl", to="currency", currency="PLN")


def data(d):
    return d.strftime("%d.%m.%Y") if d else ""


def kontekst_wariantu(nazwa, opis, pozycje, rabat_procent, vat_procent):
    """pozycje: lista słowników z kluczami nazwa, opis, jednostka, ilosc, cena (Decimal)."""
    wiersze = []
    suma = Decimal("0")
    for lp, p in enumerate(pozycje, 1):
        wartosc = zaokr(p["ilosc"] * p["cena"])
        suma += wartosc
        wiersze.append({
            "lp": lp,
            "nazwa": p["nazwa"],
            "opis": p["opis"],
            "jednostka": ETYKIETY_JEDNOSTEK.get(p["jednostka"], p["jednostka"]),
            "ilosc": liczba(p["ilosc"]),
            "cena": kwota(p["cena"]),
            "wartosc": kwota(wartosc),
        })
    rabat = zaokr(suma * Decimal(rabat_procent) / 100)
    netto = suma - rabat
    vat = zaokr(netto * Decimal(vat_procent) / 100)
    brutto = netto + vat
    return {
        "nazwa": nazwa,
        "opis": opis,
        "pozycje": wiersze,
        "suma_przed_rabatem": kwota(suma),
        "rabat": kwota(rabat),
        "netto": kwota(netto),
        "vat": kwota(vat),
        "brutto": kwota(brutto),
        "netto_slownie": slownie(netto),
        "brutto_slownie": slownie(brutto),
    }


def zbuduj(naglowek, warianty, rabat_procent, vat_procent):
    """naglowek: słownik pól ogólnych; warianty: lista (nazwa, opis, pozycje)."""
    kw = [kontekst_wariantu(n, o, p, rabat_procent, vat_procent) for n, o, p in warianty]
    pierwszy = kw[0] if kw else kontekst_wariantu("", "", [], rabat_procent, vat_procent)
    rabat = Decimal(rabat_procent)
    return {
        **naglowek,
        "rabat_procent": liczba(rabat),
        "jest_rabat": rabat > 0,
        "vat_procent": vat_procent,
        "warianty": kw,
        "wiele_wariantow": len(kw) > 1,
        # Skróty dla ofert z jednym wariantem:
        "pozycje": pierwszy["pozycje"],
        "suma_przed_rabatem": pierwszy["suma_przed_rabatem"],
        "rabat": pierwszy["rabat"],
        "netto": pierwszy["netto"],
        "vat": pierwszy["vat"],
        "brutto": pierwszy["brutto"],
        "netto_slownie": pierwszy["netto_slownie"],
        "brutto_slownie": pierwszy["brutto_slownie"],
    }


def kontekst_oferty(oferta):
    k = oferta.klient
    h = oferta.handlowiec
    naglowek = {
        "numer_oferty": oferta.pelny_numer,
        "data": data(oferta.data_wystawienia),
        "wazna_do": data(oferta.wazna_do),
        "waznosc_dni": oferta.waznosc_dni,
        "klient": k.nazwa,
        "klient_adres": k.adres,
        "klient_nip": k.nip,
        "osoba_kontaktowa": k.osoba_kontaktowa,
        "klient_telefon": k.telefon,
        "klient_email": k.email,
        "inwestycja": oferta.nazwa,
        "adres_budowy": ", ".join(x for x in [oferta.adres_budowy, oferta.miasto] if x),
        "powierzchnia": liczba(oferta.powierzchnia_m2) if oferta.powierzchnia_m2 else "",
        "handlowiec": (h.get_full_name() or h.username) if h else "",
        "handlowiec_telefon": getattr(h, "telefon", "") if h else "",
        "handlowiec_email": h.email if h else "",
        "termin_realizacji": oferta.termin_realizacji,
        "warunki_platnosci": oferta.warunki_platnosci,
        "uwagi": oferta.uwagi,
    }
    warianty = [
        (
            w.nazwa,
            w.opis,
            [
                {"nazwa": p.nazwa, "opis": p.opis, "jednostka": p.jednostka, "ilosc": p.ilosc, "cena": p.cena_netto}
                for p in w.pozycje.all()
            ],
        )
        for w in oferta.warianty.prefetch_related("pozycje")
    ]
    return zbuduj(naglowek, warianty, oferta.rabat_procent, oferta.vat_procent)


def kontekst_przykladowy():
    """Wymyślone dane – do sprawdzania szablonu."""
    D = Decimal
    naglowek = {
        "numer_oferty": "OF/2026/0001/v2",
        "data": data(timezone.localdate()),
        "wazna_do": "31.12.2026",
        "waznosc_dni": 30,
        "klient": "Przykładowy Klient Sp. z o.o.",
        "klient_adres": "ul. Przykładowa 1, 00-001 Testowo",
        "klient_nip": "000-000-00-00",
        "osoba_kontaktowa": "Jan Przykładowy",
        "klient_telefon": "500 000 000",
        "klient_email": "jan@example.com",
        "inwestycja": "Hala magazynowa – posadzka epoksydowa",
        "adres_budowy": "ul. Testowa 10, Testowo",
        "powierzchnia": "1 200",
        "handlowiec": "Anna Handlowa",
        "handlowiec_telefon": "600 000 000",
        "handlowiec_email": "anna@example.com",
        "termin_realizacji": "do uzgodnienia",
        "warunki_platnosci": "przelew 30 dni",
        "uwagi": "Oferta nie obejmuje zapewnienia mediów.",
    }
    pozycje_a = [
        {"nazwa": "Szlifowanie podłoża", "opis": "", "jednostka": "m2", "ilosc": D("1200"), "cena": D("9.50")},
        {"nazwa": "Gruntowanie", "opis": "żywica epoksydowa", "jednostka": "m2", "ilosc": D("1200"), "cena": D("14.00")},
        {"nazwa": "Posadzka epoksydowa 2 mm", "opis": "samopoziomująca", "jednostka": "m2", "ilosc": D("1200"), "cena": D("78.00")},
        {"nazwa": "Cokolik h=10 cm", "opis": "", "jednostka": "mb", "ilosc": D("180"), "cena": D("45.00")},
    ]
    pozycje_b = pozycje_a[:2] + [
        {"nazwa": "Posadzka poliuretanowa 2 mm", "opis": "elastyczna", "jednostka": "m2", "ilosc": D("1200"), "cena": D("92.00")},
    ]
    return zbuduj(naglowek, [("Wariant A – epoksyd", "", pozycje_a), ("Wariant B – poliuretan", "", pozycje_b)], D("5"), 23)


# Opis pól – wyświetlany na stronie „Pola szablonu oferty”.
POLA = [
    ("Nagłówek", [
        ("numer_oferty", "numer oferty, np. OF/2026/0001 (z wersją: OF/2026/0001/v2)"),
        ("data", "data wystawienia"),
        ("wazna_do", "data ważności oferty"),
        ("waznosc_dni", "ważność w dniach"),
        ("handlowiec", "imię i nazwisko handlowca"),
        ("handlowiec_telefon", "telefon handlowca"),
        ("handlowiec_email", "e-mail handlowca"),
    ]),
    ("Klient i budowa", [
        ("klient", "nazwa klienta"),
        ("klient_adres", "adres klienta"),
        ("klient_nip", "NIP klienta"),
        ("osoba_kontaktowa", "osoba kontaktowa"),
        ("klient_telefon", "telefon klienta"),
        ("klient_email", "e-mail klienta"),
        ("inwestycja", "nazwa inwestycji / obiektu"),
        ("adres_budowy", "adres budowy (z miastem)"),
        ("powierzchnia", "powierzchnia w m²"),
    ]),
    ("Warunki", [
        ("termin_realizacji", "termin realizacji"),
        ("warunki_platnosci", "warunki płatności"),
        ("uwagi", "uwagi i wyłączenia"),
        ("rabat_procent", "rabat w %"),
        ("jest_rabat", "prawda/fałsz – do warunku {% if jest_rabat %}…{% endif %}"),
        ("vat_procent", "stawka VAT"),
    ]),
    ("Kwoty (oferta z jednym wariantem)", [
        ("suma_przed_rabatem", "suma netto przed rabatem"),
        ("rabat", "kwota rabatu"),
        ("netto", "razem netto"),
        ("vat", "kwota VAT"),
        ("brutto", "razem brutto"),
        ("netto_slownie", "netto słownie"),
        ("brutto_slownie", "brutto słownie"),
    ]),
    ("Tabela pozycji – wiersz tabeli w pętli", [
        ("{%tr for p in pozycje %}", "początek pętli – w osobnym wierszu tabeli"),
        ("p.lp / p.nazwa / p.opis", "numer, nazwa, opis pozycji"),
        ("p.jednostka / p.ilosc / p.cena / p.wartosc", "jednostka, ilość, cena netto, wartość netto"),
        ("{%tr endfor %}", "koniec pętli – w osobnym wierszu tabeli"),
    ]),
    ("Wiele wariantów", [
        ("{%p for w in warianty %} … {%p endfor %}", "powtarza fragment dla każdego wariantu (każde w osobnym akapicie)"),
        ("w.nazwa, w.opis, w.pozycje, w.netto, w.vat, w.brutto, w.brutto_slownie, w.rabat", "dane wariantu"),
        ("wiele_wariantow", "prawda, gdy oferta ma więcej niż jeden wariant"),
    ]),
]
