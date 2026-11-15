from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from apps.konta import uprawnienia


class ModulMixin(LoginRequiredMixin):
    """Wpuszcza tylko osoby z dostępem do modułu.

    modul   – nazwa z uprawnienia.MACIERZ
    edycja  – True dla widoków, które coś zmieniają
    """

    modul = None
    edycja = False

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.edycja:
            ok = uprawnienia.moze_edytowac(request.user, self.modul)
        else:
            ok = uprawnienia.moze_widziec(request.user, self.modul)
        if not ok:
            raise PermissionDenied("Brak uprawnień do tej części aplikacji.")
        return super().dispatch(request, *args, **kwargs)


class KomunikatZapisuMixin:
    komunikat = "Zapisano zmiany."

    def form_valid(self, form):
        odpowiedz = super().form_valid(form)
        messages.success(self.request, self.komunikat)
        return odpowiedz
