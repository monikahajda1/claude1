from django import forms


class BootstrapMixin:
    """Nadaje polom formularza wygląd Bootstrapa i kalendarz dla dat."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for pole in self.fields.values():
            w = pole.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")
            elif isinstance(w, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
                pass
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "form-select")
            else:
                w.attrs.setdefault("class", "form-control")


class PoleDaty(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%Y-%m-%d")
