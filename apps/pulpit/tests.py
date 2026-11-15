import io

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.konta.models import Uzytkownik


class CoDzisTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("dane_testowe", "--konta", stdout=io.StringIO())

    def test_kazda_rola_widzi_ekran(self):
        for login in ["admin_demo", "handlowiec_demo", "bhp_demo", "kierownik_demo", "podglad_demo"]:
            self.client.force_login(Uzytkownik.objects.get(username=login))
            r = self.client.get(reverse("pulpit:co_dzis"))
            self.assertEqual(r.status_code, 200, login)

    def test_handlowiec_nie_widzi_alertow_bhp(self):
        self.client.force_login(Uzytkownik.objects.get(username="handlowiec_demo"))
        r = self.client.get(reverse("pulpit:co_dzis"))
        self.assertNotIn("alerty_pilne", r.context)
        self.assertNotContains(r, "Zieliński")

    def test_bhp_widzi_alerty(self):
        self.client.force_login(Uzytkownik.objects.get(username="bhp_demo"))
        r = self.client.get(reverse("pulpit:co_dzis"))
        self.assertTrue(r.context["alerty_pilne"])
        self.assertContains(r, "brak dokumentu")

    def test_pwa(self):
        self.assertEqual(self.client.get("/manifest.webmanifest").status_code, 200)
        self.assertEqual(self.client.get("/sw.js").status_code, 200)
