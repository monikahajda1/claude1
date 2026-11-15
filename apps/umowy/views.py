import mimetypes

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import ModulMixin
from apps.konta import uprawnienia as u
from apps.oferty.models import Oferta, Status

from . import operacje
from .forms import AneksForm, BudowaZUmowyForm, TerminyBudowyForm, UmowaForm, ZakresFormSet
from .models import Aneks, Umowa


class BudowaMixin(ModulMixin):
    """Budowa z adresu – tylko taka, do której użytkownik ma dostęp (kierownik: swoje)."""

    modul = "umowy"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.budowa = get_object_or_404(u.budowy_dla(request.user), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)


class UtworzBudoweView(ModulMixin, TemplateView):
    """Wygrana oferta → budowa z umową i zakresem prac."""

    modul = "umowy"
    edycja = True
    template_name = "umowy/utworz_budowe.html"

    def dispatch(self, request, *args, **kwargs):
        self.oferta = get_object_or_404(Oferta, pk=kwargs["pk"])
        if request.user.is_authenticated and self.oferta.budowa_id:
            messages.info(request, "Budowa z tej oferty już istnieje.")
            return redirect(self.oferta.budowa)
        return super().dispatch(request, *args, **kwargs)

    def sprawdz(self):
        if self.oferta.status != Status.WYGRANA:
            messages.error(self.request, "Budowę można utworzyć tylko z wygranej oferty.")
            return redirect(self.oferta)
        return None

    def get(self, request, *args, **kwargs):
        if (r := self.sprawdz()) is not None:
            return r
        poczatek = operacje.dane_poczatkowe_z_oferty(self.oferta)
        return self.render_to_response(self.get_context_data(
            bform=BudowaZUmowyForm(prefix="b", initial=poczatek["budowa"]),
            uform=UmowaForm(prefix="u", initial=poczatek["umowa"]),
        ))

    def post(self, request, *args, **kwargs):
        if (r := self.sprawdz()) is not None:
            return r
        bform = BudowaZUmowyForm(request.POST, prefix="b")
        uform = UmowaForm(request.POST, request.FILES, prefix="u")
        if bform.is_valid() and uform.is_valid():
            budowa = operacje.utworz_budowe_z_oferty(self.oferta, bform.save(commit=False), uform.save(commit=False))
            messages.success(request, f"Utworzono budowę {budowa.numer} z umową i zakresem prac z oferty {self.oferta.pelny_numer}.")
            return redirect(budowa)
        messages.error(request, "Popraw zaznaczone pola.")
        return self.render_to_response(self.get_context_data(bform=bform, uform=uform))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["oferta"] = self.oferta
        ctx["wariant"] = self.oferta.wariant_glowny()
        return ctx


class UmowaEdytujView(BudowaMixin, TemplateView):
    """Dodanie lub edycja danych umowy dla budowy."""

    edycja = True
    template_name = "umowy/umowa_formularz.html"

    def formy(self, data=None, files=None):
        umowa = Umowa.objects.filter(budowa=self.budowa).first()
        return (
            UmowaForm(data, files, instance=umowa, prefix="u",
                      initial=None if umowa else {"wartosc_netto": self.budowa.wartosc_netto}),
            TerminyBudowyForm(data, instance=self.budowa, prefix="t"),
        )

    def get(self, request, *args, **kwargs):
        uform, tform = self.formy()
        return self.render_to_response(self.get_context_data(uform=uform, tform=tform, budowa=self.budowa))

    def post(self, request, *args, **kwargs):
        uform, tform = self.formy(request.POST, request.FILES)
        if uform.is_valid() and tform.is_valid():
            tform.save()
            umowa = uform.save(commit=False)
            umowa.budowa = self.budowa
            umowa.save()
            umowa.synchronizuj_budowe()
            messages.success(request, "Zapisano dane umowy.")
            return redirect(self.budowa)
        messages.error(request, "Popraw zaznaczone pola.")
        return self.render_to_response(self.get_context_data(uform=uform, tform=tform, budowa=self.budowa))


class ZakresView(BudowaMixin, TemplateView):
    edycja = True
    template_name = "umowy/zakres.html"

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data(formset=ZakresFormSet(instance=self.budowa), budowa=self.budowa))

    def post(self, request, *args, **kwargs):
        formset = ZakresFormSet(request.POST, instance=self.budowa)
        if formset.is_valid():
            kolejnosc = 0
            for form in formset.forms:
                if not form.has_changed() and not form.instance.pk:
                    continue
                if formset._should_delete_form(form):
                    if form.instance.pk:
                        form.instance.delete()
                    continue
                poz = form.save(commit=False)
                poz.budowa = self.budowa
                kolejnosc += 1
                poz.kolejnosc = kolejnosc
                poz.save()
            messages.success(request, "Zapisano zakres prac.")
            return redirect(self.budowa)
        messages.error(request, "Popraw zaznaczone pola.")
        return self.render_to_response(self.get_context_data(formset=formset, budowa=self.budowa))


class AneksView(BudowaMixin, TemplateView):
    edycja = True
    template_name = "umowy/aneks_formularz.html"

    def get_umowa(self):
        umowa = Umowa.objects.filter(budowa=self.budowa).first()
        if umowa is None:
            raise Http404("Najpierw uzupełnij dane umowy.")
        return umowa

    def get_aneks(self, umowa):
        if "apk" in self.kwargs:
            return get_object_or_404(Aneks, pk=self.kwargs["apk"], umowa=umowa)
        return None

    def get(self, request, *args, **kwargs):
        umowa = self.get_umowa()
        form = AneksForm(instance=self.get_aneks(umowa))
        return self.render_to_response(self.get_context_data(form=form, budowa=self.budowa, umowa=umowa))

    def post(self, request, *args, **kwargs):
        umowa = self.get_umowa()
        form = AneksForm(request.POST, request.FILES, instance=self.get_aneks(umowa))
        if form.is_valid():
            aneks = form.save(commit=False)
            aneks.umowa = umowa
            operacje.zapisz_aneks(aneks)
            messages.success(request, f"Zapisano {aneks}. Wartość i termin budowy zostały zaktualizowane.")
            return redirect(self.budowa)
        return self.render_to_response(self.get_context_data(form=form, budowa=self.budowa, umowa=umowa))


class SkanView(BudowaMixin, View):
    """Skan umowy lub aneksu – tylko dla osób z dostępem do tej budowy."""

    def get(self, request, pk, apk=None):
        umowa = get_object_or_404(Umowa, budowa=self.budowa)
        obiekt = get_object_or_404(Aneks, pk=apk, umowa=umowa) if apk else umowa
        if not obiekt.skan:
            raise Http404
        typ, _ = mimetypes.guess_type(obiekt.skan.name)
        return FileResponse(obiekt.skan.open("rb"), content_type=typ or "application/octet-stream")

