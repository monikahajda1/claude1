from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.mixins import KomunikatZapisuMixin, ModulMixin
from apps.konta import uprawnienia as u

from .forms import BudowaForm, BudowaKierownikForm, KlientForm, ZespolBudowyForm
from .models import ETAPY_AKTYWNE, Budowa, Etap, Klient

WIDOKI_LISTY = {
    "w-toku": ("W toku", ~Q(etap__in=[Etap.ZAKONCZONA])),
    "aktywne": ("Na budowie", Q(etap__in=ETAPY_AKTYWNE)),
    "zakonczone": ("Zakończone", Q(etap=Etap.ZAKONCZONA)),
    "wszystkie": ("Wszystkie", Q()),
}


class BudowaListView(ModulMixin, ListView):
    modul = "budowy"
    template_name = "budowy/lista.html"
    paginate_by = 25

    def get_queryset(self):
        qs = u.budowy_dla(self.request.user).select_related("klient", "kierownik")
        self.widok = self.request.GET.get("widok", "w-toku")
        if self.widok not in WIDOKI_LISTY:
            self.widok = "w-toku"
        qs = qs.filter(WIDOKI_LISTY[self.widok][1])
        etap = self.request.GET.get("etap")
        if etap in Etap.values:
            qs = qs.filter(etap=etap)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nazwa__icontains=q) | Q(numer__icontains=q) | Q(adres__icontains=q)
                | Q(miasto__icontains=q) | Q(klient__nazwa__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        widoczne = u.budowy_dla(self.request.user)
        liczniki = widoczne.aggregate(**{k: Count("pk", filter=v[1]) for k, v in WIDOKI_LISTY.items()})
        ctx.update(
            widoki=[(k, v[0], liczniki[k]) for k, v in WIDOKI_LISTY.items()],
            widok=self.widok,
            etapy=Etap.choices,
            etap=self.request.GET.get("etap", ""),
            q=self.request.GET.get("q", ""),
            moze_dodac=u.moze_edytowac(self.request.user, "klienci"),
        )
        return ctx


class BudowaDetailView(ModulMixin, DetailView):
    modul = "budowy"
    template_name = "budowy/szczegoly.html"

    def get_queryset(self):
        return u.budowy_dla(self.request.user).select_related("klient", "kierownik")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        b = self.object
        ctx["moze_edytowac"] = u.moze_edytowac_budowe(user, b)
        ctx["widzi_bhp"] = u.moze_widziec(user, "bhp")
        ctx["edytuje_bhp"] = u.moze_edytowac(user, "bhp")
        ctx["widzi_klienta"] = u.moze_widziec(user, "klienci")
        if ctx["widzi_bhp"]:
            from apps.bhp.alerty import alerty_bhp

            alerty = alerty_bhp(pracownicy=b.pracownicy.all(), sprzet=b.sprzet.all())
            ctx["alerty_bhp"] = alerty
            problemy = {}
            for a in alerty:
                problemy.setdefault((a.rodzaj, a.obiekt.pk), []).append(a)
            ctx["pracownicy"] = [(p, problemy.get(("pracownik", p.pk), [])) for p in b.pracownicy.all()]
            ctx["sprzet"] = [(s, problemy.get(("sprzet", s.pk), [])) for s in b.sprzet.all()]
        if u.moze_widziec(user, "umowy"):
            from apps.umowy.models import Umowa
            from apps.umowy.operacje import suma_zakresu

            ctx["widzi_umowe"] = True
            ctx["edytuje_umowe"] = u.moze_edytowac(user, "umowy")
            ctx["umowa"] = Umowa.objects.filter(budowa=b).prefetch_related("aneksy").first()
            ctx["zakres"] = list(b.zakres.all())
            ctx["suma_zakresu"] = suma_zakresu(b)
            if ctx["umowa"]:
                ctx["roznica_zakresu"] = ctx["umowa"].wartosc_aktualna - ctx["suma_zakresu"]
            if u.moze_widziec(user, "oferty"):
                ctx["oferty"] = b.oferty.all()
        ctx["historia"] = b.history.select_related("history_user")[:10]
        return ctx


class BudowaCreateView(ModulMixin, KomunikatZapisuMixin, CreateView):
    modul = "klienci"  # zakładać budowy może ten, kto edytuje klientów (admin, handlowiec)
    edycja = True
    model = Budowa
    form_class = BudowaForm
    template_name = "budowy/formularz.html"
    komunikat = "Dodano budowę."

    def get_initial(self):
        initial = super().get_initial()
        if "klient" in self.request.GET:
            initial["klient"] = self.request.GET["klient"]
        return initial


class BudowaUpdateView(ModulMixin, KomunikatZapisuMixin, UpdateView):
    modul = "budowy"
    edycja = True
    template_name = "budowy/formularz.html"

    def get_queryset(self):
        return u.budowy_dla(self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not u.moze_edytowac_budowe(self.request.user, obj):
            raise PermissionDenied
        return obj

    def get_form_class(self):
        if u.role(self.request.user) & {u.ADMINISTRATOR, u.HANDLOWIEC}:
            return BudowaForm
        return BudowaKierownikForm


class ZespolBudowyView(ModulMixin, KomunikatZapisuMixin, UpdateView):
    modul = "bhp"
    edycja = True
    model = Budowa
    form_class = ZespolBudowyForm
    template_name = "budowy/zespol.html"
    komunikat = "Zapisano skład ekipy i sprzęt."


class KlientListView(ModulMixin, ListView):
    modul = "klienci"
    template_name = "budowy/klienci.html"
    paginate_by = 50

    def get_queryset(self):
        qs = Klient.objects.annotate(liczba_budow=Count("budowy"))
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nazwa__icontains=q) | Q(nip__icontains=q) | Q(osoba_kontaktowa__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class KlientCreateView(ModulMixin, KomunikatZapisuMixin, CreateView):
    modul = "klienci"
    edycja = True
    model = Klient
    form_class = KlientForm
    template_name = "budowy/klient_formularz.html"
    success_url = reverse_lazy("budowy:klienci")
    komunikat = "Dodano klienta."


class KlientUpdateView(ModulMixin, KomunikatZapisuMixin, UpdateView):
    """Karta klienta: osoby z prawem podglądu widzą dane, z prawem edycji – mogą je zmienić."""

    modul = "klienci"
    model = Klient
    form_class = KlientForm
    template_name = "budowy/klient_formularz.html"
    success_url = reverse_lazy("budowy:klienci")
    komunikat = "Zapisano dane klienta."

    def post(self, request, *args, **kwargs):
        if not u.moze_edytowac(request.user, "klienci"):
            raise PermissionDenied
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["budowy"] = u.budowy_dla(self.request.user).filter(klient=self.object)
        if u.moze_widziec(self.request.user, "oferty"):
            ctx["oferty"] = self.object.oferty.filter(aktualna=True).select_related("handlowiec")
        return ctx
