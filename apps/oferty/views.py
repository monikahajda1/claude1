from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils.http import content_disposition_header
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.core.mixins import KomunikatZapisuMixin, ModulMixin
from apps.konta import uprawnienia as u
from apps.szablony.generator import generuj

from . import operacje
from .dokument import kontekst_oferty
from .forms import (
    KontaktForm,
    OfertaForm,
    PozycjaCennikaForm,
    PozycjeFormSet,
    RozstrzygniecieForm,
    WariantForm,
    handlowcy,
)
from .models import (
    DNI_DO_KONTAKTU,
    STATUSY_OTWARTE,
    Oferta,
    PozycjaCennika,
    PozycjaOferty,
    RodzajPozycji,
    Status,
    Wariant,
)

# Zakładki listy ofert.
WIDOKI = {
    "otwarte": ("Wysłane i negocjowane", Q(status__in=STATUSY_OTWARTE)),
    "robocze": ("Robocze", Q(status=Status.ROBOCZA)),
    "wygrane": ("Wygrane", Q(status=Status.WYGRANA)),
    "przegrane": ("Przegrane", Q(status=Status.PRZEGRANA)),
    "wszystkie": ("Wszystkie", Q()),
}


def z_wartosciami(qs):
    """Pobiera warianty i pozycje jednym zapytaniem – do liczenia wartości na liście."""
    return qs.select_related("klient", "handlowiec").prefetch_related(
        Prefetch("warianty", queryset=Wariant.objects.prefetch_related("pozycje").select_related("oferta"))
    )


class OfertaListView(ModulMixin, ListView):
    modul = "oferty"
    template_name = "oferty/lista.html"
    paginate_by = 30

    def get_queryset(self):
        qs = Oferta.objects.filter(aktualna=True)
        self.widok = self.request.GET.get("widok", "otwarte")
        if self.widok not in WIDOKI:
            self.widok = "otwarte"
        qs = qs.filter(WIDOKI[self.widok][1])
        self.kto = self.request.GET.get("kto", "")
        if self.kto == "moje":
            qs = qs.filter(handlowiec=self.request.user)
        elif self.kto.isdigit():
            qs = qs.filter(handlowiec_id=int(self.kto))
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(numer__icontains=q) | Q(nazwa__icontains=q) | Q(klient__nazwa__icontains=q)
                | Q(miasto__icontains=q) | Q(adres_budowy__icontains=q)
            )
        if self.widok == "otwarte":
            qs = qs.order_by("nastepny_kontakt", "-data_wystawienia")
        return z_wartosciami(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        aktualne = Oferta.objects.filter(aktualna=True)
        ctx.update(
            widoki=[(k, v[0], aktualne.filter(v[1]).count()) for k, v in WIDOKI.items()],
            widok=self.widok,
            kto=self.kto,
            q=self.request.GET.get("q", ""),
            handlowcy=handlowcy(),
            dzis=timezone.localdate(),
        )
        return ctx


class OfertaDetailView(ModulMixin, DetailView):
    modul = "oferty"
    template_name = "oferty/szczegoly.html"

    def get_queryset(self):
        return z_wartosciami(Oferta.objects.all())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        o = self.object
        warianty = list(o.warianty.all())
        ctx["warianty"] = [(w, w.podsumowanie()) for w in warianty]
        ctx["kontakty"] = o.kontakty.select_related("kto")
        ctx["wersje"] = Oferta.objects.filter(numer=o.numer).order_by("wersja")
        ctx["edytuje"] = u.moze_edytowac(self.request.user, "oferty")
        ctx["edytuje_umowy"] = u.moze_edytowac(self.request.user, "umowy")
        ctx["mozna_zmieniac_pozycje"] = o.status == Status.ROBOCZA and o.aktualna
        ctx["kontakt_form"] = KontaktForm(
            initial={"nastepny_kontakt": timezone.localdate() + timedelta(days=DNI_DO_KONTAKTU)}
        )
        ctx["rozstrzygniecie_form"] = RozstrzygniecieForm(oferta=o)
        ctx["historia"] = o.history.select_related("history_user")[:10]
        return ctx


class OfertaCreateView(ModulMixin, CreateView):
    modul = "oferty"
    edycja = True
    model = Oferta
    form_class = OfertaForm
    template_name = "oferty/formularz.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["handlowiec"] = self.request.user
        if "klient" in self.request.GET:
            initial["klient"] = self.request.GET["klient"]
        return initial

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        wariant = Wariant.objects.create(oferta=self.object, nazwa="Wariant A")
        messages.success(self.request, f"Utworzono ofertę {self.object.pelny_numer}. Teraz dodaj pozycje do kalkulacji.")
        return redirect("oferty:wariant", self.object.pk, wariant.pk)


class OfertaUpdateView(ModulMixin, KomunikatZapisuMixin, UpdateView):
    modul = "oferty"
    edycja = True
    model = Oferta
    form_class = OfertaForm
    template_name = "oferty/formularz.html"


class WariantView(ModulMixin, TemplateView):
    """Kalkulator: pozycje jednego wariantu."""

    modul = "oferty"
    edycja = True
    template_name = "oferty/wariant.html"

    def dispatch(self, request, *args, **kwargs):
        self.oferta = get_object_or_404(Oferta, pk=kwargs["pk"])
        self.wariant = get_object_or_404(Wariant, pk=kwargs["wpk"], oferta=self.oferta)
        return super().dispatch(request, *args, **kwargs)

    def zablokowana(self):
        return self.oferta.status != Status.ROBOCZA or not self.oferta.aktualna

    def get(self, request, *args, **kwargs):
        if self.zablokowana():
            messages.warning(request, "Ta oferta została już wysłana. Aby zmienić pozycje lub ceny, utwórz nową wersję.")
            return redirect(self.oferta)
        return self.render_to_response(self.kontekst(WariantForm(instance=self.wariant), PozycjeFormSet(instance=self.wariant)))

    def post(self, request, *args, **kwargs):
        if self.zablokowana():
            raise PermissionDenied
        wform = WariantForm(request.POST, instance=self.wariant)
        formset = PozycjeFormSet(request.POST, instance=self.wariant)
        if wform.is_valid() and formset.is_valid():
            with transaction.atomic():
                wform.save()
                self.zapisz_pozycje(formset)
                pow_m2 = request.POST.get("powierzchnia_m2", "").replace(",", ".").strip()
                if pow_m2:
                    try:
                        self.oferta.powierzchnia_m2 = round(float(pow_m2), 2)
                        self.oferta.save(update_fields=["powierzchnia_m2"])
                    except ValueError:
                        pass
            messages.success(request, "Zapisano kalkulację.")
            if "zostan" in request.POST:
                return redirect("oferty:wariant", self.oferta.pk, self.wariant.pk)
            return redirect(self.oferta)
        messages.error(request, "Popraw zaznaczone pola.")
        return self.render_to_response(self.kontekst(wform, formset))

    def zapisz_pozycje(self, formset):
        kolejnosc = 0
        for form in formset.forms:
            if not form.has_changed() and not form.instance.pk:
                continue
            if formset.can_delete and formset._should_delete_form(form):
                if form.instance.pk:
                    form.instance.delete()
                continue
            poz = form.save(commit=False)
            poz.wariant = self.wariant
            kolejnosc += 1
            poz.kolejnosc = kolejnosc
            if "pozycja_cennika" in form.changed_data or poz.pk is None:
                poz.koszt_jednostkowy = poz.pozycja_cennika.koszt if poz.pozycja_cennika else None
            poz.save()

    def kontekst(self, wform, formset):
        cennik = {
            str(p.pk): {
                "nazwa": p.nazwa, "jednostka": p.jednostka, "cena": str(p.cena_netto),
                "koszt": str(p.koszt) if p.koszt is not None else None, "opis": p.opis,
            }
            for p in PozycjaCennika.objects.all()
        }
        return self.get_context_data(
            oferta=self.oferta,
            wariant=self.wariant,
            wform=wform,
            formset=formset,
            cennik_json=cennik,
            ustawienia_json={"rabat": str(self.oferta.rabat_procent), "vat": self.oferta.vat_procent},
            rodzaje=RodzajPozycji.choices,
            cennik_wg_rodzaju=[
                (nazwa, list(PozycjaCennika.objects.filter(aktywna=True, rodzaj=kod)))
                for kod, nazwa in RodzajPozycji.choices
            ],
        )


class AkcjaView(ModulMixin, View):
    """Wspólna baza dla przycisków-akcji (tylko POST)."""

    modul = "oferty"
    edycja = True

    def post(self, request, pk, **kwargs):
        self.oferta = get_object_or_404(Oferta, pk=pk)
        return self.wykonaj(request, **kwargs) or redirect(self.oferta)


class WariantDodajView(AkcjaView):
    def wykonaj(self, request):
        if self.oferta.status != Status.ROBOCZA:
            raise PermissionDenied
        zrodlo = request.POST.get("kopiuj")
        litera = chr(ord("A") + self.oferta.warianty.count())
        if zrodlo:
            w = operacje.kopiuj_wariant(get_object_or_404(Wariant, pk=zrodlo, oferta=self.oferta), self.oferta, f"Wariant {litera}")
        else:
            w = Wariant.objects.create(oferta=self.oferta, nazwa=f"Wariant {litera}", kolejnosc=self.oferta.warianty.count() + 1)
        messages.success(request, f"Dodano {w.nazwa}.")
        return redirect("oferty:wariant", self.oferta.pk, w.pk)


class WariantUsunView(AkcjaView):
    def wykonaj(self, request, wpk):
        if self.oferta.status != Status.ROBOCZA:
            raise PermissionDenied
        if self.oferta.warianty.count() <= 1:
            messages.error(request, "Oferta musi mieć przynajmniej jeden wariant.")
            return None
        get_object_or_404(Wariant, pk=wpk, oferta=self.oferta).delete()
        messages.success(request, "Usunięto wariant.")
        return None


class WyslanaView(AkcjaView):
    def wykonaj(self, request):
        if self.oferta.status != Status.ROBOCZA:
            raise PermissionDenied
        if not PozycjaOferty.objects.filter(wariant__oferta=self.oferta).exists():
            messages.error(request, "Oferta nie ma żadnych pozycji – uzupełnij kalkulację przed wysłaniem.")
            return None
        operacje.oznacz_wyslana(self.oferta)
        messages.success(
            request, f"Oznaczono jako wysłaną. Przypomnienie o kontakcie: {self.oferta.nastepny_kontakt:%d.%m.%Y}."
        )
        return None


class KontaktView(AkcjaView):
    def wykonaj(self, request):
        form = KontaktForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Nie zapisano kontaktu: " + " ".join(f"{k}: {' '.join(v)}" for k, v in form.errors.items()))
            return None
        operacje.zapisz_kontakt(
            self.oferta, form.save(commit=False), request.user,
            form.cleaned_data.get("nastepny_kontakt"), form.cleaned_data.get("negocjacje"),
        )
        messages.success(request, "Zapisano kontakt.")
        return None


class RozstrzygnijView(AkcjaView):
    def wykonaj(self, request):
        form = RozstrzygniecieForm(request.POST, oferta=self.oferta)
        if not form.is_valid():
            messages.error(request, "Nie zapisano: " + " ".join(" ".join(v) for v in form.errors.values()))
            return None
        d = form.cleaned_data
        operacje.rozstrzygnij(self.oferta, d["wynik"], d.get("wariant"), d.get("powod_przegranej", ""), d.get("powod_opis", ""))
        messages.success(request, f"Status oferty: {self.oferta.get_status_display()}.")
        return None


class PrzywrocView(AkcjaView):
    def wykonaj(self, request):
        operacje.przywroc_do_negocjacji(self.oferta)
        messages.success(request, "Przywrócono ofertę do negocjacji.")
        return None


class NowaWersjaView(AkcjaView):
    def wykonaj(self, request):
        if not self.oferta.aktualna:
            messages.error(request, "Nową wersję tworzy się z aktualnej (najnowszej) wersji oferty.")
            return None
        nowa = operacje.nowa_wersja(self.oferta, request.user)
        messages.success(request, f"Utworzono wersję {nowa.pelny_numer}. Zmień pozycje i wyślij ponownie.")
        return redirect(nowa)


class DokumentView(ModulMixin, View):
    """Pobranie oferty jako plik Word."""

    modul = "oferty"

    def get(self, request, pk):
        oferta = get_object_or_404(Oferta, pk=pk)
        try:
            tresc = generuj("oferta", kontekst_oferty(oferta))
        except ValidationError as e:
            messages.error(request, " ".join(e.messages) + " Popraw szablon w Administracji → Szablony dokumentów.")
            return redirect(oferta)
        nazwa = f"Oferta_{oferta.pelny_numer.replace('/', '-')}.docx"
        odp = HttpResponse(tresc, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        odp["Content-Disposition"] = content_disposition_header(True, f"{nazwa}")
        return odp


# --- Cennik ---


class CennikListView(ModulMixin, ListView):
    modul = "cennik"
    template_name = "oferty/cennik.html"

    def get_queryset(self):
        qs = PozycjaCennika.objects.all()
        if self.request.GET.get("pokaz") != "wszystkie":
            qs = qs.filter(aktywna=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["grupy"] = [(nazwa, [p for p in ctx["object_list"] if p.rodzaj == kod]) for kod, nazwa in RodzajPozycji.choices]
        ctx["pokaz"] = self.request.GET.get("pokaz", "")
        return ctx


class CennikCreateView(ModulMixin, KomunikatZapisuMixin, CreateView):
    modul = "cennik"
    edycja = True
    model = PozycjaCennika
    form_class = PozycjaCennikaForm
    template_name = "oferty/cennik_formularz.html"
    success_url = reverse_lazy("oferty:cennik")
    komunikat = "Dodano pozycję cennika."


class CennikUpdateView(ModulMixin, KomunikatZapisuMixin, UpdateView):
    modul = "cennik"
    edycja = True
    model = PozycjaCennika
    form_class = PozycjaCennikaForm
    template_name = "oferty/cennik_formularz.html"
    success_url = reverse_lazy("oferty:cennik")
    komunikat = "Zapisano pozycję cennika. Zmiana ceny NIE zmienia ofert już utworzonych."


class StatystykiView(ModulMixin, TemplateView):
    modul = "statystyki"
    template_name = "oferty/statystyki.html"

    def get_context_data(self, **kwargs):
        from .statystyki import policz

        ctx = super().get_context_data(**kwargs)
        lata = sorted({d.year for d in Oferta.objects.dates("data_wystawienia", "year")} | {timezone.localdate().year}, reverse=True)
        try:
            rok = int(self.request.GET.get("rok", lata[0]))
        except ValueError:
            rok = lata[0]
        qs = Oferta.objects.filter(aktualna=True, data_wystawienia__year=rok)
        kto = self.request.GET.get("kto", "")
        if kto.isdigit():
            qs = qs.filter(handlowiec_id=int(kto))
        qs = z_wartosciami(qs).prefetch_related("warianty__pozycje__pozycja_cennika")
        ctx.update(policz(list(qs)), rok=rok, lata=lata, kto=kto, handlowcy_lista=handlowcy())
        return ctx
