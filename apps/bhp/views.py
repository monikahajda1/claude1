"""Widoki modułu BHP. Pracownik i sprzęt działają tak samo, więc mają wspólne klasy bazowe."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from apps.core.mixins import KomunikatZapisuMixin, ModulMixin

from .alerty import alerty_bhp, stan_dokumentow
from .forms import DokumentPracownikaForm, DokumentSprzetuForm, PracownikForm, SprzetForm
from .models import DokumentPracownika, DokumentSprzetu, Dotyczy, Pracownik, Sprzet, TypDokumentu

# Konfiguracja obu rodzajów „właścicieli dokumentów”.
RODZAJE = {
    "pracownik": {
        "model": Pracownik,
        "form": PracownikForm,
        "dok_model": DokumentPracownika,
        "dok_form": DokumentPracownikaForm,
        "dotyczy": Dotyczy.PRACOWNIK,
        "pole": "pracownik",
        "url": "bhp:pracownik",
        "lista_url": "bhp:pracownicy",
        "tytul_listy": "Pracownicy",
        "nowy": "Nowy pracownik",
        "szukaj": ["imie", "nazwisko", "stanowisko", "firma"],
    },
    "sprzet": {
        "model": Sprzet,
        "form": SprzetForm,
        "dok_model": DokumentSprzetu,
        "dok_form": DokumentSprzetuForm,
        "dotyczy": Dotyczy.SPRZET,
        "pole": "sprzet",
        "url": "bhp:sprzet",
        "lista_url": "bhp:sprzety",
        "tytul_listy": "Sprzęt",
        "nowy": "Nowy sprzęt",
        "szukaj": ["nazwa", "numer_ewidencyjny", "producent_model"],
    },
}

for _rodzaj, _cfg in RODZAJE.items():
    _cfg.update(
        nowy_url=f"bhp:{_rodzaj}_nowy",
        edytuj_url=f"bhp:{_rodzaj}_edytuj",
        dok_nowy_url=f"bhp:{_rodzaj}_dokument_nowy",
        dok_edytuj_url=f"bhp:{_rodzaj}_dokument_edytuj",
        dok_usun_url=f"bhp:{_rodzaj}_dokument_usun",
    )


class RodzajMixin(ModulMixin):
    modul = "bhp"
    rodzaj = None

    @property
    def cfg(self):
        return RODZAJE[self.rodzaj]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rodzaj"] = self.rodzaj
        ctx["cfg"] = self.cfg
        return ctx


class ListaView(RodzajMixin, ListView):
    template_name = "bhp/lista.html"
    paginate_by = 50

    def get_paginate_by(self, queryset):
        # Filtr „tylko z problemami” liczony jest w Pythonie – wtedy pokazujemy wszystko na jednej stronie.
        return None if self.request.GET.get("problemy") == "1" else self.paginate_by

    def get_queryset(self):
        qs = self.cfg["model"].objects.prefetch_related("dokumenty", "budowy")
        self.pokaz = self.request.GET.get("pokaz", "aktywni")
        if self.pokaz == "aktywni":
            qs = qs.filter(aktywny=True)
        elif self.pokaz == "nieaktywni":
            qs = qs.filter(aktywny=False)
        q = self.request.GET.get("q", "").strip()
        if q:
            warunek = Q()
            for pole in self.cfg["szukaj"]:
                warunek |= Q(**{f"{pole}__icontains": q})
            qs = qs.filter(warunek)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        typy = list(TypDokumentu.objects.filter(dotyczy=self.cfg["dotyczy"]))
        tylko_problemy = self.request.GET.get("problemy") == "1"
        wiersze = []
        for obiekt in ctx["object_list"]:
            stan = stan_dokumentow(obiekt, typy)
            problemy = [s for s in stan if s[2].alert]
            if tylko_problemy and not problemy:
                continue
            najgorszy = min((s[2] for s in problemy), key=lambda st: st.waga, default=None)
            wiersze.append({"obiekt": obiekt, "problemy": problemy, "najgorszy": najgorszy})
        ctx.update(wiersze=wiersze, q=self.request.GET.get("q", ""), pokaz=self.pokaz, tylko_problemy=tylko_problemy)
        return ctx


class SzczegolyView(RodzajMixin, DetailView):
    template_name = "bhp/szczegoly.html"

    def get_queryset(self):
        return self.cfg["model"].objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        typy = list(TypDokumentu.objects.filter(dotyczy=self.cfg["dotyczy"]))
        ctx["stan"] = stan_dokumentow(self.object, typy)
        ctx["dokumenty"] = self.object.dokumenty.select_related("typ").order_by("typ__kolejnosc", "-data_waznosci")
        aktualne_id = {d.pk for _, d, _ in ctx["stan"] if d is not None}
        ctx["aktualne_id"] = aktualne_id
        ctx["budowy"] = self.object.budowy.all()
        ctx["historia"] = self.object.history.select_related("history_user")[:10]
        return ctx


class ObiektFormMixin(RodzajMixin, KomunikatZapisuMixin):
    edycja = True
    template_name = "bhp/formularz.html"

    def get_form_class(self):
        return self.cfg["form"]

    def get_queryset(self):
        return self.cfg["model"].objects.all()


class NowyView(ObiektFormMixin, CreateView):
    komunikat = "Dodano. Teraz dodaj dokumenty (badania, szkolenia, przeglądy)."


class EdytujView(ObiektFormMixin, UpdateView):
    pass


class DokumentMixin(RodzajMixin, KomunikatZapisuMixin):
    edycja = True
    template_name = "bhp/dokument_formularz.html"

    def get_form_class(self):
        return self.cfg["dok_form"]

    def wlasciciel(self):
        return get_object_or_404(self.cfg["model"], pk=self.kwargs["wlasciciel_pk"])

    def get_queryset(self):
        return self.cfg["dok_model"].objects.filter(**{f"{self.cfg['pole']}_id": self.kwargs["wlasciciel_pk"]})

    def get_success_url(self):
        return self.object.wlasciciel.get_absolute_url()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["wlasciciel"] = self.wlasciciel()
        ctx["okresy"] = {t.pk: t.okres_miesiecy for t in TypDokumentu.objects.filter(dotyczy=self.cfg["dotyczy"])}
        return ctx


class DokumentNowyView(DokumentMixin, CreateView):
    komunikat = "Dodano dokument."

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("typ"):
            initial["typ"] = self.request.GET["typ"]
        return initial

    def form_valid(self, form):
        setattr(form.instance, self.cfg["pole"], self.wlasciciel())
        return super().form_valid(form)


class DokumentEdytujView(DokumentMixin, UpdateView):
    komunikat = "Zapisano dokument."


class DokumentUsunView(DokumentMixin, DeleteView):
    template_name = "bhp/dokument_usun.html"

    def form_valid(self, form):
        url = self.get_success_url()
        self.object.delete()
        messages.success(self.request, "Usunięto dokument.")
        return redirect(url)


class AlertyView(ModulMixin, TemplateView):
    """Pełna lista problemów z dokumentami – do wydruku lub przeglądu."""

    modul = "bhp"
    template_name = "bhp/alerty.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["alerty"] = alerty_bhp()
        return ctx
