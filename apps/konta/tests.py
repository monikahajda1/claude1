from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.budowy.models import Budowa, Klient

from . import uprawnienia as u
from .models import Uzytkownik


class UprawnieniaTest(TestCase):
    def setUp(self):
        self.klient = Klient.objects.create(nazwa="Klient Testowy")
        self.k1 = self.konto("kier1", u.KIEROWNIK)
        self.k2 = self.konto("kier2", u.KIEROWNIK)
        self.b1 = Budowa.objects.create(nazwa="Budowa 1", klient=self.klient, adres="ul. A 1", kierownik=self.k1)
        self.b2 = Budowa.objects.create(nazwa="Budowa 2", klient=self.klient, adres="ul. B 2", kierownik=self.k2)

    def konto(self, login, *role, **extra):
        user = Uzytkownik.objects.create_user(login, password="x-Haslo-12345", **extra)
        user.groups.set(Group.objects.filter(name__in=role))
        return user

    def test_role_istnieja(self):
        self.assertEqual(set(Group.objects.values_list("name", flat=True)), set(u.ROLE))

    def test_numeracja_budow(self):
        self.assertTrue(self.b1.numer.endswith("/001"))
        self.assertTrue(self.b2.numer.endswith("/002"))

    def test_kierownik_widzi_tylko_swoje_budowy(self):
        self.client.force_login(self.k1)
        self.assertEqual(self.client.get(reverse("budowy:szczegoly", args=[self.b1.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("budowy:szczegoly", args=[self.b2.pk])).status_code, 404)
        lista = self.client.get(reverse("budowy:lista"))
        self.assertContains(lista, "Budowa 1")
        self.assertNotContains(lista, "Budowa 2")

    def test_kierownik_nie_widzi_pracownikow(self):
        self.client.force_login(self.k1)
        self.assertEqual(self.client.get(reverse("bhp:pracownicy")).status_code, 403)

    def test_handlowiec_bez_danych_pracownikow(self):
        self.client.force_login(self.konto("hand", u.HANDLOWIEC))
        self.assertEqual(self.client.get(reverse("bhp:pracownicy")).status_code, 403)
        self.assertEqual(self.client.get(reverse("budowy:lista")).status_code, 200)

    def test_bhp_nie_widzi_klientow(self):
        self.client.force_login(self.konto("bhp", u.BHP))
        self.assertEqual(self.client.get(reverse("budowy:klienci")).status_code, 403)
        self.assertEqual(self.client.get(reverse("bhp:pracownicy")).status_code, 200)

    def test_tylko_podglad_nie_moze_zapisac(self):
        self.client.force_login(self.konto("podglad", u.ADMINISTRATOR, tylko_podglad=True))
        self.assertEqual(self.client.get(reverse("budowy:szczegoly", args=[self.b1.pk])).status_code, 200)
        r = self.client.post(reverse("budowy:edytuj", args=[self.b1.pk]), {"nazwa": "Zmiana"})
        self.assertEqual(r.status_code, 403)
        r = self.client.post(reverse("budowy:klient_edytuj", args=[self.klient.pk]), {"nazwa": "Zmiana"})
        self.assertEqual(r.status_code, 403)

    def test_niezalogowany_przekierowany_do_logowania(self):
        r = self.client.get(reverse("pulpit:co_dzis"))
        self.assertRedirects(r, reverse("konta:logowanie") + "?next=/")

    def test_dziennik_zapisuje_autora_zmiany(self):
        admin = self.konto("adm", u.ADMINISTRATOR)
        self.client.force_login(admin)
        r = self.client.post(
            reverse("budowy:klient_edytuj", args=[self.klient.pk]), {"nazwa": "Nowa nazwa klienta"}
        )
        self.assertEqual(r.status_code, 302)
        wpis = self.klient.history.first()
        self.assertEqual(wpis.history_user, admin)
        self.assertEqual(wpis.nazwa, "Nowa nazwa klienta")
        self.assertContains(self.client.get(reverse("core:dziennik")), "Nowa nazwa klienta")
