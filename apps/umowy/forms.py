from django import forms
from django.forms import inlineformset_factory

from apps.budowy.models import Budowa
from apps.core.formularze import BootstrapMixin, PoleDaty

from .models import Aneks, PozycjaZakresu, Umowa

DOZWOLONE = (".pdf", ".jpg", ".jpeg", ".png", ".heic", ".webp")


def sprawdz_plik(plik):
    if plik and hasattr(plik, "size"):
        if not plik.name.lower().endswith(DOZWOLONE):
            raise forms.ValidationError("Dozwolone pliki: PDF lub zdjęcie (JPG, PNG, HEIC, WEBP).")
        if plik.size > 20 * 1024 * 1024:
            raise forms.ValidationError("Plik jest za duży (maks. 20 MB).")
    return plik


class UmowaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Umowa
        fields = [
            "numer", "data_podpisania", "wartosc_netto", "vat_procent", "sposob_rozliczenia", "termin_platnosci_dni",
            "kary_umowne", "data_odbioru_koncowego", "gwarancja_miesiecy", "zabezpieczenie_forma", "zabezpieczenie_procent",
            "zwrot1_procent", "zwrot1_data", "zwrot1_zwrocono", "zwrot2_data", "zwrot2_zwrocono", "skan", "uwagi",
        ]
        widgets = {
            "data_podpisania": PoleDaty(), "data_odbioru_koncowego": PoleDaty(),
            "zwrot1_data": PoleDaty(), "zwrot2_data": PoleDaty(),
            "uwagi": forms.Textarea(attrs={"rows": 2}),
        }

    # Grupy pól – do czytelnego formularza.
    GRUPY = [
        ("Umowa", ["numer", "data_podpisania", "wartosc_netto", "vat_procent", "sposob_rozliczenia", "termin_platnosci_dni", "kary_umowne"]),
        ("Odbiór i gwarancja", ["data_odbioru_koncowego", "gwarancja_miesiecy"]),
        ("Zabezpieczenie (kaucja)", ["zabezpieczenie_forma", "zabezpieczenie_procent", "zwrot1_procent", "zwrot1_data", "zwrot1_zwrocono", "zwrot2_data", "zwrot2_zwrocono"]),
        ("Skan i uwagi", ["skan", "uwagi"]),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skan"].widget.attrs["accept"] = "application/pdf,image/*"

    def grupy(self):
        return [(nazwa, [self[p] for p in pola]) for nazwa, pola in self.GRUPY]

    def clean_skan(self):
        return sprawdz_plik(self.cleaned_data.get("skan"))

    def clean(self):
        dane = super().clean()
        for pole in ("zabezpieczenie_procent", "zwrot1_procent"):
            v = dane.get(pole)
            if v is not None and not (0 <= v <= 100):
                self.add_error(pole, "Wpisz wartość od 0 do 100.")
        return dane


class BudowaZUmowyForm(BootstrapMixin, forms.ModelForm):
    """Dane budowy przy tworzeniu jej z oferty (klient jest brany z oferty)."""

    class Meta:
        model = Budowa
        fields = ["nazwa", "adres", "miasto", "kierownik", "system_posadzki", "powierzchnia_m2", "data_rozpoczecia", "data_zakonczenia"]
        widgets = {"data_rozpoczecia": PoleDaty(), "data_zakonczenia": PoleDaty()}
        labels = {"data_rozpoczecia": "termin rozpoczęcia (z umowy)", "data_zakonczenia": "termin zakończenia (z umowy)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model

        from apps.konta.uprawnienia import KIEROWNIK

        if "kierownik" in self.fields:
            self.fields["kierownik"].queryset = get_user_model().objects.filter(groups__name=KIEROWNIK, is_active=True)

    def clean(self):
        dane = super().clean()
        start, koniec = dane.get("data_rozpoczecia"), dane.get("data_zakonczenia")
        if start and koniec and koniec < start:
            self.add_error("data_zakonczenia", "Zakończenie nie może być przed rozpoczęciem.")
        return dane


class TerminyBudowyForm(BudowaZUmowyForm):
    """Przy edycji umowy – tylko terminy budowy."""

    class Meta(BudowaZUmowyForm.Meta):
        fields = ["data_rozpoczecia", "data_zakonczenia"]


class AneksForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Aneks
        fields = ["numer", "data", "opis", "zmiana_wartosci", "nowy_termin_zakonczenia", "skan"]
        widgets = {"data": PoleDaty(), "nowy_termin_zakonczenia": PoleDaty(), "opis": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skan"].widget.attrs["accept"] = "application/pdf,image/*"

    def clean_skan(self):
        return sprawdz_plik(self.cleaned_data.get("skan"))


class PozycjaZakresuForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PozycjaZakresu
        fields = ["nazwa", "opis", "jednostka", "ilosc", "cena_netto"]
        widgets = {"opis": forms.Textarea(attrs={"rows": 1})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for pole in ("ilosc", "cena_netto"):
            self.fields[pole].widget.attrs.update({"inputmode": "decimal", "step": "0.01"})


ZakresFormSet = inlineformset_factory(Budowa, PozycjaZakresu, form=PozycjaZakresuForm, extra=0, can_delete=True)
