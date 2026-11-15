from django import template

register = template.Library()


@register.filter
def zl(wartosc):
    """Kwota w formacie 12 345,67 zł."""
    if wartosc in (None, ""):
        return "—"
    tekst = f"{wartosc:,.2f}".replace(",", " ").replace(".", ",")
    return f"{tekst} zł"


@register.simple_tag(takes_context=True)
def zamien_param(context, **kwargs):
    """Buduje adres z bieżącymi filtrami, podmieniając wybrane (np. stronę)."""
    params = context["request"].GET.copy()
    for k, v in kwargs.items():
        params[k] = v
    return params.urlencode()
