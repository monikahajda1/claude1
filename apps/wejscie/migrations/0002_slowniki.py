"""Słowniki startowe: typowe zagrożenia przy posadzkach żywicznych i ręczne punkty checklisty.
Można je zmieniać w panelu administracyjnym."""

from django.db import migrations

ZAGROZENIA = [
    ("Kontakt skóry i oczu z żywicami i utwardzaczami (uczulenia, poparzenia chemiczne)",
     "Rękawice nitrylowe, okulary ochronne, odzież z długim rękawem; myjka do oczu na stanowisku; zapoznanie z kartami charakterystyki."),
    ("Wdychanie oparów i rozpuszczalników",
     "Wentylacja pomieszczeń, półmaska z pochłaniaczem A2 przy pracy w zamkniętych pomieszczeniach, przerwy w pracy."),
    ("Pył przy szlifowaniu i śrutowaniu podłoża",
     "Maszyny z odkurzaczem przemysłowym, półmaska P3, okulary ochronne."),
    ("Hałas maszyn (szlifierki, śrutownice)", "Ochronniki słuchu, ograniczenie czasu ekspozycji."),
    ("Porażenie prądem (urządzenia 230/400 V)",
     "Sprawne przewody i rozdzielnice z zabezpieczeniem różnicowoprądowym, aktualne pomiary elektronarzędzi, zakaz pracy przy uszkodzonej izolacji."),
    ("Pochwycenie przez elementy wirujące maszyn", "Osłony maszyn, obsługa tylko przez przeszkolonych operatorów, ściśle przylegająca odzież."),
    ("Pożar (materiały łatwopalne, rozpuszczalniki)",
     "Gaśnica proszkowa na stanowisku, zakaz palenia i używania otwartego ognia, przechowywanie materiałów w zamkniętych opakowaniach."),
    ("Poślizgnięcie i potknięcie (świeże warstwy, przewody)",
     "Oznakowanie i wygrodzenie strefy prac, porządek na stanowisku, obuwie antypoślizgowe."),
    ("Ręczne przenoszenie ciężarów (worki, opakowania)", "Przestrzeganie norm dźwigania, wózki transportowe, praca w parach."),
]

PUNKTY = [
    ("Szkolenie stanowiskowe / wprowadzenie u GW", "np. instruktaż koordynatora BHP generalnego wykonawcy"),
    ("Zgłoszenie listy pracowników i sprzętu do GW", ""),
    ("Zapoznanie ekipy z planem BIOZ", ""),
    ("Uzgodnione zaplecze: prąd 400 V, woda, magazyn materiałów", ""),
    ("Protokół przekazania frontu robót", ""),
]


def dodaj(apps, schema_editor):
    Zagrozenie = apps.get_model("wejscie", "Zagrozenie")
    for i, (nazwa, srodki) in enumerate(ZAGROZENIA, 1):
        Zagrozenie.objects.get_or_create(nazwa=nazwa, defaults={"srodki": srodki, "kolejnosc": i * 10})
    Punkt = apps.get_model("wejscie", "PunktChecklisty")
    for i, (nazwa, opis) in enumerate(PUNKTY, 1):
        Punkt.objects.get_or_create(nazwa=nazwa, defaults={"opis": opis, "kolejnosc": i * 10})


class Migration(migrations.Migration):
    dependencies = [("wejscie", "0001_initial")]
    operations = [migrations.RunPython(dodaj, migrations.RunPython.noop)]
