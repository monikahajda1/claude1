import tempfile
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.budowy.models import Budowa, Etap, Klient
from apps.konta import uprawnienia as u
from apps.konta.models import Uzytkownik
from apps.oferty import operacje as op_oferty
from apps.oferty.models import Oferta, PozycjaCennika, PozycjaOferty, Status, Wariant
from apps.pulpit.zadania import zadania_umow

from . import operacje
from .models import Aneks, FormaZabezpieczenia, Umowa


def konto(login, *role, **extra):
    user = Uzytkownik.objects.create_user(login, password="x-Haslo-12345", **extra)
    user.groups.set(Group.objects.filter(name__in=role))
    return user


class BazaUmow(TestCase):
    def setUp(self):
        self.handlowiec = konto("hand", u.HANDLOWIEC)
        self.kierownik = konto("kier", u.KIEROWNIK)
        self.klient = Klient.objects.create(nazwa="Klient Testowy")
        system = PozycjaCennika.objects.create(nazwa="Epoksyd 2 mm", cena_netto=Decimal("85"))
        self.oferta = Oferta.objects.create(klient=self.klient, nazwa="Hala", adres_budowy="ul. Testowa 1", miasto="Testowo",
                                            powierzchnia_m2=Decimal("1000"), rabat_procent=Decimal("10"))
        w = Wariant.objects.create(oferta=self.oferta)
        PozycjaOferty.objects.create(wariant=w, pozycja_cennika=system, nazwa="Epoksyd", ilosc=Decimal("1000"), cena_netto=Decimal("85"))
        PozycjaOferty.objects.create(wariant=w, nazwa="Cokolik", jednostka="mb", ilosc=Decimal("100"), cena_netto=Decimal("50"))
        op_oferty.rozstrzygnij(self.oferta, Status.WYGRANA, w)

    def utworz(self):
        budowa = Budowa(nazwa="Hala", adres="ul. Testowa 1", kierownik=self.kierownik)
        umowa = Umowa(wartosc_netto=Decimal("81000"), zabezpieczenie_forma=FormaZabezpieczenia.KAUCJA, zabezpieczenie_procent=Decimal("5"))
        return operacje.utworz_budowe_z_oferty(self.oferta, budowa, umowa)


class OperacjeTest(BazaUmow):
    def test_budowa_z_oferty(self):
        b = self.utworz()
        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.budowa, b)
        self.assertEqual(b.klient, self.klient)
        self.assertEqual(b.etap, Etap.UMOWA)
        ceny = list(b.zakres.values_list("nazwa", "cena_netto"))
        self.assertEqual(ceny, [("Epoksyd", Decimal("76.50")), ("Cokolik", Decimal("45.00"))])  # po rabacie 10%
        self.assertEqual(operacje.suma_zakresu(b), Decimal("81000.00"))
        self.assertEqual(b.wartosc_netto, Decimal("81000"))

    def test_materialy_z_oferty_trafiaja_na_budowe(self):
        from apps.materialy.models import Material

        m = Material.objects.create(nazwa="Grunt", producent="Fikcja")
        m.systemy.add(PozycjaCennika.objects.get(nazwa="Epoksyd 2 mm"))
        b = self.utworz()
        self.assertEqual([mb.material for mb in b.materialy.all()], [m])

    def test_podpowiedzi_z_oferty(self):
        d = operacje.dane_poczatkowe_z_oferty(self.oferta)
        self.assertEqual(d["umowa"]["wartosc_netto"], Decimal("81000.00"))
        self.assertEqual(d["budowa"]["system_posadzki"], "Epoksyd 2 mm")

    def test_aneks_zmienia_wartosc_i_termin(self):
        b = self.utworz()
        operacje.zapisz_aneks(Aneks(umowa=b.umowa, numer="1", data=date(2026, 5, 1), opis="x",
                                    zmiana_wartosci=Decimal("5000"), nowy_termin_zakonczenia=date(2026, 7, 31)))
        operacje.zapisz_aneks(Aneks(umowa=b.umowa, numer="2", data=date(2026, 6, 1), opis="y", zmiana_wartosci=Decimal("-1000")))
        b.refresh_from_db()
        self.assertEqual(b.wartosc_netto, Decimal("85000"))
        self.assertEqual(b.data_zakonczenia, date(2026, 7, 31))
        self.assertEqual(b.umowa.zabezpieczenie_kwota, Decimal("4250.00"))
        self.assertEqual(b.umowa.zwrot1_kwota + b.umowa.zwrot2_kwota, Decimal("4250.00"))

    def test_koniec_gwarancji(self):
        umowa = Umowa(wartosc_netto=1, data_odbioru_koncowego=date(2026, 1, 31), gwarancja_miesiecy=1)
        self.assertEqual(umowa.koniec_gwarancji, date(2026, 2, 28))

    def test_przypomnienia(self):
        b = self.utworz()
        b.etap = Etap.REALIZACJA
        b.save()
        umowa = b.umowa
        dzis = timezone.localdate()
        umowa.zwrot1_data = dzis - timedelta(days=2)
        umowa.data_odbioru_koncowego = dzis.replace(year=dzis.year - 1) + timedelta(days=10)
        umowa.gwarancja_miesiecy = 12
        umowa.save()
        teksty = " | ".join(z.tekst for z in zadania_umow(Budowa.objects.all(), dzis))
        self.assertIn("Brak skanu", teksty)
        self.assertIn("Zwrot zabezpieczenia cz. 1", teksty)
        self.assertIn("Koniec gwarancji", teksty)
        umowa.zwrot1_zwrocono = True
        umowa.save()
        self.assertNotIn("cz. 1", " ".join(z.tekst for z in zadania_umow(Budowa.objects.all(), dzis)))

    def test_brak_umowy_na_aktywnej_budowie(self):
        Budowa.objects.create(nazwa="Bez umowy", klient=self.klient, adres="x", etap=Etap.REALIZACJA)
        self.assertIn("Brak danych umowy", zadania_umow(Budowa.objects.all())[0].tekst)

    def test_migracja_usunela_etap_oferta(self):
        self.assertNotIn("oferta", Etap.values)


class WidokiTest(BazaUmow):
    def test_utworzenie_budowy_formularzem(self):
        self.client.force_login(self.handlowiec)
        url = reverse("umowy:z_oferty", args=[self.oferta.pk])
        r = self.client.get(url)
        self.assertContains(r, "81000")
        r = self.client.post(url, {
            "b-nazwa": "Hala", "b-adres": "ul. Testowa 1", "b-miasto": "Testowo", "b-kierownik": self.kierownik.pk,
            "u-wartosc_netto": "81000", "u-vat_procent": "23", "u-sposob_rozliczenia": "obmiar", "u-termin_platnosci_dni": "30",
            "u-gwarancja_miesiecy": "36", "u-zabezpieczenie_forma": "brak", "u-zabezpieczenie_procent": "0", "u-zwrot1_procent": "70",
        })
        self.oferta.refresh_from_db()
        self.assertIsNotNone(self.oferta.budowa)
        self.assertRedirects(r, self.oferta.budowa.get_absolute_url())
        # Druga próba – przekierowanie do istniejącej budowy, bez duplikatu.
        self.client.get(url)
        self.assertEqual(Budowa.objects.count(), 1)

    def test_nie_z_przegranej(self):
        self.oferta.status = Status.PRZEGRANA
        self.oferta.save()
        self.client.force_login(self.handlowiec)
        self.client.get(reverse("umowy:z_oferty", args=[self.oferta.pk]))
        self.assertEqual(Budowa.objects.count(), 0)

    def test_uprawnienia(self):
        b = self.utworz()
        inna = Budowa.objects.create(nazwa="Inna", klient=self.klient, adres="x")
        Umowa.objects.create(budowa=inna, wartosc_netto=1)
        szczegoly = reverse("budowy:szczegoly", args=[b.pk])
        # Kierownik: widzi umowę swojej budowy, nie może edytować, cudzej nie widzi.
        self.client.force_login(self.kierownik)
        r = self.client.get(szczegoly)
        self.assertContains(r, "Zakres prac z umowy")
        self.assertNotContains(r, "Edytuj umowę")
        self.assertEqual(self.client.get(reverse("umowy:edytuj", args=[b.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("umowy:skan", args=[inna.pk])).status_code, 404)
        # BHP: bez kwot.
        self.client.force_login(konto("bhp", u.BHP))
        r = self.client.get(szczegoly)
        self.assertNotContains(r, "Zakres prac z umowy")
        self.assertNotContains(r, "Wartość netto")
        self.assertEqual(self.client.get(reverse("umowy:skan", args=[b.pk])).status_code, 403)

    def test_skan_tylko_przez_kontrole(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            b = self.utworz()
            b.umowa.skan.save("u.pdf", ContentFile(b"%PDF test"))
            self.client.force_login(self.kierownik)
            r = self.client.get(reverse("umowy:skan", args=[b.pk]))
            self.assertEqual(r.status_code, 200)
            # Bezpośredni adres pliku nie działa – katalog umów nie jest udostępniany ogólnie.
            self.client.force_login(self.handlowiec)
            self.assertEqual(self.client.get(b.umowa.skan.url).status_code, 403)

    def test_edycja_zakresu(self):
        b = self.utworz()
        self.client.force_login(self.handlowiec)
        p = list(b.zakres.all())
        dane = {"zakres-TOTAL_FORMS": "3", "zakres-INITIAL_FORMS": "2", "zakres-MIN_NUM_FORMS": "0", "zakres-MAX_NUM_FORMS": "1000"}
        for i, poz in enumerate(p):
            dane.update({f"zakres-{i}-id": poz.pk, f"zakres-{i}-budowa": b.pk, f"zakres-{i}-nazwa": poz.nazwa, f"zakres-{i}-opis": "",
                         f"zakres-{i}-jednostka": poz.jednostka, f"zakres-{i}-ilosc": str(poz.ilosc), f"zakres-{i}-cena_netto": str(poz.cena_netto)})
        dane["zakres-1-DELETE"] = "on"
        dane.update({"zakres-2-nazwa": "Dylatacje", "zakres-2-jednostka": "mb", "zakres-2-ilosc": "50", "zakres-2-cena_netto": "28", "zakres-2-opis": ""})
        r = self.client.post(reverse("umowy:zakres", args=[b.pk]), dane)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(list(b.zakres.values_list("nazwa", flat=True)), ["Epoksyd", "Dylatacje"])
