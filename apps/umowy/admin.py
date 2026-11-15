from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Aneks, PozycjaZakresu, Umowa


class AneksInline(admin.TabularInline):
    model = Aneks
    extra = 0


@admin.register(Umowa)
class UmowaAdmin(SimpleHistoryAdmin):
    list_display = ("budowa", "numer", "data_podpisania", "wartosc_netto", "sposob_rozliczenia")
    search_fields = ("numer", "budowa__nazwa", "budowa__numer")
    inlines = [AneksInline]


@admin.register(PozycjaZakresu)
class PozycjaZakresuAdmin(SimpleHistoryAdmin):
    list_display = ("nazwa", "budowa", "ilosc", "jednostka", "cena_netto")
    list_filter = ("budowa",)
