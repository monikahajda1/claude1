from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Budowa, Klient


@admin.register(Klient)
class KlientAdmin(SimpleHistoryAdmin):
    list_display = ("nazwa", "nip", "osoba_kontaktowa", "telefon")
    search_fields = ("nazwa", "nip")


@admin.register(Budowa)
class BudowaAdmin(SimpleHistoryAdmin):
    list_display = ("numer", "nazwa", "klient", "etap", "kierownik", "data_rozpoczecia")
    list_filter = ("etap", "kierownik")
    search_fields = ("numer", "nazwa", "adres", "klient__nazwa")
    filter_horizontal = ("pracownicy", "sprzet")
