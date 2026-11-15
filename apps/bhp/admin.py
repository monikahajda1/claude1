from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import DokumentPracownika, DokumentSprzetu, Pracownik, Sprzet, TypDokumentu


@admin.register(TypDokumentu)
class TypDokumentuAdmin(SimpleHistoryAdmin):
    list_display = ("nazwa", "dotyczy", "wymagany", "okres_miesiecy", "kolejnosc")
    list_filter = ("dotyczy", "wymagany")
    list_editable = ("wymagany", "okres_miesiecy", "kolejnosc")


class DokumentPracownikaInline(admin.TabularInline):
    model = DokumentPracownika
    extra = 0


class DokumentSprzetuInline(admin.TabularInline):
    model = DokumentSprzetu
    extra = 0


@admin.register(Pracownik)
class PracownikAdmin(SimpleHistoryAdmin):
    list_display = ("nazwisko", "imie", "stanowisko", "firma", "aktywny")
    list_filter = ("aktywny",)
    search_fields = ("nazwisko", "imie", "firma")
    inlines = [DokumentPracownikaInline]


@admin.register(Sprzet)
class SprzetAdmin(SimpleHistoryAdmin):
    list_display = ("nazwa", "numer_ewidencyjny", "producent_model", "aktywny")
    list_filter = ("aktywny",)
    search_fields = ("nazwa", "numer_ewidencyjny")
    inlines = [DokumentSprzetuInline]
