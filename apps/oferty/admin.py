from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Kontakt, Oferta, PozycjaCennika, PozycjaOferty, Wariant


@admin.register(PozycjaCennika)
class PozycjaCennikaAdmin(SimpleHistoryAdmin):
    list_display = ("nazwa", "rodzaj", "jednostka", "cena_netto", "koszt", "aktywna", "kolejnosc")
    list_filter = ("rodzaj", "aktywna")
    list_editable = ("cena_netto", "koszt", "aktywna", "kolejnosc")
    search_fields = ("nazwa",)


class WariantInline(admin.TabularInline):
    model = Wariant
    extra = 0
    show_change_link = True


class KontaktInline(admin.TabularInline):
    model = Kontakt
    extra = 0


@admin.register(Oferta)
class OfertaAdmin(SimpleHistoryAdmin):
    list_display = ("pelny_numer", "nazwa", "klient", "handlowiec", "status", "data_wystawienia", "aktualna")
    list_filter = ("status", "aktualna", "handlowiec")
    search_fields = ("numer", "nazwa", "klient__nazwa")
    inlines = [WariantInline, KontaktInline]


class PozycjaInline(admin.TabularInline):
    model = PozycjaOferty
    extra = 0


@admin.register(Wariant)
class WariantAdmin(SimpleHistoryAdmin):
    list_display = ("__str__", "wybrany")
    inlines = [PozycjaInline]
