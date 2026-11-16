from django import forms

from apps.core.formularze import BootstrapMixin, PoleDaty

from .models import IBWR, KZM, DokumentFirmy, OdhaczeniePunktu, Zagrozenie

PLIKI = (".pdf", ".jpg", ".jpeg", ".png", ".heic", ".webp")


def sprawdz_plik(plik):
    if plik and hasattr(plik, "size"):
        if not plik.name.lower().endswith(PLIKI):
            raise forms.ValidationError("Dozwolone pliki: PDF lub zdjęcie.")
        if plik.size > 20 * 1024 * 1024:
            raise forms.ValidationError("Plik jest za duży (maks. 20 MB).")
    return plik


class PlikMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nazwa in ("skan", "plik"):
            if nazwa in self.fields:
                self.fields[nazwa].widget.attrs["accept"] = "application/pdf,image/*"

    def clean_skan(self):
        return sprawdz_plik(self.cleaned_data.get("skan"))

    def clean_plik(self):
        return sprawdz_plik(self.cleaned_data.get("plik"))


class KZMForm(PlikMixin, BootstrapMixin, forms.ModelForm):
    class Meta:
        model = KZM
        fields = ["status", "zastosowanie", "data_zlozenia", "data_decyzji", "uwagi_zatwierdzajacego", "skan"]
        widgets = {"data_zlozenia": PoleDaty(), "data_decyzji": PoleDaty(),
                   "zastosowanie": forms.Textarea(attrs={"rows": 2}), "uwagi_zatwierdzajacego": forms.Textarea(attrs={"rows": 2})}


class IBWRForm(PlikMixin, BootstrapMixin, forms.ModelForm):
    class Meta:
        model = IBWR
        fields = ["status", "zagrozenia", "dodatkowe_zagrozenia", "procedury_awaryjne", "data_przekazania", "data_zatwierdzenia", "skan"]
        widgets = {"zagrozenia": forms.CheckboxSelectMultiple, "data_przekazania": PoleDaty(), "data_zatwierdzenia": PoleDaty(),
                   "dodatkowe_zagrozenia": forms.Textarea(attrs={"rows": 3}), "procedury_awaryjne": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["zagrozenia"].queryset = Zagrozenie.objects.filter(aktywne=True)
        if not self.instance.pk:
            self.initial.setdefault("zagrozenia", list(Zagrozenie.objects.filter(aktywne=True, domyslne=True)))


class OdhaczenieForm(PlikMixin, BootstrapMixin, forms.ModelForm):
    class Meta:
        model = OdhaczeniePunktu
        fields = ["zrobione", "nie_dotyczy", "uwagi", "plik"]


class DokumentFirmyForm(PlikMixin, BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DokumentFirmy
        fields = ["rodzaj", "nazwa", "numer", "data_waznosci", "plik", "wymagany_na_budowie", "uwagi"]
        widgets = {"data_waznosci": PoleDaty()}
