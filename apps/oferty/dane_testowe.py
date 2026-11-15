"""Fikcyjny cennik i oferty – używane przez komendę `dane_testowe`. Ceny są wymyślone."""

import math
import random
from datetime import timedelta
from decimal import Decimal

from .models import Jednostka, Kontakt, Oferta, PowodPrzegranej, PozycjaCennika, PozycjaOferty, RodzajPozycji, Status, Wariant

S, P, D = RodzajPozycji.SYSTEM, RodzajPozycji.PRZYGOTOWANIE, RodzajPozycji.DODATKOWA
M2, MB, SZT, RYCZ = Jednostka.M2, Jednostka.MB, Jednostka.SZT, Jednostka.RYCZALT

CENNIK = [
    # nazwa, rodzaj, jednostka, cena, koszt, opis
    ("Posadzka epoksydowa cienkowarstwowa 0,3 mm", S, M2, 38, 24, "Dwukrotne malowanie żywicą epoksydową, wykończenie półmat."),
    ("Posadzka epoksydowa samopoziomująca 2 mm", S, M2, 85, 58, "Grunt + warstwa samopoziomująca 2 mm + zamknięcie. Kolor RAL do wyboru."),
    ("Posadzka epoksydowa samopoziomująca 3 mm", S, M2, 105, 72, "Grunt + warstwa samopoziomująca 3 mm + zamknięcie. Kolor RAL do wyboru."),
    ("Posadzka epoksydowa antypoślizgowa z posypką", S, M2, 98, 66, "Warstwa zasadnicza z posypką kwarcową, zamknięcie – klasa antypoślizgowości R10–R11."),
    ("Posadzka poliuretanowa elastyczna 2 mm", S, M2, 110, 76, "System elastyczny, mostkujący rysy."),
    ("Posadzka poliuretanowo-cementowa 6 mm", S, M2, 135, 92, "Odporna na szok termiczny i chemię – przemysł spożywczy."),
    ("Posadzka poliuretanowo-cementowa 9 mm", S, M2, 165, 115, "Odporna na szok termiczny do +120°C – przemysł spożywczy."),
    ("System parkingowy OS 8", S, M2, 125, 85, "System poliuretanowy z posypką, odporny na sole odladzające."),
    ("Posadzka metakrylanowa (MMA) 4 mm", S, M2, 210, 150, "Szybkie utwardzanie – możliwa eksploatacja po 2 godzinach."),
    ("Posadzka antyelektrostatyczna (ESD)", S, M2, 180, 125, "Z siatką uziemiającą, rezystancja wg PN-EN 61340."),
    ("Szlifowanie podłoża betonowego", P, M2, 12, 6, ""),
    ("Śrutowanie podłoża", P, M2, 14, 7, ""),
    ("Frezowanie podłoża", P, M2, 22, 12, ""),
    ("Gruntowanie żywicą epoksydową", P, M2, 16, 9, ""),
    ("Naprawa ubytków zaprawą żywiczną", P, M2, 90, 50, ""),
    ("Naprawa rys – iniekcja żywiczna", P, MB, 35, 18, ""),
    ("Cokolik żywiczny h=10 cm", D, MB, 48, 26, ""),
    ("Wyoblenie (faseta) przy ścianie", D, MB, 55, 30, ""),
    ("Dylatacje – nacięcie i wypełnienie masą PU", D, MB, 28, 14, ""),
    ("Transport, zaplecze i zagospodarowanie placu", D, RYCZ, 2500, 1500, ""),
    ("Pomiar wilgotności podłoża metodą CM", D, SZT, 150, 60, ""),
    ("Badanie przyczepności pull-off", D, SZT, 250, 100, ""),
]

KLIENCI_DODATKOWI = [
    ("Centrum Logistyczne Wschód-Test Sp. z o.o.", "Karolina Próbna", "500 100 207"),
    ("Browar Rzemieślniczy Chmielowo (fikcyjny)", "Adam Testowski", "500 100 208"),
    ("Przedszkole Niezapominajka w Testowie", "Maria Demo", "500 100 209"),
    ("Fabryka Mebli Dębowy Las (fikcyjna)", "Zbigniew Fikcyjny", "500 100 210"),
]

OBIEKTY = [
    "Hala magazynowa", "Hala produkcyjna", "Garaż podziemny", "Magazyn wysokiego składowania", "Warsztat",
    "Chłodnia", "Kuchnia zbiorcza", "Pomieszczenia techniczne", "Laboratorium", "Rampa rozładunkowa", "Showroom",
    "Serwerownia", "Myjnia", "Browarnia", "Hala sportowa – zaplecze",
]
MIASTA = ["Poznań", "Wrocław", "Kalisz", "Łódź", "Leszno", "Konin", "Gniezno", "Piła", "Ostrów Wlkp.", "Testowo"]


def wczytaj_cennik():
    pozycje = {}
    for i, (nazwa, rodzaj, jedn, cena, koszt, opis) in enumerate(CENNIK, 1):
        pozycje[nazwa], _ = PozycjaCennika.objects.get_or_create(
            nazwa=nazwa,
            defaults=dict(rodzaj=rodzaj, jednostka=jedn, cena_netto=Decimal(cena), koszt=Decimal(koszt), opis=opis, kolejnosc=i * 10),
        )
    return pozycje


def _dodaj_pozycje(wariant, cennik, system, m2, rnd):
    def poz(nazwa, ilosc, korekta=1.0):
        c = cennik[nazwa]
        PozycjaOferty.objects.create(
            wariant=wariant, pozycja_cennika=c, nazwa=c.nazwa, opis=c.opis, jednostka=c.jednostka,
            ilosc=Decimal(ilosc), cena_netto=(c.cena_netto * Decimal(str(korekta))).quantize(Decimal("0.01")),
            koszt_jednostkowy=c.koszt, kolejnosc=wariant.pozycje.count() + 1,
        )

    korekta = rnd.choice([0.95, 1.0, 1.0, 1.05, 1.1])
    poz(rnd.choice(["Szlifowanie podłoża betonowego", "Śrutowanie podłoża"]), m2)
    if "cienkowarstwowa" not in system:
        poz("Gruntowanie żywicą epoksydową", m2)
    poz(system, m2, korekta)
    obwod = int(4 * math.sqrt(m2) * 0.6)
    poz("Cokolik żywiczny h=10 cm", obwod)
    if m2 > 1500:
        poz("Dylatacje – nacięcie i wypełnienie masą PU", int(m2 / 10))
    if rnd.random() < 0.3:
        poz("Naprawa rys – iniekcja żywiczna", rnd.randint(20, 120))
    poz("Transport, zaplecze i zagospodarowanie placu", 1)
    if rnd.random() < 0.4:
        poz("Pomiar wilgotności podłoża metodą CM", rnd.randint(3, 10))


def wczytaj_oferty(klienci, handlowcy, dzis):
    from apps.budowy.models import Klient

    rnd = random.Random(2026)
    cennik = wczytaj_cennik()
    for i, (nazwa, osoba, tel) in enumerate(KLIENCI_DODATKOWI, len(klienci) + 1):
        klienci.append(Klient.objects.create(
            nazwa=nazwa, nip=f"000-000-00-{i:02d}", adres=f"ul. Przykładowa {i * 7}, 00-0{i:02d} Testowo",
            osoba_kontaktowa=osoba, telefon=tel, email=f"kontakt{i}@example.com",
        ))
    systemy = [n for n, r, *_ in CENNIK if r == S]
    poczatek_roku = dzis.replace(month=1, day=1)
    dni_w_roku = (dzis - poczatek_roku).days
    daty = sorted(poczatek_roku + timedelta(days=rnd.randint(0, dni_w_roku)) for _ in range(40))
    powody = [PowodPrzegranej.CENA] * 5 + [PowodPrzegranej.KONKURENCJA] * 2 + [
        PowodPrzegranej.TERMIN, PowodPrzegranej.REZYGNACJA, PowodPrzegranej.TECHNOLOGIA, PowodPrzegranej.BRAK_ODPOWIEDZI]
    utworzone = []
    for nr, data in enumerate(daty):
        wiek = (dzis - data).days
        system = rnd.choice(systemy)
        m2 = rnd.choice([150, 320, 480, 750, 1200, 1800, 2600, 3500, 4800])
        o = Oferta.objects.create(
            klient=rnd.choice(klienci), nazwa=f"{rnd.choice(OBIEKTY)} – {system.split(' ')[1]}",
            adres_budowy=f"ul. Testowa {rnd.randint(1, 99)}", miasto=rnd.choice(MIASTA), powierzchnia_m2=Decimal(m2),
            handlowiec=rnd.choice(handlowcy) if handlowcy else None, data_wystawienia=data,
            rabat_procent=Decimal(rnd.choice([0, 0, 0, 3, 5])), termin_realizacji=rnd.choice(["do uzgodnienia", "maj–czerwiec", "2 tygodnie od zlecenia"]),
        )
        w = Wariant.objects.create(oferta=o, nazwa="Wariant A")
        _dodaj_pozycje(w, cennik, system, m2, rnd)
        if rnd.random() < 0.25:
            w2 = Wariant.objects.create(oferta=o, nazwa="Wariant B", kolejnosc=2)
            _dodaj_pozycje(w2, cennik, rnd.choice(systemy), m2, rnd)

        # Status zależny od „wieku” oferty.
        if wiek <= 2 or nr % 13 == 0:
            o.status = Status.ROBOCZA
        else:
            o.status = Status.WYSLANA
            o.data_wyslania = data + timedelta(days=rnd.randint(0, 2))
            if wiek > 40 or (wiek > 14 and rnd.random() < 0.5):
                wygrana = rnd.random() < 0.42
                o.status = Status.WYGRANA if wygrana else Status.PRZEGRANA
                o.data_rozstrzygniecia = min(dzis, o.data_wyslania + timedelta(days=rnd.randint(7, 45)))
                if wygrana:
                    w.wybrany = True
                    w.save()
                else:
                    o.powod_przegranej = rnd.choice(powody)
                    if o.powod_przegranej == PowodPrzegranej.CENA:
                        o.powod_opis = f"konkurencja tańsza o ok. {rnd.choice([5, 8, 10, 15])}%"
            else:
                if rnd.random() < 0.5:
                    o.status = Status.NEGOCJACJE
                # Część przypomnień jest już po terminie – pojawią się na „Co dziś?”.
                o.nastepny_kontakt = dzis + timedelta(days=rnd.choice([-6, -2, -1, 0, 2, 5]))
            Kontakt.objects.create(
                oferta=o, data=o.data_wyslania + timedelta(days=7), forma=rnd.choice(["telefon", "email"]),
                notatka=rnd.choice([
                    "Klient analizuje oferty, decyzja w przyszłym tygodniu.",
                    "Prośba o wariant z tańszym systemem.",
                    "Inwestor czeka na finansowanie.",
                    "Klient porównuje z dwiema innymi ofertami.",
                ]),
                kto=o.handlowiec,
            )
        o.save()
        utworzone.append(o)

    # Przykład wersjonowania: oferta po negocjacjach w wersji 2.
    from .operacje import nowa_wersja

    otwarte = [o for o in utworzone if o.status in (Status.WYSLANA, Status.NEGOCJACJE)]
    if otwarte:
        v1 = otwarte[0]
        v2 = nowa_wersja(v1)
        v2.rabat_procent = Decimal("7")
        v2.status = Status.NEGOCJACJE
        v2.data_wyslania = dzis - timedelta(days=3)
        v2.nastepny_kontakt = dzis + timedelta(days=4)
        v2.save()
    return utworzone
