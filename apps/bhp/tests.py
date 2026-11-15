from datetime import date, timedelta

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.konta import uprawnienia as u
from apps.konta.models import Uzytkownik

from .alerty import alerty_bhp
from .models import DokumentPracownika, Pracownik, TypDokumentu
from .terminy import status_terminu

DZIS = date(2026, 6, 1)


class StatusTerminuTest(TestCase):
    def test_progi(self):
        self.assertEqual(status_terminu(None, DZIS).kod, "bezterminowy")
        self.assertEqual(status_terminu(DZIS - timedelta(days=1), DZIS).kod, "wygasl")
        self.assertEqual(status_terminu(DZIS, DZIS).kod, "pilne")
        self.assertEqual(status_terminu(DZIS + timedelta(days=7), DZIS).kod, "pilne")
        self.assertEqual(status_terminu(DZIS + timedelta(days=8), DZIS).kod, "wkrotce")
        self.assertEqual(status_terminu(DZIS + timedelta(days=30), DZIS).kod, "wkrotce")
        self.assertEqual(status_terminu(DZIS + timedelta(days=31), DZIS).kod, "wazny")


class AlertyTest(TestCase):
    def setUp(self):
        self.badania = TypDokumentu.objects.get(nazwa__startswith="Badania lekarskie")
        self.p = Pracownik.objects.create(imie="Jan", nazwisko="Testowy")
        DokumentPracownika.objects.create(
            pracownik=self.p, typ=TypDokumentu.objects.get(nazwa="Szkolenie BHP wstępne"), data_waznosci=None
        )

    def kody(self):
        return {(a.typ.nazwa[:8], a.status.kod) for a in alerty_bhp(DZIS)}

    def test_brak_wymaganego_dokumentu(self):
        self.assertIn(("Badania ", "brak"), self.kody())

    def test_nowy_dokument_zastepuje_wygasly(self):
        DokumentPracownika.objects.create(pracownik=self.p, typ=self.badania, data_waznosci=DZIS - timedelta(days=10))
        self.assertIn(("Badania ", "wygasl"), self.kody())
        DokumentPracownika.objects.create(pracownik=self.p, typ=self.badania, data_waznosci=DZIS + timedelta(days=700))
        self.assertEqual(self.kody(), set())

    def test_nieaktywny_pracownik_bez_alertow(self):
        self.p.aktywny = False
        self.p.save()
        self.assertEqual(self.kody(), set())


class PlikiTest(TestCase):
    """Skany dokumentów (np. badań lekarskich) nie mogą być dostępne dla osób spoza BHP."""

    def setUp(self):
        import tempfile

        self.tmp = tempfile.mkdtemp()
        self.ustawienia = override_settings(MEDIA_ROOT=self.tmp)
        self.ustawienia.enable()
        p = Pracownik.objects.create(imie="Jan", nazwisko="Testowy")
        self.dok = DokumentPracownika.objects.create(
            pracownik=p, typ=TypDokumentu.objects.first(), plik=SimpleUploadedFile("skan.pdf", b"%PDF-1.4 test")
        )

    def tearDown(self):
        self.ustawienia.disable()

    def zaloguj(self, rola):
        user = Uzytkownik.objects.create_user(f"u_{rola}", password="x-Haslo-12345")
        user.groups.add(Group.objects.get(name=rola))
        self.client.force_login(user)

    def test_bhp_widzi_plik(self):
        self.zaloguj(u.BHP)
        self.assertEqual(self.client.get(self.dok.plik.url).status_code, 200)

    def test_handlowiec_nie_widzi_pliku(self):
        self.zaloguj(u.HANDLOWIEC)
        self.assertEqual(self.client.get(self.dok.plik.url).status_code, 403)

    def test_niezalogowany_nie_widzi_pliku(self):
        self.assertEqual(self.client.get(self.dok.plik.url).status_code, 302)

    def test_nazwa_pliku_jest_losowa(self):
        self.assertNotIn("skan", self.dok.plik.name)
