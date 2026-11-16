from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.mixins import KomunikatZapisuMixin, ModulMixin
from apps.konta import uprawnienia as u

from .forms import DokumentMaterialuForm, MaterialForm
from .models import KOLEJNOSC_TYPOW, DokumentMaterialu, Material, RodzajMaterialu, TypDokumentuMaterialu


class ListaView(ModulMixin, ListView):
    modul = "materialy"
    template_name = "materialy/lista.html"

    def get_queryset(self):
        qs = Material.objects.prefetch_related("dokumenty", "systemy")
        if self.request.GET.get("pokaz") != "wszystkie":
            qs = qs.filter(aktywny=True)
        if self.request.GET.get("rodzaj") in RodzajMaterialu.values:
            qs = qs.filter(rodzaj=self.request.GET["rodzaj"])
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nazwa__icontains=q) | Q(producent__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(rodzaje=RodzajMaterialu.choices, rodzaj=self.request.GET.get("rodzaj", ""),
                   q=self.request.GET.get("q", ""), pokaz=self.request.GET.get("pokaz", ""))
        return ctx


class SzczegolyView(ModulMixin, DetailView):
    modul = "materialy"
    model = Material
    template_name = "materialy/szczegoly.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        m = self.object
        aktualne = m.aktualne_dokumenty()
        ctx["aktualne"] = [(TypDokumentuMaterialu(t).label, aktualne.get(t)) for t in KOLEJNOSC_TYPOW if t in aktualne or t != "inny"]
        ctx["aktualne_id"] = {d.pk for d in aktualne.values()}
        ctx["dokumenty"] = m.dokumenty.all()
        ctx["form"] = DokumentMaterialuForm()
        ctx["budowy"] = u.budowy_dla(self.request.user).filter(materialy__material=m, materialy__wykluczony=False).distinct()
        ctx["historia"] = m.history.select_related("history_user")[:10]
        return ctx


class NowyView(ModulMixin, KomunikatZapisuMixin, CreateView):
    modul = "materialy"
    edycja = True
    model = Material
    form_class = MaterialForm
    template_name = "materialy/formularz.html"
    komunikat = "Dodano materiał. Teraz wgraj jego dokumenty."


class EdytujView(ModulMixin, KomunikatZapisuMixin, UpdateView):
    modul = "materialy"
    edycja = True
    model = Material
    form_class = MaterialForm
    template_name = "materialy/formularz.html"


class DokumentDodajView(ModulMixin, View):
    modul = "materialy"
    edycja = True

    def post(self, request, pk):
        m = get_object_or_404(Material, pk=pk)
        form = DokumentMaterialuForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.save(commit=False)
            d.material = m
            d.save()
            messages.success(request, f"Dodano: {d.get_typ_display()}. Poprzednia wersja (jeśli była) zostaje w archiwum.")
        else:
            messages.error(request, "Nie dodano dokumentu: " + " ".join(" ".join(v) for v in form.errors.values()))
        return redirect(m)


class DokumentUsunView(ModulMixin, View):
    modul = "materialy"
    edycja = True

    def post(self, request, pk, dpk):
        d = get_object_or_404(DokumentMaterialu, pk=dpk, material_id=pk)
        d.delete()
        messages.success(request, "Usunięto dokument.")
        return redirect(d.material)
