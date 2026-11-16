from django import forms

from apps.core.formularze import BootstrapMixin, PoleDaty
from apps.oferty.models import PozycjaCennika

from .models import DokumentMaterialu, Material


class MaterialForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Material
        fields = ["nazwa", "producent", "rodzaj", "zastosowanie", "chemiczny", "aktywny", "systemy"]
        widgets = {"zastosowanie": forms.Textarea(attrs={"rows": 2}), "systemy": forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["systemy"].queryset = PozycjaCennika.objects.filter(aktywna=True)


class DokumentMaterialuForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DokumentMaterialu
        fields = ["typ", "plik", "opis", "data_waznosci"]
        widgets = {"data_waznosci": PoleDaty()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plik"].widget.attrs["accept"] = "application/pdf,image/*"

    def clean_plik(self):
        plik = self.cleaned_data.get("plik")
        if plik and hasattr(plik, "size"):
            if not plik.name.lower().endswith((".pdf", ".jpg", ".jpeg", ".png", ".docx")):
                raise forms.ValidationError("Dozwolone pliki: PDF, JPG, PNG, DOCX.")
            if plik.size > 30 * 1024 * 1024:
                raise forms.ValidationError("Plik jest za duży (maks. 30 MB).")
        return plik
