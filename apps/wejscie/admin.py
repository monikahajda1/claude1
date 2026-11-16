from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import IBWR, KZM, DokumentFirmy, OdhaczeniePunktu, PunktChecklisty, Zagrozenie


@admin.register(Zagrozenie)
class ZagrozenieAdmin(SimpleHistoryAdmin):
    list_display = ("nazwa", "domyslne", "aktywne", "kolejnosc")
    list_editable = ("domyslne", "aktywne", "kolejnosc")


@admin.register(PunktChecklisty)
class PunktChecklistyAdmin(SimpleHistoryAdmin):
    list_display = ("nazwa", "opis", "aktywny", "kolejnosc")
    list_editable = ("aktywny", "kolejnosc")


@admin.register(DokumentFirmy)
class DokumentFirmyAdmin(SimpleHistoryAdmin):
    list_display = ("nazwa", "rodzaj", "data_waznosci", "wymagany_na_budowie")
    list_filter = ("rodzaj",)


@admin.register(KZM)
class KZMAdmin(SimpleHistoryAdmin):
    list_display = ("numer", "material", "budowa", "status")
    list_filter = ("status",)


admin.site.register(IBWR, SimpleHistoryAdmin)
admin.site.register(OdhaczeniePunktu, SimpleHistoryAdmin)
