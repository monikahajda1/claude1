"""Słownik startowy rodzajów dokumentów. Można go potem zmieniać w panelu administracyjnym."""

from django.db import migrations

# (nazwa, dotyczy, wymagany, okres w miesiącach, kolejność)
TYPY = [
    ("Badania lekarskie (medycyna pracy)", "pracownik", True, 24, 10),
    ("Szkolenie BHP wstępne", "pracownik", True, None, 20),
    ("Szkolenie BHP okresowe", "pracownik", False, 36, 30),
    ("Badania do pracy na wysokości", "pracownik", False, 12, 40),
    ("Szkolenie do pracy na wysokości", "pracownik", False, 60, 50),
    ("Uprawnienia UDT – podesty ruchome", "pracownik", False, 120, 60),
    ("Uprawnienia UDT – wózki jezdniowe", "pracownik", False, 120, 70),
    ("Uprawnienia SEP (do 1 kV)", "pracownik", False, 60, 80),
    ("Przegląd UDT", "sprzet", False, 12, 10),
    ("Przegląd techniczny", "sprzet", True, 12, 20),
    ("Pomiary elektryczne (elektronarzędzia)", "sprzet", False, 12, 30),
    ("Kalibracja / świadectwo wzorcowania", "sprzet", False, 12, 40),
]


def dodaj(apps, schema_editor):
    TypDokumentu = apps.get_model("bhp", "TypDokumentu")
    for nazwa, dotyczy, wymagany, okres, kolejnosc in TYPY:
        TypDokumentu.objects.get_or_create(
            nazwa=nazwa,
            dotyczy=dotyczy,
            defaults={"wymagany": wymagany, "okres_miesiecy": okres, "kolejnosc": kolejnosc},
        )


class Migration(migrations.Migration):
    dependencies = [("bhp", "0002_initial")]
    operations = [migrations.RunPython(dodaj, migrations.RunPython.noop)]
