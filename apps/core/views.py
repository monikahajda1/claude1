import mimetypes
from itertools import islice
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from apps.konta import uprawnienia

from .mixins import ModulMixin

# Katalog w przesłanych plikach -> moduł, którego uprawnienia są potrzebne.
# Skany umów i dokumenty budów (katalogi „umowy”, „wejscie”) NIE są tu wymienione celowo – wydaje je widok umowy, który sprawdza też,
# czy użytkownik ma dostęp do konkretnej budowy (kierownik – tylko swoich).
MODUL_KATALOGU = {"bhp": "bhp", "szablony": "ustawienia", "materialy": "materialy", "firma": "firma"}


@login_required
def pobierz_plik(request, sciezka):
    """Wydaje przesłany plik (skan, zdjęcie) – tylko osobom z uprawnieniami."""
    katalog = sciezka.split("/", 1)[0]
    modul = MODUL_KATALOGU.get(katalog)
    if modul is None or not uprawnienia.moze_widziec(request.user, modul):
        raise PermissionDenied
    root = Path(settings.MEDIA_ROOT).resolve()
    plik = (root / sciezka).resolve()
    if root not in plik.parents or not plik.is_file():
        raise Http404
    typ, _ = mimetypes.guess_type(plik.name)
    return FileResponse(open(plik, "rb"), content_type=typ or "application/octet-stream")


def manifest(request):
    """Opis aplikacji PWA – dzięki niemu można ją „zainstalować” na telefonie."""
    import json

    dane = {
        "name": settings.NAZWA_APLIKACJI,
        "short_name": "Budowy",
        "lang": "pl",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1f4e79",
        "icons": [
            {"src": static("ikony/ikona-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("ikony/ikona-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": static("ikony/ikona-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return HttpResponse(json.dumps(dane, ensure_ascii=False), content_type="application/manifest+json")


@never_cache
def service_worker(request):
    """Skrypt PWA – musi być pod adresem głównym, by obejmować całą aplikację."""
    return render(request, "pwa/sw.js", {"offline_url": "/offline/"}, content_type="application/javascript")


def offline(request):
    return render(request, "pwa/offline.html")


SYMBOL_ZMIANY = {"+": ("dodano", "success"), "~": ("zmieniono", "primary"), "-": ("usunięto", "danger")}


def _modele_z_historia():
    for model in apps.get_models():
        if hasattr(model, "history") and not model.__name__.startswith("Historical"):
            yield model


class DziennikZmianView(ModulMixin, TemplateView):
    """Kto, co i kiedy zmienił – ostatnie wpisy ze wszystkich części aplikacji."""

    modul = "dziennik"
    template_name = "core/dziennik.html"
    LIMIT = 200

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        wybrany_model = self.request.GET.get("model", "")
        wybrany_user = self.request.GET.get("kto", "")
        modele = list(_modele_z_historia())
        wpisy = []
        for model in modele:
            if wybrany_model and model._meta.label_lower != wybrany_model:
                continue
            qs = model.history.select_related("history_user").order_by("-history_date")
            if wybrany_user:
                qs = qs.filter(history_user__username=wybrany_user)
            wpisy.extend(islice(qs, self.LIMIT))
        wpisy.sort(key=lambda r: r.history_date, reverse=True)
        wiersze = []
        for r in wpisy[: self.LIMIT]:
            zmiany = []
            if r.history_type == "~":
                poprzedni = r.prev_record
                if poprzedni is not None:
                    for c in r.diff_against(poprzedni).changes:
                        pole = r.instance_type._meta.get_field(c.field)
                        zmiany.append((pole.verbose_name, c.old, c.new))
            opis, kolor = SYMBOL_ZMIANY.get(r.history_type, ("?", "secondary"))
            wiersze.append(
                {
                    "kiedy": r.history_date,
                    "kto": r.history_user,
                    "co": r.instance_type._meta.verbose_name,
                    "obiekt": str(r.instance) if r.history_type != "-" else str(r.history_object),
                    "opis": opis,
                    "kolor": kolor,
                    "zmiany": zmiany,
                }
            )
        from apps.konta.models import Uzytkownik

        ctx.update(
            wiersze=wiersze,
            modele=sorted(((m._meta.label_lower, m._meta.verbose_name_plural) for m in modele), key=lambda x: x[1]),
            uzytkownicy=Uzytkownik.objects.all(),
            wybrany_model=wybrany_model,
            wybrany_user=wybrany_user,
            limit=self.LIMIT,
        )
        return ctx
