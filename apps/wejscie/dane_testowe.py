"""Fikcyjne materiały (z dokumentami), dokumenty firmy, KZM, IBWR i odhaczenia checklisty.

Nazwy producentów i materiałów są wymyślone; pliki to puste, fikcyjne PDF-y.
"""

from datetime import timedelta

from django.core.files.base import ContentFile

from apps.budowy.models import Budowa, Etap
from apps.materialy.models import DokumentMaterialu, Material, RodzajMaterialu as R, TypDokumentuMaterialu as T
from apps.materialy.operacje import uzupelnij_z_zakresu
from apps.oferty.models import PozycjaCennika

from .models import IBWR, KZM, DokumentFirmy, OdhaczeniePunktu, PunktChecklisty, RodzajDokumentuFirmy, StatusIBWR, StatusKZM, Zagrozenie


def pdf(tekst):
    return ContentFile(f"%PDF-1.4\n% FIKCYJNY DOKUMENT TESTOWY: {tekst}\n".encode())


P1, P2 = "Żywice Testowe Sp. z o.o. (fikcyjny)", "ChemBud-Demo S.A. (fikcyjny)"
MATERIALY = [
    # nazwa, producent, rodzaj, chemiczny, systemy (początki nazw w cenniku), dokumenty (brakujące pomijamy)
    ("Grunt epoksydowy GE-10", P1, R.GRUNT, True, ["Gruntowanie", "Posadzka epoksydowa samo", "Posadzka epoksydowa anty", "Posadzka antyelektro"], "KDS"),
    ("Żywica samopoziomująca ES-20", P1, R.ZYWICA, True, ["Posadzka epoksydowa samo", "Posadzka epoksydowa anty", "Cokolik"], "KDS"),
    ("Farba epoksydowa EF-03", P1, R.ZYWICA, True, ["Posadzka epoksydowa cienko"], "KDS"),
    ("Lakier poliuretanowy PL-5", P1, R.ZAMKNIECIE, True, ["Posadzka epoksydowa samo", "Posadzka epoksydowa anty", "Posadzka poliuretanowa", "System parkingowy"], "KDS"),
    ("Żywica poliuretanowa PU-30", P2, R.ZYWICA, True, ["Posadzka poliuretanowa", "System parkingowy"], "KDS"),
    ("Zaprawa poliuretanowo-cementowa PC-60", P2, R.ZYWICA, True, ["Posadzka poliuretanowo-cementowa"], "KDSA"),
    ("Posypka kwarcowa 0,3–0,8 mm", P2, R.POSYPKA, False, ["Posadzka epoksydowa anty", "System parkingowy"], "KD"),
    ("Żywica metakrylanowa MMA-40", P2, R.ZYWICA, True, ["Posadzka metakrylanowa"], "KS"),  # brak DoP – pokaże się na checkliście
    ("Zestaw przewodzący ESD-Test", P1, R.ZYWICA, True, ["Posadzka antyelektro"], "KDS"),
    ("Masa naprawcza epoksydowa EN-1", P1, R.MASA, True, ["Naprawa"], "KDS"),
    ("Masa dylatacyjna PU-D", P2, R.COKOL, True, ["Dylatacje"], "KDS"),
]
KODY = {"K": T.KARTA_TECHNICZNA, "D": T.DOP, "S": T.SDS, "A": T.ATEST}


def wczytaj_materialy(dzis):
    for nazwa, producent, rodzaj, chem, systemy, dok in MATERIALY:
        m = Material.objects.create(nazwa=nazwa, producent=producent, rodzaj=rodzaj, chemiczny=chem,
                                    zastosowanie=f"{dict(R.choices)[rodzaj]} w systemach posadzek żywicznych.")
        for prefiks in systemy:
            m.systemy.add(*PozycjaCennika.objects.filter(nazwa__startswith=prefiks))
        for kod in dok:
            typ = KODY[kod]
            waznosc = dzis + timedelta(days=20) if typ == T.ATEST else None  # atest PZH kończy się wkrótce → alert
            d = DokumentMaterialu(material=m, typ=typ, opis="wersja testowa", data_waznosci=waznosc)
            d.plik.save(f"{kod}.pdf", pdf(f"{typ} {nazwa}"), save=False)
            d.save()


def wczytaj_dokumenty_firmy(dzis):
    pozycje = [
        (RodzajDokumentuFirmy.POLISA_OC, "Polisa OC działalności (test)", "OC/TEST/2026", dzis + timedelta(days=20), True),
        (RodzajDokumentuFirmy.KRS, "Odpis z KRS (test)", "0000000000", None, False),
        (RodzajDokumentuFirmy.ZUS, "Zaświadczenie ZUS o niezaleganiu (test)", "", dzis + timedelta(days=45), False),
    ]
    for rodzaj, nazwa, numer, waznosc, wymagany in pozycje:
        d = DokumentFirmy(rodzaj=rodzaj, nazwa=nazwa, numer=numer, data_waznosci=waznosc, wymagany_na_budowie=wymagany)
        d.plik.save("dok.pdf", pdf(nazwa), save=False)
        d.save()


def wczytaj_wejscia(dzis):
    """KZM, IBWR i checklisty – różne stany, żeby było co oglądać."""
    zagrozenia = list(Zagrozenie.objects.filter(domyslne=True))
    punkty = list(PunktChecklisty.objects.all())
    for b in Budowa.objects.exclude(etap=Etap.ZAKONCZONA):
        uzupelnij_z_zakresu(b)
        materialy = [mb.material for mb in b.materialy.select_related("material")]
        if b.etap in (Etap.REALIZACJA, Etap.ROZLICZENIE, Etap.DOKUMENTACJA):
            stan_kzm, stan_ibwr, odhaczone = StatusKZM.ZATWIERDZONA, StatusIBWR.ZATWIERDZONA, len(punkty)
        elif b.etap == Etap.PRZYGOTOWANIE:
            stan_kzm, stan_ibwr, odhaczone = StatusKZM.ZLOZONA, StatusIBWR.PRZEKAZANA, 2
        else:
            continue  # budowy na etapie umowy – checklista dopiero do zrobienia
        for i, m in enumerate(materialy):
            status = stan_kzm if not (b.etap == Etap.PRZYGOTOWANIE and i == 0) else StatusKZM.ZATWIERDZONA
            if b.etap == Etap.PRZYGOTOWANIE and i == len(materialy) - 1:
                continue  # jednej KZM brakuje
            KZM.objects.create(budowa=b, material=m, zastosowanie=m.zastosowanie, status=status,
                               data_zlozenia=dzis - timedelta(days=10), data_decyzji=dzis - timedelta(days=3) if status == StatusKZM.ZATWIERDZONA else None)
        ibwr = IBWR.objects.create(budowa=b, status=stan_ibwr, data_przekazania=dzis - timedelta(days=7))
        ibwr.zagrozenia.set(zagrozenia)
        for p in punkty[:odhaczone]:
            OdhaczeniePunktu.objects.create(budowa=b, punkt=p, zrobione=True, data=dzis - timedelta(days=5))
