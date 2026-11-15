from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from apps.budowy.models import ETAPY_AKTYWNE, Etap
from apps.konta import uprawnienia as u

from .zadania import zadania_budow


class CoDzisView(LoginRequiredMixin, TemplateView):
    template_name = "pulpit/co_dzis.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        dzis = timezone.localdate()
        ctx["dzis"] = dzis
        widzi_bhp = u.moze_widziec(user, "bhp")

        if u.moze_widziec(user, "budowy"):
            budowy = u.budowy_dla(user)
            ctx["zadania_budow"] = zadania_budow(budowy, dzis, z_bhp=widzi_bhp)
            ctx["liczba_aktywnych"] = budowy.filter(etap__in=ETAPY_AKTYWNE).count()
            ctx["liczba_ofert"] = budowy.filter(etap=Etap.OFERTA).count()
            if u.KIEROWNIK in u.role(user):
                ctx["moje_budowy"] = budowy.filter(kierownik=user).exclude(etap=Etap.ZAKONCZONA).select_related("klient")

        if widzi_bhp:
            from apps.bhp.alerty import alerty_bhp

            alerty = alerty_bhp(dzis)
            ctx["alerty_pilne"] = [a for a in alerty if a.status.kod in ("wygasl", "brak", "pilne")]
            ctx["alerty_wkrotce"] = [a for a in alerty if a.status.kod == "wkrotce"]
            # Najważniejsze: problemy ludzi i sprzętu, którzy są TERAZ na aktywnych budowach.
            ctx["alerty_na_budowach"] = sum(1 for a in ctx["alerty_pilne"] if a.budowy)
        return ctx
