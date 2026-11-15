import io
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from docx import Document

from apps.budowy.models import Klient
from apps.konta import uprawnienia as u
from apps.konta.models import Uzytkownik
from apps.pulpit.zadania import zadania_ofert
from apps.szablony.generator import generuj

from . import operacje
from .dokument import kontekst_oferty, kontekst_przykladowy
from .models import Oferta, PozycjaCennika, PozycjaOferty, Status, Wariant
from .statystyki import policz


def konto(login, *role, **extra):
    user = Uzytkownik.objects.create_user(login, password="x-Haslo-12345", **extra)
    user.groups.set(Group.objects.filter(name__in=role))
    return user


class BazaOfert(TestCase):
    def setUp(self):
        self.handlowiec = konto("hand", u.HANDLOWIEC, first_name="Henryk", last_name="Test")
        self.klient = Klient.objects.create(nazwa="Klient Testowy", telefon="500 000 000")
        self.system = PozycjaCennika.objects.create(nazwa="Epoksyd 2 mm", cena_netto=Decimal("85"), koszt=Decimal("58"))
        self.oferta = Oferta.objects.create(klient=self.klient, nazwa="Hala", handlowiec=self.handlowiec, rabat_procent=Decimal("5"))
        self.wariant = Wariant.objects.create(oferta=self.oferta)
        PozycjaOferty.objects.create(wariant=self.wariant, pozycja_cennika=self.system, nazwa="Epoksyd", ilosc=Decimal("1000"),
                                     cena_netto=Decimal("85"), koszt_jednostkowy=Decimal("58"))
        PozycjaOferty.objects.create(wariant=self.wariant, nazwa="Cokolik", jednostka="mb", ilosc=Decimal("120"),
                                     cena_netto=Decimal("48"), koszt_jednostkowy=Decimal("26"))


class ObliczeniaTest(BazaOfert):
    def test_sumy(self):
        s = self.wariant.podsumowanie()
        self.assertEqual(s["przed_rabatem"], Decimal("90760.00"))
        self.assertEqual(s["rabat"], Decimal("4538.00"))
        self.assertEqual(s["netto"], Decimal("86222.00"))
        self.assertEqual(s["vat"], Decimal("19831.06"))
        self.assertEqual(s["brutto"], Decimal("106053.06"))
        self.assertEqual(s["marza"], Decimal("86222.00") - Decimal("61120.00"))

    def test_marza_nieznana_gdy_brak_kosztu(self):
        PozycjaOferty.objects.create(wariant=self.wariant, nazwa="Ręczna", ilosc=1, cena_netto=100)
        self.assertIsNone(self.wariant.podsumowanie()["marza"])

    def test_dokument_ma_te_same_kwoty(self):
        k = kontekst_oferty(self.oferta)
        self.assertEqual(k["netto"], "86 222,00")
        self.assertEqual(k["brutto"], "106 053,06")
        self.assertIn("sto sześć tysięcy", k["brutto_slownie"])

    def test_numeracja(self):
        druga = Oferta.objects.create(klient=self.klient, nazwa="Druga")
        rok = timezone.localdate().year
        self.assertEqual(self.oferta.numer, f"OF/{rok}/0001")
        self.assertEqual(druga.numer, f"OF/{rok}/0002")


class OperacjeTest(BazaOfert):
    def test_wyslanie_ustawia_przypomnienie_za_7_dni(self):
        operacje.oznacz_wyslana(self.oferta, dzis=date(2026, 3, 2))
        self.assertEqual(self.oferta.status, Status.WYSLANA)
        self.assertEqual(self.oferta.nastepny_kontakt, date(2026, 3, 9))

    def test_nowa_wersja_kopiuje_i_archiwizuje(self):
        operacje.oznacz_wyslana(self.oferta)
        v2 = operacje.nowa_wersja(self.oferta)
        self.oferta.refresh_from_db()
        self.assertFalse(self.oferta.aktualna)
        self.assertTrue(v2.aktualna)
        self.assertEqual(v2.numer, self.oferta.numer)
        self.assertEqual(v2.pelny_numer, self.oferta.numer + "/v2")
        self.assertEqual(v2.status, Status.ROBOCZA)
        self.assertEqual(v2.warianty.first().pozycje.count(), 2)
        self.assertEqual(self.wariant.pozycje.count(), 2)  # oryginał nietknięty

    def test_wygrana_zaznacza_wariant(self):
        b = operacje.kopiuj_wariant(self.wariant, self.oferta, "Wariant B")
        operacje.rozstrzygnij(self.oferta, Status.WYGRANA, b)
        self.assertTrue(Wariant.objects.get(pk=b.pk).wybrany)
        self.assertEqual(self.oferta.wariant_glowny().pk, b.pk)
        self.assertIsNone(self.oferta.nastepny_kontakt)

    def test_przypomnienia_na_co_dzis(self):
        operacje.oznacz_wyslana(self.oferta, dzis=timezone.localdate() - timedelta(days=10))
        zadania = zadania_ofert(Oferta.objects.all())
        self.assertTrue(any("kontakt" in z.tekst for z in zadania))
        operacje.rozstrzygnij(self.oferta, Status.PRZEGRANA, powod="cena")
        self.assertEqual(zadania_ofert(Oferta.objects.all()), [])


class StatystykiTest(BazaOfert):
    def test_skutecznosc_bez_ofert_w_toku(self):
        druga = Oferta.objects.create(klient=self.klient, nazwa="Druga")
        Wariant.objects.create(oferta=druga)
        trzecia = Oferta.objects.create(klient=self.klient, nazwa="Trzecia")
        Wariant.objects.create(oferta=trzecia)
        operacje.rozstrzygnij(self.oferta, Status.WYGRANA, self.wariant)
        operacje.rozstrzygnij(druga, Status.PRZEGRANA, powod="cena")
        operacje.oznacz_wyslana(trzecia)
        wynik = policz(list(Oferta.objects.all()))
        self.assertEqual(wynik["razem"].wyslane, 3)
        self.assertEqual(wynik["razem"].skutecznosc, Decimal("50.00"))
        self.assertEqual(wynik["powody"][0]["liczba"], 1)


class WidokiTest(BazaOfert):
    def test_bhp_i_kierownik_nie_widza_ofert(self):
        for rola in (u.BHP, u.KIEROWNIK):
            self.client.force_login(konto(f"x_{rola[:3]}", rola))
            self.assertEqual(self.client.get(reverse("oferty:lista")).status_code, 403)
            self.assertEqual(self.client.get(reverse("oferty:szczegoly", args=[self.oferta.pk])).status_code, 403)

    def test_handlowiec_nie_zmieni_cennika(self):
        self.client.force_login(self.handlowiec)
        self.assertEqual(self.client.get(reverse("oferty:cennik")).status_code, 200)
        self.assertEqual(self.client.get(reverse("oferty:cennik_nowa")).status_code, 403)

    def test_tylko_podglad_nie_wysle_oferty(self):
        self.client.force_login(konto("podglad", u.ADMINISTRATOR, tylko_podglad=True))
        self.assertEqual(self.client.post(reverse("oferty:wyslana", args=[self.oferta.pk])).status_code, 403)

    def test_po_wyslaniu_nie_mozna_zmienic_pozycji(self):
        self.client.force_login(self.handlowiec)
        operacje.oznacz_wyslana(self.oferta)
        url = reverse("oferty:wariant", args=[self.oferta.pk, self.wariant.pk])
        self.assertRedirects(self.client.get(url), self.oferta.get_absolute_url())
        self.assertEqual(self.client.post(url, {}).status_code, 403)

    def test_zapis_kalkulacji(self):
        self.client.force_login(self.handlowiec)
        url = reverse("oferty:wariant", args=[self.oferta.pk, self.wariant.pk])
        istniejace = list(self.wariant.pozycje.all())
        dane = {
            "nazwa": "Wariant A", "opis": "", "powierzchnia_m2": "1000",
            "pozycje-TOTAL_FORMS": "3", "pozycje-INITIAL_FORMS": "2", "pozycje-MIN_NUM_FORMS": "0", "pozycje-MAX_NUM_FORMS": "1000",
        }
        for i, p in enumerate(istniejace):
            dane.update({f"pozycje-{i}-id": p.pk, f"pozycje-{i}-wariant": self.wariant.pk, f"pozycje-{i}-nazwa": p.nazwa,
                         f"pozycje-{i}-jednostka": p.jednostka, f"pozycje-{i}-ilosc": "10", f"pozycje-{i}-cena_netto": str(p.cena_netto),
                         f"pozycje-{i}-opis": "", f"pozycje-{i}-pozycja_cennika": p.pozycja_cennika_id or ""})
        dane["pozycje-1-DELETE"] = "on"
        dane.update({"pozycje-2-nazwa": "Nowa z cennika", "pozycje-2-jednostka": "m2", "pozycje-2-ilosc": "5",
                     "pozycje-2-cena_netto": "85", "pozycje-2-pozycja_cennika": self.system.pk, "pozycje-2-opis": ""})
        r = self.client.post(url, dane)
        self.assertEqual(r.status_code, 302, r.content.decode()[:3000])
        nazwy = list(self.wariant.pozycje.values_list("nazwa", "ilosc", "koszt_jednostkowy"))
        self.assertEqual(nazwy, [("Epoksyd", Decimal("10.00"), Decimal("58.00")), ("Nowa z cennika", Decimal("5.00"), Decimal("58.00"))])
        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.powierzchnia_m2, Decimal("1000"))

    def test_pobranie_worda(self):
        self.client.force_login(self.handlowiec)
        r = self.client.get(reverse("oferty:dokument", args=[self.oferta.pk]))
        self.assertEqual(r.status_code, 200)
        tekst = "\n".join(p.text for p in Document(io.BytesIO(r.content)).paragraphs)
        self.assertIn(self.oferta.numer, tekst)
        self.assertIn("86 222,00", tekst)
        self.assertNotIn("{{", tekst)

    def test_wbudowany_szablon_z_przykladem(self):
        dok = Document(io.BytesIO(generuj("oferta", kontekst_przykladowy())))
        tekst = "\n".join(p.text for p in dok.paragraphs)
        self.assertIn("Wariant B", tekst)
        self.assertNotIn("{%", tekst)


class SzablonAdminTest(TestCase):
    def test_bledny_szablon_odrzucony(self):
        admin = konto("adm", u.ADMINISTRATOR, is_staff=True, is_superuser=True)
        self.client.force_login(admin)
        d = Document()
        d.add_paragraph("{{ klient ")  # niedomknięte pole
        buf = io.BytesIO()
        d.save(buf)
        r = self.client.post(reverse("admin:szablony_szablondokumentu_add"), {
            "rodzaj": "oferta", "nazwa": "Zły", "aktywny": "on",
            "plik": SimpleUploadedFile("zly.docx", buf.getvalue()),
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Błąd w szablonie")

    def test_wlasny_szablon_jest_uzywany(self):
        import tempfile

        from django.test import override_settings

        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            admin = konto("adm2", u.ADMINISTRATOR, is_staff=True, is_superuser=True)
            self.client.force_login(admin)
            d = Document()
            d.add_paragraph("MOJ WZOR {{ numer_oferty }} dla {{ klient }}")
            buf = io.BytesIO()
            d.save(buf)
            r = self.client.post(reverse("admin:szablony_szablondokumentu_add"), {
                "rodzaj": "oferta", "nazwa": "Mój", "aktywny": "on",
                "plik": SimpleUploadedFile("moj.docx", buf.getvalue()),
            })
            self.assertEqual(r.status_code, 302)
            tekst = Document(io.BytesIO(generuj("oferta", kontekst_przykladowy()))).paragraphs[0].text
            self.assertEqual(tekst, "MOJ WZOR OF/2026/0001/v2 dla Przykładowy Klient Sp. z o.o.")
