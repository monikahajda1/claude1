from django import forms

from apps.core.formularze import BootstrapMixin, PoleDaty

from .models import DokumentPracownika, DokumentSprzetu, Dotyczy, Pracownik, Sprzet, TypDokumentu

DOZWOLONE_ROZSZERZENIA = (".pdf", ".jpg", ".jpeg", ".png", ".heic", ".webp")


class PracownikForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Pracownik
        fields = ["imie", "nazwisko", "stanowisko", "firma", "telefon", "aktywny", "uwagi"]
        widgets = {"uwagi": forms.Textarea(attrs={"rows": 3})}


class SprzetForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Sprzet
        fields = ["nazwa", "numer_ewidencyjny", "producent_model", "aktywny", "uwagi"]
        widgets = {"uwagi": forms.Textarea(attrs={"rows": 3})}


class DokumentFormBaza(BootstrapMixin, forms.ModelForm):
    dotyczy = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["typ"].queryset = TypDokumentu.objects.filter(dotyczy=self.dotyczy)
        # Na telefonie pozwala zrobić zdjęcie aparatem albo wybrać plik.
        self.fields["plik"].widget.attrs["accept"] = "image/*,application/pdf"
        self.fields["plik"].help_text = "PDF lub zdjęcie. Na telefonie możesz od razu zrobić zdjęcie aparatem."

    def clean_plik(self):
        plik = self.cleaned_data.get("plik")
        if plik and hasattr(plik, "name") and not plik.name.lower().endswith(DOZWOLONE_ROZSZERZENIA):
            raise forms.ValidationError("Dozwolone pliki: PDF, JPG, PNG, HEIC, WEBP.")
        if plik and hasattr(plik, "size") and plik.size > 20 * 1024 * 1024:
            raise forms.ValidationError("Plik jest za duży (maks. 20 MB).")
        return plik

    def clean(self):
        dane = super().clean()
        wyd, waz = dane.get("data_wydania"), dane.get("data_waznosci")
        if wyd and waz and waz < wyd:
            self.add_error("data_waznosci", "Data ważności nie może być wcześniejsza niż data wydania.")
        return dane


POLA_DOKUMENTU = ["typ", "numer", "data_wydania", "data_waznosci", "plik", "uwagi"]
WIDGETY_DOKUMENTU = {"data_wydania": PoleDaty(), "data_waznosci": PoleDaty()}


class DokumentPracownikaForm(DokumentFormBaza):
    dotyczy = Dotyczy.PRACOWNIK

    class Meta:
        model = DokumentPracownika
        fields = POLA_DOKUMENTU
        widgets = WIDGETY_DOKUMENTU


class DokumentSprzetuForm(DokumentFormBaza):
    dotyczy = Dotyczy.SPRZET

    class Meta:
        model = DokumentSprzetu
        fields = POLA_DOKUMENTU
        widgets = WIDGETY_DOKUMENTU
