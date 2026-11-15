from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import Uzytkownik


@admin.register(Uzytkownik)
class UzytkownikAdmin(UserAdmin, SimpleHistoryAdmin):
    list_display = ("username", "first_name", "last_name", "lista_rol", "tylko_podglad", "is_active")
    list_filter = ("groups", "tylko_podglad", "is_active")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Dane osobowe", {"fields": ("first_name", "last_name", "email", "telefon")}),
        (
            "Role i uprawnienia",
            {
                "fields": ("groups", "tylko_podglad", "is_active", "is_staff", "is_superuser"),
                "description": "Rola = grupa. Aby ktoś mógł wejść do tego panelu administracyjnego, "
                "zaznacz „W zespole” (is_staff) – tylko dla Administratora.",
            },
        ),
        ("Ważne daty", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "first_name", "last_name", "password1", "password2", "groups", "tylko_podglad")}),
    )

    @admin.display(description="role")
    def lista_rol(self, obj):
        return ", ".join(obj.groups.values_list("name", flat=True)) or "—"
