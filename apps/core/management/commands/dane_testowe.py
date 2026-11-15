"""
Wczytuje FIKCYJNE dane testowe: klientów, budowy, pracowników, sprzęt i dokumenty.
Wszystkie nazwy, osoby i adresy są wymyślone.

Użycie:
    python manage.py dane_testowe            # dane przykładowe
    python manage.py dane_testowe --konta    # + konta demonstracyjne dla każdej roli
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.bhp.models import DokumentPracownika, DokumentSprzetu, Pracownik, Sprzet, TypDokumentu
from apps.budowy.models import Budowa, Etap, Klient
from apps.konta import uprawnienia as u
from apps.konta.models import Uzytkownik

HASLO_DEMO = "Demo-haslo-2026"

KLIENCI = [
    ("Magazyny Zielony Park Sp. z o.o.", "Anna Testowa", "500 100 201"),
    ("Kwadrat-Bud Generalny Wykonawca S.A. (fikcyjny)", "Piotr Przykładowy", "500 100 202"),
    ("Zakłady Mleczarskie Łąka Sp. z o.o.", "Ewa Fikcyjna", "500 100 203"),
    ("Szpital Powiatowy w Testowie", "Marek Demo", "500 100 204"),
    ("Galeria Handlowa Słoneczna", "Joanna Wzorcowa", "500 100 205"),
    ("Auto-Serwis Kowalczyk-Test", "Tomasz Próbny", "500 100 206"),
]

BUDOWY = [
    # nazwa, klient_idx, miasto, etap, system, m2, start_dni, czas_dni
    ("Hala magazynowa A – posadzka epoksydowa", 0, "Poznań", Etap.REALIZACJA, "Epoksydowa samopoziomująca 3 mm", 4200, -20, 40),
    ("Hala magazynowa B – posadzka epoksydowa", 0, "Poznań", Etap.PRZYGOTOWANIE, "Epoksydowa samopoziomująca 3 mm", 3800, 6, 35),
    ("Biurowiec Kwadrat – garaż podziemny", 1, "Wrocław", Etap.UMOWA, "Poliuretanowa OS 8, system parkingowy", 2600, 12, 30),
    ("Mleczarnia – hala produkcyjna", 2, "Kalisz", Etap.REALIZACJA, "Poliuretanowo-cementowa 9 mm", 1500, -35, 30),
    ("Szpital – blok operacyjny", 3, "Testowo", Etap.ROZLICZENIE, "Epoksydowa antyelektrostatyczna", 640, -60, 45),
    ("Magazyn chłodniczy – rampa", 0, "Poznań", Etap.DOKUMENTACJA, "Metakrylanowa (MMA)", 450, -90, 14),
    ("Archiwum miejskie – piwnice", 1, "Wrocław", Etap.ZAKONCZONA, "Epoksydowa cienkowarstwowa", 780, -200, 20),
    ("Pralnia przemysłowa", 2, "Kalisz", Etap.WSTRZYMANA, "Poliuretanowo-cementowa 6 mm", 520, -10, 20),
]

PRACOWNICY = [
    ("Jan", "Nowakowski", "Brygadzista", ""),
    ("Adam", "Wiśniewski", "Posadzkarz", ""),
    ("Krzysztof", "Lewandowski", "Posadzkarz", ""),
    ("Paweł", "Zieliński", "Posadzkarz", ""),
    ("Michał", "Szymański", "Pomocnik", ""),
    ("Łukasz", "Dąbrowski", "Operator szlifierki", ""),
    ("Grzegorz", "Kamiński", "Posadzkarz", ""),
    ("Dariusz", "Wójcik", "Kierowca / magazynier", ""),
    ("Sebastian", "Mazur", "Posadzkarz", "Usługi Posadzkowe Test-Mazur"),
    ("Rafał", "Krawczyk", "Pomocnik", "Usługi Posadzkowe Test-Mazur"),
    ("Robert", "Piotrowski", "Posadzkarz (były)", ""),
]

SPRZET = [
    ("Szlifierka do betonu", "SZL-01", "Szlif-Demo 650"),
    ("Szlifierka do betonu", "SZL-02", "Szlif-Demo 420"),
    ("Śrutownica", "SRU-01", "Śrut-Demo 200"),
    ("Odkurzacz przemysłowy", "ODK-01", "Demo T-8"),
    ("Podest ruchomy nożycowy", "POD-01", "Test-Lift 8 m"),
    ("Wilgotnościomierz CM", "MIE-01", "Przyrząd CM-Demo"),
    ("Miernik pull-off", "MIE-02", "Pull-Test 50 kN"),
    ("Mieszarka", "MIE-03", "Mix-Demo 1600"),
]


class Command(BaseCommand):
    help = "Wczytuje fikcyjne dane testowe (budowy, klienci, pracownicy, sprzęt, dokumenty)."

    def add_arguments(self, parser):
        parser.add_argument("--konta", action="store_true", help="Utwórz też konta demonstracyjne dla każdej roli.")
        parser.add_argument("--wymus", action="store_true", help="Wczytaj, nawet jeśli w bazie są już budowy.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if Budowa.objects.exists() and not opts["wymus"]:
            raise CommandError("W bazie są już budowy – nie dokładam danych testowych. Użyj --wymus, jeśli na pewno chcesz.")
        random.seed(2026)
        dzis = timezone.localdate()

        kierownicy = self._konta() if opts["konta"] else []

        klienci = []
        for i, (nazwa, osoba, tel) in enumerate(KLIENCI, 1):
            klienci.append(
                Klient.objects.create(
                    nazwa=nazwa, nip=f"000-000-00-{i:02d}", adres=f"ul. Przykładowa {i * 7}, 00-00{i} Testowo",
                    osoba_kontaktowa=osoba, telefon=tel, email=f"kontakt{i}@example.com",
                )
            )

        pracownicy = [
            Pracownik.objects.create(imie=i, nazwisko=n, stanowisko=s, firma=f, telefon=f"600 000 {k:03d}", aktywny="były" not in s)
            for k, (i, n, s, f) in enumerate(PRACOWNICY, 1)
        ]
        sprzet = [Sprzet.objects.create(nazwa=n, numer_ewidencyjny=nr, producent_model=m) for n, nr, m in SPRZET]

        self._dokumenty(pracownicy, sprzet, dzis)

        for k, (nazwa, ki, miasto, etap, system, m2, start, czas) in enumerate(BUDOWY):
            b = Budowa.objects.create(
                nazwa=nazwa, klient=klienci[ki], adres=f"ul. Testowa {10 + k}", miasto=miasto, etap=etap,
                system_posadzki=system, powierzchnia_m2=Decimal(m2), wartosc_netto=Decimal(m2) * Decimal(random.choice([95, 120, 145, 180])),
                data_rozpoczecia=dzis + timedelta(days=start), data_zakonczenia=dzis + timedelta(days=start + czas),
                kierownik=kierownicy[k % len(kierownicy)] if kierownicy and k != 2 else None,
            )
            if etap in (Etap.REALIZACJA, Etap.PRZYGOTOWANIE, Etap.ROZLICZENIE):
                b.pracownicy.set(random.sample(pracownicy[:10], 4))
                b.sprzet.set(random.sample(sprzet, 3))
        from apps.oferty.dane_testowe import wczytaj_oferty

        handlowcy = list(Uzytkownik.objects.filter(username__in=["handlowiec_demo", "admin_demo"])) if opts["konta"] else []
        oferty = wczytaj_oferty(klienci, handlowcy, dzis)
        self.stdout.write(self.style.SUCCESS(f"Oferty: {len(oferty)} (+ cennik)."))

        from apps.umowy.dane_testowe import budowy_z_ofert, umowy_dla_budow

        umowy_dla_budow(dzis)
        budowy_z_ofert(kierownicy, dzis)
        self.stdout.write(self.style.SUCCESS("Umowy: dodane do budów; 3 wygrane oferty zamienione w budowy."))
        self.stdout.write(self.style.SUCCESS(
            f"Gotowe: {len(klienci)} klientów, {Budowa.objects.count()} budów, {len(pracownicy)} pracowników, {len(sprzet)} sztuk sprzętu."
        ))
        if opts["konta"]:
            self.stdout.write(self.style.WARNING(
                f"Konta demo: admin_demo, handlowiec_demo, bhp_demo, kierownik_demo, kierownik2_demo, podglad_demo – hasło: {HASLO_DEMO}\n"
                "Przed wpisaniem prawdziwych danych usuń bazę testową (instrukcja w README)."
            ))

    def _konta(self):
        def konto(login, imie, nazwisko, role, **extra):
            user, _ = Uzytkownik.objects.get_or_create(username=login, defaults={"first_name": imie, "last_name": nazwisko, **extra})
            user.set_password(HASLO_DEMO)
            user.save()
            user.groups.set(Group.objects.filter(name__in=role))
            return user

        konto("admin_demo", "Alicja", "Administratorka", [u.ADMINISTRATOR], is_staff=True, is_superuser=True)
        konto("handlowiec_demo", "Henryk", "Handlowy", [u.HANDLOWIEC])
        konto("bhp_demo", "Barbara", "Bezpieczna", [u.BHP])
        konto("podglad_demo", "Paulina", "Podglądowa", [u.ADMINISTRATOR], tylko_podglad=True)
        return [
            konto("kierownik_demo", "Karol", "Kierowniczy", [u.KIEROWNIK]),
            konto("kierownik2_demo", "Kamil", "Robotny", [u.KIEROWNIK]),
        ]

    def _dokumenty(self, pracownicy, sprzet, dzis):
        typy = {t.nazwa: t for t in TypDokumentu.objects.all()}

        def dok(model, pole, obiekt, typ, waznosc_dni, wydanie_dni=None):
            t = typy[typ]
            waz = dzis + timedelta(days=waznosc_dni) if waznosc_dni is not None else None
            wyd = dzis + timedelta(days=wydanie_dni) if wydanie_dni is not None else (
                (waz - timedelta(days=30 * (t.okres_miesiecy or 12))) if waz else dzis - timedelta(days=400)
            )
            model.objects.create(**{pole: obiekt}, typ=t, data_wydania=wyd, data_waznosci=waz, numer=f"T/{random.randint(100, 999)}")

        # Zestaw scenariuszy: większość ważna, kilka problemów do pokazania alertów.
        scenariusze_badan = [400, 15, 200, -5, 300, 5, 250, 500, 25, 180, -100]
        for p, badania in zip(pracownicy, scenariusze_badan):
            dok(DokumentPracownika, "pracownik", p, "Badania lekarskie (medycyna pracy)", badania)
            if p.nazwisko != "Zieliński":  # jemu „brakuje” szkolenia wstępnego
                dok(DokumentPracownika, "pracownik", p, "Szkolenie BHP wstępne", None)
            dok(DokumentPracownika, "pracownik", p, "Szkolenie BHP okresowe", random.choice([300, 600, 20]))
        # Przykład: stare badania wygasły, ale są nowe – NIE powinno być alertu.
        dok(DokumentPracownika, "pracownik", pracownicy[0], "Badania lekarskie (medycyna pracy)", -30, -760)
        dok(DokumentPracownika, "pracownik", pracownicy[0], "Badania do pracy na wysokości", 3)
        dok(DokumentPracownika, "pracownik", pracownicy[5], "Uprawnienia UDT – podesty ruchome", 1500)

        przeglady = [200, 28, 100, -12, 300, 150, 60, 2]
        for s, dni in zip(sprzet, przeglady):
            dok(DokumentSprzetu, "sprzet", s, "Przegląd techniczny", dni)
        dok(DokumentSprzetu, "sprzet", sprzet[4], "Przegląd UDT", 18)
        dok(DokumentSprzetu, "sprzet", sprzet[5], "Kalibracja / świadectwo wzorcowania", 90)
        dok(DokumentSprzetu, "sprzet", sprzet[6], "Kalibracja / świadectwo wzorcowania", -40)
