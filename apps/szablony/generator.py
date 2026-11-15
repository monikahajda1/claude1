"""Wypełnianie szablonów Word (biblioteka docxtpl).

W szablonie wpisuje się pola w podwójnych nawiasach, np. {{ klient }}.
Listę pól dla każdego rodzaju dokumentu pokazuje strona „Pola szablonu”.
"""

import io
from pathlib import Path

from django.core.exceptions import ValidationError
from docxtpl import DocxTemplate
from jinja2 import TemplateSyntaxError, UndefinedError

from .models import SzablonDokumentu

WBUDOWANE = Path(__file__).resolve().parent / "wbudowane"


def plik_szablonu(rodzaj):
    """Najnowszy aktywny szablon użytkownika albo szablon wbudowany."""
    wlasny = SzablonDokumentu.objects.filter(rodzaj=rodzaj, aktywny=True).order_by("-dodano").first()
    if wlasny:
        return wlasny.plik.path
    return str(WBUDOWANE / f"{rodzaj}.docx")


def wypelnij(sciezka, kontekst):
    """Zwraca gotowy dokument jako bajty. Błędy w szablonie zamienia na zrozumiały komunikat."""
    try:
        dok = DocxTemplate(sciezka)
        dok.render(kontekst, autoescape=True)
    except TemplateSyntaxError as e:
        raise ValidationError(f"Błąd w szablonie Word (linia {e.lineno}): {e.message}. Sprawdź nawiasy {{{{ }}}} i {{% %}}.")
    except UndefinedError as e:
        raise ValidationError(f"Szablon używa pola, którego nie ma: {e.message}")
    bufor = io.BytesIO()
    dok.save(bufor)
    return bufor.getvalue()


def generuj(rodzaj, kontekst):
    return wypelnij(plik_szablonu(rodzaj), kontekst)
