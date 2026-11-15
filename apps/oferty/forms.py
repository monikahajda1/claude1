from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory

from apps.core.formularze import BootstrapMixin, PoleDaty
from apps.konta.uprawnienia import ADMINISTRATOR, HANDLOWIEC

from .models import Kontakt, Oferta, PowodPrzegranej, PozycjaCennika, PozycjaOferty, RodzajPozycji, Wariant


def handlowcy():
    return get_user_model().objects.filter(groups__name__in=[HANDLOWIEC, ADMINISTRATOR], is_active=True).distinct()


class OfertaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Oferta
        fields = [
            "klient", "nazwa", "adres_budowy", "miasto", "powierzchnia_m2", "handlowiec", "data_wystawienia",
            "waznosc_dni", "termin_realizacji", "warunki_platnosci", "rabat_procent", "vat_procent", "uwagi",
            "notatki_wewnetrzne",
        ]
        widgets = {
            "data_wystawienia": PoleDaty(),
            "uwagi": forms.Textarea(attrs={"rows": 3}),
            "notatki_wewnetrzne": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["handlowiec"].queryset = handlowcy()

    def clean_rabat_procent(self):
        r = self.cleaned_data["rabat_procent"]
        if r < 0 or r >= 100:
            raise forms.ValidationError("Rabat musi być między 0 a 99,99%.")
        return r


class WariantForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Wariant
        fields = ["nazwa", "opis"]
        widgets = {"opis": forms.Textarea(attrs={"rows": 2})}


class PozycjaCennikaWybor(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.nazwa} ({obj.get_jednostka_display()})"


class PozycjaOfertyForm(BootstrapMixin, forms.ModelForm):
    pozycja_cennika = PozycjaCennikaWybor(queryset=PozycjaCennika.objects.none(), required=False, label="z cennika")

    class Meta:
        model = PozycjaOferty
        fields = ["pozycja_cennika", "nazwa", "opis", "jednostka", "ilosc", "cena_netto"]
        widgets = {"opis": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = PozycjaCennika.objects.filter(aktywna=True)
        if self.instance.pozycja_cennika_id:  # nieaktywna pozycja w starej ofercie nie może zniknąć
            qs = qs | PozycjaCennika.objects.filter(pk=self.instance.pozycja_cennika_id)
        self.fields["pozycja_cennika"].queryset = qs
        # Pola liczbowe: klawiatura numeryczna na telefonie.
        for pole in ("ilosc", "cena_netto"):
            self.fields[pole].widget.attrs.update({"inputmode": "decimal", "step": "0.01"})


PozycjeFormSet = inlineformset_factory(
    Wariant, PozycjaOferty, form=PozycjaOfertyForm, extra=0, can_delete=True, min_num=0
)


class KontaktForm(BootstrapMixin, forms.ModelForm):
    nastepny_kontakt = forms.DateField(
        label="następny kontakt", required=False, widget=PoleDaty(),
        help_text="Domyślnie za 7 dni. Wyczyść, jeśli nie trzeba przypominać.",
    )
    negocjacje = forms.BooleanField(label="klient negocjuje – zmień status na „Negocjacje”", required=False)

    class Meta:
        model = Kontakt
        fields = ["data", "forma", "notatka"]
        widgets = {"data": PoleDaty(), "notatka": forms.Textarea(attrs={"rows": 2})}


class RozstrzygniecieForm(BootstrapMixin, forms.Form):
    WYNIKI = [("wygrana", "Wygrana"), ("przegrana", "Przegrana"), ("anulowana", "Anulowana (np. błędna, zdublowana)")]
    wynik = forms.ChoiceField(label="wynik", choices=WYNIKI, widget=forms.RadioSelect)
    wariant = forms.ModelChoiceField(label="który wariant wybrał klient", queryset=Wariant.objects.none(), required=False)
    powod_przegranej = forms.ChoiceField(label="powód przegranej", choices=[("", "—")] + PowodPrzegranej.choices, required=False)
    powod_opis = forms.CharField(label="szczegóły (np. cena konkurencji)", required=False, max_length=300)

    def __init__(self, *args, oferta=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.oferta = oferta
        self.fields["wariant"].queryset = oferta.warianty.all()
        if oferta.warianty.count() == 1:
            self.fields["wariant"].initial = oferta.warianty.first()

    def clean(self):
        dane = super().clean()
        if dane.get("wynik") == "przegrana" and not dane.get("powod_przegranej"):
            self.add_error("powod_przegranej", "Wybierz powód – przyda się w statystykach.")
        if dane.get("wynik") == "wygrana" and not dane.get("wariant"):
            self.add_error("wariant", "Wybierz wariant, który wybrał klient.")
        return dane


class PozycjaCennikaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PozycjaCennika
        fields = ["nazwa", "rodzaj", "jednostka", "cena_netto", "koszt", "opis", "aktywna", "kolejnosc"]
        widgets = {"opis": forms.Textarea(attrs={"rows": 3})}


RODZAJE_CENNIKA = RodzajPozycji.choices
