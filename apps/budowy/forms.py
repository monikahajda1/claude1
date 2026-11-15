from django import forms
from django.contrib.auth import get_user_model

from apps.core.formularze import BootstrapMixin, PoleDaty
from apps.konta.uprawnienia import KIEROWNIK

from .models import Budowa, Klient


class BudowaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Budowa
        fields = [
            "nazwa", "klient", "adres", "miasto", "etap", "kierownik", "system_posadzki",
            "powierzchnia_m2", "wartosc_netto", "data_rozpoczecia", "data_zakonczenia", "uwagi",
        ]
        widgets = {
            "data_rozpoczecia": PoleDaty(),
            "data_zakonczenia": PoleDaty(),
            "uwagi": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "kierownik" in self.fields:
            self.fields["kierownik"].queryset = get_user_model().objects.filter(groups__name=KIEROWNIK, is_active=True)

    def clean(self):
        dane = super().clean()
        start, koniec = dane.get("data_rozpoczecia"), dane.get("data_zakonczenia")
        if start and koniec and koniec < start:
            self.add_error("data_zakonczenia", "Zakończenie nie może być przed startem.")
        return dane


class BudowaKierownikForm(BudowaForm):
    """Kierownik robót może zmieniać etap i uwagi, ale nie klienta, wartości ani przypisania."""

    class Meta(BudowaForm.Meta):
        fields = ["etap", "data_rozpoczecia", "data_zakonczenia", "uwagi"]


class ZespolBudowyForm(BootstrapMixin, forms.ModelForm):
    """Przypisanie pracowników i sprzętu do budowy (dział BHP)."""

    class Meta:
        model = Budowa
        fields = ["pracownicy", "sprzet"]
        widgets = {"pracownicy": forms.CheckboxSelectMultiple, "sprzet": forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.bhp.models import Pracownik, Sprzet

        # Pokazujemy aktywnych + tych, którzy już są przypisani (żeby nie zniknęli po cichu).
        b = self.instance
        self.fields["pracownicy"].queryset = (Pracownik.objects.filter(aktywny=True) | b.pracownicy.all()).distinct()
        self.fields["sprzet"].queryset = (Sprzet.objects.filter(aktywny=True) | b.sprzet.all()).distinct()


class KlientForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Klient
        fields = ["nazwa", "nip", "adres", "osoba_kontaktowa", "telefon", "email", "uwagi"]
        widgets = {"uwagi": forms.Textarea(attrs={"rows": 3})}
