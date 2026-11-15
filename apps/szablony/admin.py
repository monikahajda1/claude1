from django import forms
from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import SzablonDokumentu


class SzablonForm(forms.ModelForm):
    class Meta:
        model = SzablonDokumentu
        fields = "__all__"

    def clean_plik(self):
        plik = self.cleaned_data["plik"]
        if plik and not plik.name.lower().endswith(".docx"):
            raise forms.ValidationError("Szablon musi być plikiem Word .docx (nie .doc ani .pdf).")
        return plik

    def clean(self):
        dane = super().clean()
        plik = dane.get("plik")
        if plik and hasattr(plik, "read"):
            # Próbne wypełnienie przykładowymi danymi – od razu widać błędy w polach.
            from django.core.exceptions import ValidationError

            from .generator import wypelnij
            from .pola import PRZYKLADY

            przyklad = PRZYKLADY.get(dane.get("rodzaj"))
            if przyklad:
                try:
                    wypelnij(plik, przyklad())
                except ValidationError as e:
                    raise forms.ValidationError(e.messages)
                except Exception as e:  # uszkodzony plik itp.
                    raise forms.ValidationError(f"Nie udało się odczytać pliku Word: {e}")
                plik.seek(0)
        return dane


@admin.register(SzablonDokumentu)
class SzablonAdmin(SimpleHistoryAdmin):
    form = SzablonForm
    list_display = ("nazwa", "rodzaj", "aktywny", "dodano", "pola")
    list_filter = ("rodzaj", "aktywny")

    @admin.display(description="lista pól")
    def pola(self, obj):
        return format_html('<a href="/szablony/pola/{}/">pokaż pola</a>', obj.rodzaj)
