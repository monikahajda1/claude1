import io
import tempfile
import zipfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from docx import Document

from apps.bhp.models import DokumentPracownika, DokumentSprzetu, Pracownik, Sprzet, TypDokumentu
from apps.budowy.models import Budowa, Etap, Klient
from apps.konta import uprawnienia as u
from apps.konta.models import Uzytkownik
from apps.materialy.models import DokumentMaterialu, Material, MaterialBudowy
from apps.materialy.operacje import uzupelnij_z_zakresu
from apps.oferty.models import PozycjaCennika
from apps.pulpit.zadania import zadania_budow, zadania_dokumentow
from apps.umowy.models import PozycjaZakresu, Umowa

from .checklista import checklista, podsumowanie
from .models import IBWR, KZM, DokumentFirmy, OdhaczeniePunktu, PunktChecklisty, StatusIBWR, StatusKZM, Zagrozenie

MEDIA = tempfile.mkdtemp()


def konto(login, *role):
    user = Uzytkownik.objects.create_user(login, password="x-Haslo-12345")
    user.groups.set(Group.objects.filter(name__in=role))
    return user


def plik(tekst="test"):
    return ContentFile(f"%PDF-1.4 {tekst}".encode())


@override_settings(MEDIA_ROOT=MEDIA)
class Baza(TestCase):
    def setUp(self):
        self.dzis = timezone.localdate()
        self.kierownik = konto("kier", u.KIEROWNIK)
        klient = Klient.objects.create(nazwa="Klient")
        self.budowa = Budowa.objects.create(nazwa="Hala", klient=klient, adres="ul. 1", kierownik=self.kierownik,
                                            etap=Etap.UMOWA, data_rozpoczecia=self.dzis + timedelta(days=5),
                                            data_zakonczenia=self.dzis + timedelta(days=30))
        self.system = PozycjaCennika.objects.create(nazwa="Epoksyd 2 mm", cena_netto=Decimal("85"))
        PozycjaZakresu.objects.create(budowa=self.budowa, pozycja_cennika=self.system, nazwa="Epoksyd", ilosc=100, cena_netto=Decimal("85"))
        self.grunt = Material.objects.create(nazwa="Grunt X", producent="Fikcja")
        self.grunt.systemy.add(self.system)
        self.zywica = Material.objects.create(nazwa="Żywica Y", producent="Fikcja")
        self.zywica.systemy.add(self.system)

    def dokumenty(self, m, typy=("karta_techniczna", "dop", "sds")):
        for t in typy:
            d = DokumentMaterialu(material=m, typ=t)
            d.plik.save("d.pdf", plik(f"{t} {m.nazwa}"))


class MaterialyTest(Baza):
    def test_uzupelnij_z_zakresu_szanuje_wykluczenie(self):
        self.assertEqual(uzupelnij_z_zakresu(self.budowa), 2)
        mb = MaterialBudowy.objects.get(budowa=self.budowa, material=self.grunt)
        mb.wykluczony = True
        mb.save()
        self.assertEqual(uzupelnij_z_zakresu(self.budowa), 0)
        self.assertTrue(MaterialBudowy.objects.get(pk=mb.pk).wykluczony)

    def test_braki_dokumentow(self):
        self.dokumenty(self.grunt, ("karta_techniczna",))
        self.assertEqual(self.grunt.brakujace_typy(), ["Deklaracja właściwości użytkowych (DoP)", "Karta charakterystyki (SDS)"])
        self.grunt.chemiczny = False
        self.assertEqual(self.grunt.brakujace_typy(), ["Deklaracja właściwości użytkowych (DoP)"])


class ChecklistaTest(Baza):
    def test_pusta_budowa(self):
        s = podsumowanie(checklista(self.budowa))
        self.assertFalse(s["komplet"])
        self.assertGreater(s["brakuje"], 5)

    def test_komplet(self):
        b = self.budowa
        umowa = Umowa(budowa=b, wartosc_netto=1)
        umowa.skan.save("u.pdf", plik())
        p = Pracownik.objects.create(imie="Jan", nazwisko="Test")
        for t in TypDokumentu.objects.filter(dotyczy="pracownik", wymagany=True):
            DokumentPracownika.objects.create(pracownik=p, typ=t, data_waznosci=self.dzis + timedelta(days=400))
        s = Sprzet.objects.create(nazwa="Szlifierka")
        for t in TypDokumentu.objects.filter(dotyczy="sprzet", wymagany=True):
            DokumentSprzetu.objects.create(sprzet=s, typ=t, data_waznosci=self.dzis + timedelta(days=400))
        b.pracownicy.add(p)
        b.sprzet.add(s)
        uzupelnij_z_zakresu(b)
        for m in (self.grunt, self.zywica):
            self.dokumenty(m)
            KZM.objects.create(budowa=b, material=m, status=StatusKZM.ZATWIERDZONA)
        IBWR.objects.create(budowa=b, status=StatusIBWR.ZATWIERDZONA)
        DokumentFirmy.objects.create(rodzaj="polisa_oc", nazwa="OC", data_waznosci=self.dzis + timedelta(days=200), wymagany_na_budowie=True)
        for punkt in PunktChecklisty.objects.all():
            OdhaczeniePunktu.objects.create(budowa=b, punkt=punkt, zrobione=True)
        punkty = checklista(b)
        self.assertTrue(podsumowanie(punkty)["komplet"], [p.nazwa for p in punkty if not p.ok])
        # Co dziś: start za 5 dni, checklista kompletna.
        self.assertIn("kompletna", zadania_budow(Budowa.objects.all(), z_checklista=True)[0].tekst)

    def test_odrzucona_kzm_nie_zalicza(self):
        uzupelnij_z_zakresu(self.budowa)
        KZM.objects.create(budowa=self.budowa, material=self.grunt, status=StatusKZM.ODRZUCONA)
        KZM.objects.create(budowa=self.budowa, material=self.zywica, status=StatusKZM.ZATWIERDZONA)
        punkt = [p for p in checklista(self.budowa) if p.nazwa.startswith("KZM")][0]
        self.assertFalse(punkt.ok)
        self.assertIn("Grunt X", punkt.szczegoly)

    def test_co_dzis_pokazuje_braki(self):
        tekst = zadania_budow(Budowa.objects.all(), z_checklista=True)[0].tekst
        self.assertIn("checklista wejścia: brakuje", tekst)
        self.assertIn("innych", tekst)

    def test_polisa_wygasajaca_na_co_dzis(self):
        DokumentFirmy.objects.create(rodzaj="polisa_oc", nazwa="OC stara", data_waznosci=self.dzis - timedelta(days=300))
        DokumentFirmy.objects.create(rodzaj="polisa_oc", nazwa="OC nowa", data_waznosci=self.dzis + timedelta(days=10))
        teksty = [z["tekst"] for z in zadania_dokumentow(materialy=False)]
        self.assertEqual(len(teksty), 1)  # stara polisa nie alarmuje
        self.assertIn("OC nowa", teksty[0])


class DokumentyTest(Baza):
    def setUp(self):
        super().setUp()
        self.admin = konto("adm", u.ADMINISTRATOR)
        self.client.force_login(self.admin)
        uzupelnij_z_zakresu(self.budowa)
        self.dokumenty(self.grunt)
        self.kzm = KZM.objects.create(budowa=self.budowa, material=self.grunt)

    def test_numer_kzm(self):
        self.assertEqual(self.kzm.numer, f"KZM/{self.budowa.numer[2:]}/01")

    def test_kzm_word(self):
        r = self.client.get(reverse("wejscie:kzm_dokument", args=[self.kzm.pk]))
        self.assertEqual(r.status_code, 200)
        tekst = " ".join(c.text for t in Document(io.BytesIO(r.content)).tables for w in t.rows for c in w.cells)
        self.assertIn("Grunt X", tekst)
        self.assertIn("Karta charakterystyki", tekst)
        self.assertNotIn("{{", tekst)

    def test_zip_tylko_aktualne_dokumenty(self):
        nowa = DokumentMaterialu(material=self.grunt, typ="karta_techniczna", opis="nowa")
        nowa.plik.save("n.pdf", plik("NOWA"))
        r = self.client.get(reverse("wejscie:kzm_zip", args=[self.kzm.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertIn("filename", r["Content-Disposition"])
        z = zipfile.ZipFile(io.BytesIO(r.content))
        nazwy = z.namelist()
        self.assertEqual(len(nazwy), 3)
        self.assertTrue(nazwy[0].startswith("01_Karta-techniczna"))
        self.assertIn(b"NOWA", z.read(nazwy[0]))
        self.assertFalse(any("KZM" in n for n in nazwy))

    def test_ibwr_word(self):
        p = Pracownik.objects.create(imie="Adam", nazwisko="Testowy", stanowisko="posadzkarz")
        t_wst = TypDokumentu.objects.get(nazwa="Szkolenie BHP wstępne")
        t_okr = TypDokumentu.objects.get(nazwa="Szkolenie BHP okresowe")
        DokumentPracownika.objects.create(pracownik=p, typ=t_wst, data_waznosci=None)
        DokumentPracownika.objects.create(pracownik=p, typ=t_okr, data_waznosci=self.dzis.replace(year=self.dzis.year + 2))
        self.budowa.pracownicy.add(p)
        ibwr = IBWR.objects.create(budowa=self.budowa)
        ibwr.zagrozenia.set(Zagrozenie.objects.all()[:2])
        ibwr.dodatkowe_zagrozenia = "Praca nocna – oświetlenie stanowisk"
        ibwr.save()
        r = self.client.get(reverse("wejscie:ibwr_dokument", args=[self.budowa.pk]))
        tekst = " ".join(c.text for t in Document(io.BytesIO(r.content)).tables for w in t.rows for c in w.cells)
        self.assertIn("Adam Testowy", tekst)
        self.assertIn(self.dzis.replace(year=self.dzis.year + 2).strftime("%d.%m.%Y"), tekst)  # szkolenie okresowe, nie „bezterminowo”
        self.assertIn("Praca nocna", tekst)
        self.assertIn("Grunt X", tekst)
        self.assertNotIn("85", tekst.replace("2085", ""))  # bez cen z zakresu
        self.assertNotIn("{{", tekst)


@override_settings(MEDIA_ROOT=MEDIA)
class UprawnieniaTest(Baza):
    def setUp(self):
        super().setUp()
        uzupelnij_z_zakresu(self.budowa)
        self.mb = MaterialBudowy.objects.get(budowa=self.budowa, material=self.grunt)
        inny = konto("kier2", u.KIEROWNIK)
        self.cudza = Budowa.objects.create(nazwa="Cudza", klient=self.budowa.klient, adres="x", kierownik=inny)
        self.kzm_cudza = KZM.objects.create(budowa=self.cudza, material=self.grunt)

    def test_kierownik(self):
        self.client.force_login(self.kierownik)
        r = self.client.post(reverse("wejscie:kzm_utworz", args=[self.budowa.pk]), {"mb": self.mb.pk})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.budowa.kzm.count(), 1)
        self.assertEqual(self.client.get(reverse("wejscie:kzm", args=[self.kzm_cudza.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("wejscie:budowa", args=[self.cudza.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("wejscie:ibwr", args=[self.budowa.pk]), {}).status_code, 403)
        self.assertEqual(self.client.get(reverse("wejscie:firma")).status_code, 403)

    def test_bhp_i_handlowiec(self):
        self.client.force_login(konto("bhp", u.BHP))
        self.assertEqual(self.client.post(reverse("wejscie:kzm_utworz", args=[self.budowa.pk]), {"mb": self.mb.pk}).status_code, 403)
        self.assertEqual(self.client.get(reverse("wejscie:ibwr", args=[self.budowa.pk])).status_code, 200)
        self.client.force_login(konto("hand", u.HANDLOWIEC))
        self.assertEqual(self.client.get(reverse("wejscie:ibwr", args=[self.budowa.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("wejscie:budowa", args=[self.budowa.pk])).status_code, 200)

    def test_pliki(self):
        self.dokumenty(self.grunt, ("karta_techniczna",))
        d = self.grunt.dokumenty.first()
        firma = DokumentFirmy(rodzaj="polisa_oc", nazwa="OC")
        firma.plik.save("oc.pdf", plik())
        self.kzm_cudza.skan.save("s.pdf", plik())
        self.client.force_login(self.kierownik)
        self.assertEqual(self.client.get(d.plik.url).status_code, 200)  # karta techniczna – dla każdego z dostępem do materiałów
        self.assertEqual(self.client.get(firma.plik.url).status_code, 403)
        self.assertEqual(self.client.get(reverse("wejscie:plik", args=["kzm", self.kzm_cudza.pk])).status_code, 404)
        self.assertEqual(self.client.get(self.kzm_cudza.skan.url).status_code, 403)  # bezpośrednio – zablokowane

    def test_odhaczenie(self):
        self.client.force_login(self.kierownik)
        punkt = PunktChecklisty.objects.first()
        self.client.post(reverse("wejscie:odhacz", args=[self.budowa.pk, punkt.pk]), {"zrobione": "on", "uwagi": "ok"})
        o = OdhaczeniePunktu.objects.get(budowa=self.budowa, punkt=punkt)
        self.assertTrue(o.zrobione)
        self.assertEqual(o.kto, self.kierownik)
        self.assertEqual(o.data, self.dzis)
