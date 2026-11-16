from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import DokumentMaterialu, Material, MaterialBudowy


class DokumentInline(admin.TabularInline):
    model = DokumentMaterialu
    extra = 0


@admin.register(Material)
class MaterialAdmin(SimpleHistoryAdmin):
    list_display = ("nazwa", "producent", "rodzaj", "chemiczny", "aktywny")
    list_filter = ("rodzaj", "aktywny", "chemiczny")
    search_fields = ("nazwa", "producent")
    filter_horizontal = ("systemy",)
    inlines = [DokumentInline]


@admin.register(MaterialBudowy)
class MaterialBudowyAdmin(SimpleHistoryAdmin):
    list_display = ("material", "budowa", "dodany_recznie", "wykluczony")
    list_filter = ("budowa",)
