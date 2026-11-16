import io
import mimetypes
import zipfile

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.utils.http import content_disposition_header
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from apps.core.mixins import KomunikatZapisuMixin, ModulMixin
from apps.konta import uprawnienia as u
from apps.materialy.models import KOLEJNOSC_TYPOW, Material, MaterialBudowy
from apps.materialy.operacje import materialy_z_zakresu, uzupelnij_z_zakresu
from apps.szablony.generator import generuj

from .checklista import checklista, podsumowanie
from .dokumenty import kontekst_ibwr, kontekst_kzm
from .forms import DokumentFirmyForm, IBWRForm, KZMForm, OdhaczenieForm
from .models import IBWR, KZM, DokumentFirmy, OdhaczeniePunktu, PunktChecklisty

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def word(rodzaj, kontekst, nazwa, request, powrot):
    try:
        tresc = generuj(rodzaj, kontekst)
    except ValidationError as e:
        messages.error(request, " ".join(e.messages) + " Popraw szablon w Administracji → Szablony dokumentów.")
        return redirect(powrot)
    odp = HttpResponse(tresc, content_type=DOCX)
    odp["Content-Disposition"] = content_disposition_header(True, f"{nazwa}")
    return odp


def bezpieczna(tekst):
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in tekst)


class BudowaMixin(ModulMixin):
    """Budowa z adresu – tylko jeśli użytkownik ma do niej dostęp (kierownik: swoje)."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.budowa = get_object_or_404(u.budowy_dla(request.user), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)


class BudowaWejscieView(BudowaMixin, TemplateView):
    """Strona „Wejście na budowę”: checklista, materiały i KZM, IBWR."""

    modul = "checklista"
    template_name = "wejscie/budowa.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        b = self.budowa
        user = self.request.user
        punkty = checklista(b, user=user)
        kzm_wg_materialu = {}
        for k in b.kzm.select_related("material").order_by("utworzono"):
            kzm_wg_materialu[k.material_id] = k  # najnowsza wygrywa
        wiersze = []
        for mb in b.materialy.select_related("material").prefetch_related("material__dokumenty"):
            wiersze.append({"mb": mb, "m": mb.material, "braki": mb.material.brakujace_typy(), "kzm": kzm_wg_materialu.get(mb.material_id)})
        try:
            ibwr = b.ibwr
        except ObjectDoesNotExist:
            ibwr = None
        uzyte = set(b.materialy.values_list("material_id", flat=True))
        ctx.update(
            budowa=b, punkty=punkty, suma=podsumowanie(punkty), wiersze=wiersze, ibwr=ibwr,
            do_dodania=Material.objects.filter(aktywny=True).exclude(pk__in=uzyte),
            nowe_z_zakresu=materialy_z_zakresu(b).exclude(pk__in=uzyte).count(),
            edytuje_kzm=u.moze_edytowac(user, "kzm"), edytuje_check=u.moze_edytowac(user, "checklista"),
            widzi_ibwr=u.moze_widziec(user, "ibwr"), widzi_kzm=u.moze_widziec(user, "kzm"),
            odhacz_form=OdhaczenieForm(),
        )
        return ctx


class MaterialyAkcjaView(BudowaMixin, View):
    modul = "kzm"
    edycja = True

    def post(self, request, pk):
        b = self.budowa
        akcja = request.POST.get("akcja")
        if akcja == "uzupelnij":
            n = uzupelnij_z_zakresu(b)
            messages.success(request, f"Dodano {n} materiał(y) z zakresu prac." if n else "Lista materiałów jest już aktualna.")
        elif akcja == "dodaj":
            m = get_object_or_404(Material, pk=request.POST.get("material"), aktywny=True)
            mb, utw = MaterialBudowy.objects.get_or_create(budowa=b, material=m, defaults={"dodany_recznie": True})
            if not utw and mb.wykluczony:
                mb.wykluczony = False
                mb.save()
            messages.success(request, f"Dodano materiał: {m.nazwa}.")
        elif akcja in ("wyklucz", "przywroc"):
            mb = get_object_or_404(MaterialBudowy, pk=request.POST.get("mb"), budowa=b)
            mb.wykluczony = akcja == "wyklucz"
            mb.save()
            messages.success(request, ("Oznaczono jako nieużywany: " if mb.wykluczony else "Przywrócono: ") + mb.material.nazwa)
        return redirect("wejscie:budowa", b.pk)


class KZMUtworzView(BudowaMixin, View):
    modul = "kzm"
    edycja = True

    def post(self, request, pk):
        mb = get_object_or_404(MaterialBudowy, pk=request.POST.get("mb"), budowa=self.budowa)
        kzm = KZM.objects.create(budowa=self.budowa, material=mb.material, zastosowanie=mb.material.zastosowanie)
        messages.success(request, f"Utworzono {kzm.numer}. Pobierz kartę i paczkę dokumentów, a po złożeniu zmień status.")
        return redirect(kzm)


class KZMMixin(ModulMixin):
    modul = "kzm"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.kzm = get_object_or_404(KZM.objects.select_related("budowa", "material"), pk=kwargs["pk"])
            if not u.budowy_dla(request.user).filter(pk=self.kzm.budowa_id).exists():
                raise Http404
        return super().dispatch(request, *args, **kwargs)


class KZMView(KZMMixin, TemplateView):
    template_name = "wejscie/kzm.html"

    def formularz(self, data=None, files=None):
        return KZMForm(data, files, instance=self.kzm)

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.kontekst(self.formularz()))

    def post(self, request, *args, **kwargs):
        if not u.moze_edytowac(request.user, "kzm"):
            raise PermissionDenied
        form = self.formularz(request.POST, request.FILES)
        if form.is_valid():
            kzm = form.save(commit=False)
            dzis = timezone.localdate()
            if kzm.status != "przygotowana" and not kzm.data_zlozenia:
                kzm.data_zlozenia = dzis
            if kzm.status in ("zatwierdzona", "z_uwagami", "odrzucona") and not kzm.data_decyzji:
                kzm.data_decyzji = dzis
            kzm.save()
            messages.success(request, f"Zapisano {kzm.numer}: {kzm.get_status_display()}.")
            return redirect("wejscie:budowa", kzm.budowa_id)
        return self.render_to_response(self.kontekst(form))

    def kontekst(self, form):
        m = self.kzm.material
        aktualne = m.aktualne_dokumenty()
        return self.get_context_data(
            kzm=self.kzm, form=form, edytuje=u.moze_edytowac(self.request.user, "kzm"),
            zalaczniki=[aktualne[t] for t in KOLEJNOSC_TYPOW if t in aktualne], braki=m.brakujace_typy(),
            historia=self.kzm.history.select_related("history_user")[:10],
        )


class KZMDokumentView(KZMMixin, View):
    def get(self, request, pk):
        return word("kzm", kontekst_kzm(self.kzm), f"{bezpieczna(self.kzm.numer)}.docx", request, self.kzm)


class KZMZipView(KZMMixin, View):
    """Paczka ZIP z aktualnymi dokumentami materiału (bez samej karty KZM)."""

    def get(self, request, pk):
        m = self.kzm.material
        aktualne = m.aktualne_dokumenty()
        dokumenty = [aktualne[t] for t in KOLEJNOSC_TYPOW if t in aktualne]
        if not dokumenty:
            messages.error(request, "Materiał nie ma jeszcze żadnych dokumentów – wgraj je w module Materiały.")
            return redirect(self.kzm)
        bufor = io.BytesIO()
        with zipfile.ZipFile(bufor, "w", zipfile.ZIP_DEFLATED) as z:
            for nr, d in enumerate(dokumenty, 1):
                with d.plik.open("rb") as f:
                    z.writestr(d.nazwa_pliku(nr), f.read())
        odp = HttpResponse(bufor.getvalue(), content_type="application/zip")
        odp["Content-Disposition"] = content_disposition_header(True, f"Dokumenty_{bezpieczna(m.nazwa)}.zip")
        return odp


class IBWRView(BudowaMixin, TemplateView):
    modul = "ibwr"
    template_name = "wejscie/ibwr.html"

    def instancja(self):
        try:
            return self.budowa.ibwr
        except ObjectDoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.kontekst(IBWRForm(instance=self.instancja())))

    def post(self, request, *args, **kwargs):
        if not u.moze_edytowac(request.user, "ibwr"):
            raise PermissionDenied
        form = IBWRForm(request.POST, request.FILES, instance=self.instancja())
        if form.is_valid():
            ibwr = form.save(commit=False)
            ibwr.budowa = self.budowa
            if not ibwr.opracowal_id:
                ibwr.opracowal = request.user
            ibwr.save()
            form.save_m2m()
            messages.success(request, f"Zapisano IBWR ({ibwr.get_status_display()}).")
            if "pobierz" in request.POST:
                return redirect("wejscie:ibwr_dokument", self.budowa.pk)
            return redirect("wejscie:budowa", self.budowa.pk)
        return self.render_to_response(self.kontekst(form))

    def kontekst(self, form):
        return self.get_context_data(budowa=self.budowa, form=form, ibwr=self.instancja(), edytuje=u.moze_edytowac(self.request.user, "ibwr"))


class IBWRDokumentView(BudowaMixin, View):
    modul = "ibwr"

    def get(self, request, pk):
        try:
            ibwr = self.budowa.ibwr
        except ObjectDoesNotExist:
            messages.error(request, "Najpierw zapisz IBWR (wybierz zagrożenia).")
            return redirect("wejscie:ibwr", pk)
        return word("ibwr", kontekst_ibwr(ibwr), f"IBWR_{bezpieczna(self.budowa.numer)}.docx", request, self.budowa)


class OdhaczView(BudowaMixin, View):
    modul = "checklista"
    edycja = True

    def post(self, request, pk, ppk):
        punkt = get_object_or_404(PunktChecklisty, pk=ppk)
        obiekt, _ = OdhaczeniePunktu.objects.get_or_create(budowa=self.budowa, punkt=punkt)
        form = OdhaczenieForm(request.POST, request.FILES, instance=obiekt)
        if form.is_valid():
            o = form.save(commit=False)
            o.kto = request.user
            o.data = timezone.localdate() if (o.zrobione or o.nie_dotyczy) else None
            o.save()
            messages.success(request, f"Zapisano: {punkt.nazwa}.")
        else:
            messages.error(request, "Nie zapisano: " + " ".join(" ".join(v) for v in form.errors.values()))
        return redirect("wejscie:budowa", self.budowa.pk)


class PlikView(ModulMixin, View):
    """Skany KZM / IBWR / załączniki checklisty – tylko dla osób z dostępem do budowy."""

    modul = "checklista"
    MODELE = {"kzm": (KZM, "skan", "kzm"), "ibwr": (IBWR, "skan", "ibwr"), "punkt": (OdhaczeniePunktu, "plik", "checklista")}

    def get(self, request, rodzaj, pk):
        if rodzaj not in self.MODELE:
            raise Http404
        model, pole, modul = self.MODELE[rodzaj]
        if not u.moze_widziec(request.user, modul):
            raise PermissionDenied
        obiekt = get_object_or_404(model, pk=pk)
        if not u.budowy_dla(request.user).filter(pk=obiekt.budowa_id).exists():
            raise Http404
        plik = getattr(obiekt, pole)
        if not plik:
            raise Http404
        typ, _ = mimetypes.guess_type(plik.name)
        return FileResponse(plik.open("rb"), content_type=typ or "application/octet-stream")


# --- Dokumenty firmy ---

class FirmaListView(ModulMixin, ListView):
    modul = "firma"
    model = DokumentFirmy
    template_name = "wejscie/firma.html"


class FirmaNowyView(ModulMixin, KomunikatZapisuMixin, CreateView):
    modul = "firma"
    edycja = True
    model = DokumentFirmy
    form_class = DokumentFirmyForm
    template_name = "wejscie/firma_formularz.html"
    success_url = reverse_lazy("wejscie:firma")
    komunikat = "Dodano dokument firmy."


class FirmaEdytujView(ModulMixin, KomunikatZapisuMixin, UpdateView):
    modul = "firma"
    edycja = True
    model = DokumentFirmy
    form_class = DokumentFirmyForm
    template_name = "wejscie/firma_formularz.html"
    success_url = reverse_lazy("wejscie:firma")
