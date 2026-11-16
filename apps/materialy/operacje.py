"""Materiały budowy: uzupełnianie z zakresu prac."""

from .models import Material, MaterialBudowy


def materialy_z_zakresu(budowa):
    """Materiały przypisane do pozycji cennika użytych w zakresie prac budowy."""
    pozycje = budowa.zakres.exclude(pozycja_cennika=None).values_list("pozycja_cennika_id", flat=True)
    return Material.objects.filter(systemy__in=list(pozycje), aktywny=True).distinct()


def uzupelnij_z_zakresu(budowa):
    """Dodaje brakujące materiały. Nie przywraca tych, które ktoś świadomie wykluczył. Zwraca liczbę dodanych."""
    istniejace = set(MaterialBudowy.objects.filter(budowa=budowa).values_list("material_id", flat=True))
    dodane = 0
    for m in materialy_z_zakresu(budowa):
        if m.pk not in istniejace:
            MaterialBudowy.objects.create(budowa=budowa, material=m)
            dodane += 1
    return dodane


def materialy_budowy(budowa):
    """Materiały faktycznie używane (bez wykluczonych)."""
    return [mb.material for mb in budowa.materialy.filter(wykluczony=False).select_related("material").prefetch_related("material__dokumenty")]
