from django.utils.http import content_disposition_header
from django.http import FileResponse, Http404, HttpResponse
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import ModulMixin
from apps.konta import uprawnienia as u

from .generator import WBUDOWANE, generuj
from .models import Rodzaj, SzablonDokumentu
from .pola import OPISY_POL, PRZYKLADY

# Kto może oglądać pola i pobierać wzory danego rodzaju szablonu.
MODUL_RODZAJU = {"oferta": "oferty", "kzm": "kzm", "ibwr": "ibwr"}

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class RodzajMixin(ModulMixin):
    modul = "ustawienia"

    def dispatch(self, request, *args, **kwargs):
        rodzaj = kwargs["rodzaj"]
        if rodzaj not in Rodzaj.values:
            raise Http404
        self.rodzaj = rodzaj
        # Dostęp: administrator albo osoby z dostępem do modułu, którego dotyczy szablon.
        if request.user.is_authenticated and u.moze_widziec(request.user, MODUL_RODZAJU.get(rodzaj, "ustawienia")):
            self.modul = MODUL_RODZAJU.get(rodzaj, "ustawienia")
        return super().dispatch(request, *args, **kwargs)


class PolaView(RodzajMixin, TemplateView):
    template_name = "szablony/pola.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            rodzaj=self.rodzaj,
            nazwa_rodzaju=Rodzaj(self.rodzaj).label,
            pola=OPISY_POL[self.rodzaj](),
            aktywny=SzablonDokumentu.objects.filter(rodzaj=self.rodzaj, aktywny=True).order_by("-dodano").first(),
            jest_adminem=u.jest_adminem(self.request.user),
        )
        return ctx


class WzorView(RodzajMixin, View):
    """Pobranie wbudowanego (pustego) szablonu – do przerobienia w Wordzie."""

    def get(self, request, rodzaj):
        plik = WBUDOWANE / f"{rodzaj}.docx"
        return FileResponse(open(plik, "rb"), as_attachment=True, filename=f"wzor_{rodzaj}.docx", content_type=DOCX)


class PrzykladView(RodzajMixin, View):
    """Aktualny szablon wypełniony wymyślonymi danymi – podgląd, jak wygląda."""

    def get(self, request, rodzaj):
        odp = HttpResponse(generuj(rodzaj, PRZYKLADY[rodzaj]()), content_type=DOCX)
        odp["Content-Disposition"] = content_disposition_header(True, f"przyklad_{rodzaj}.docx")
        return odp


