"""Czynności na ofertach: wysłanie, kontakt, rozstrzygnięcie, nowa wersja."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import DNI_DO_KONTAKTU, Oferta, Status


def oznacz_wyslana(oferta, dzis=None):
    dzis = dzis or timezone.localdate()
    oferta.status = Status.WYSLANA
    oferta.data_wyslania = dzis
    oferta.nastepny_kontakt = dzis + timedelta(days=DNI_DO_KONTAKTU)
    oferta.save()


def zapisz_kontakt(oferta, kontakt, kto, nastepny_kontakt, negocjacje=False):
    kontakt.oferta = oferta
    kontakt.kto = kto
    kontakt.save()
    oferta.nastepny_kontakt = nastepny_kontakt
    if negocjacje and oferta.status == Status.WYSLANA:
        oferta.status = Status.NEGOCJACJE
    oferta.save()


def rozstrzygnij(oferta, wynik, wariant=None, powod="", powod_opis="", dzis=None):
    oferta.status = wynik
    oferta.data_rozstrzygniecia = dzis or timezone.localdate()
    oferta.nastepny_kontakt = None
    oferta.powod_przegranej = powod if wynik == Status.PRZEGRANA else ""
    oferta.powod_opis = powod_opis if wynik == Status.PRZEGRANA else ""
    with transaction.atomic():
        oferta.save()
        for w in oferta.warianty.all():
            nowy = wynik == Status.WYGRANA and wariant is not None and w.pk == wariant.pk
            if w.wybrany != nowy:
                w.wybrany = nowy
                w.save()


def przywroc_do_negocjacji(oferta):
    oferta.status = Status.NEGOCJACJE
    oferta.data_rozstrzygniecia = None
    oferta.powod_przegranej = ""
    oferta.powod_opis = ""
    oferta.nastepny_kontakt = timezone.localdate() + timedelta(days=DNI_DO_KONTAKTU)
    oferta.save()
    for w in oferta.warianty.filter(wybrany=True):
        w.wybrany = False
        w.save()


@transaction.atomic
def nowa_wersja(oferta, kto=None):
    """Kopiuje ofertę z wariantami i pozycjami jako kolejną wersję (np. po negocjacjach).

    Poprzednia wersja zostaje w historii, ale przestaje być „aktualna”.
    """
    warianty = list(oferta.warianty.prefetch_related("pozycje"))
    ostatnia = Oferta.objects.filter(numer=oferta.numer).order_by("-wersja").first()
    stara_pk = oferta.pk
    Oferta.objects.filter(numer=oferta.numer).update(aktualna=False)

    nowa = Oferta.objects.get(pk=stara_pk)
    nowa.pk = None
    nowa.id = None
    nowa._state.adding = True
    nowa.wersja = ostatnia.wersja + 1
    nowa.aktualna = True
    nowa.poprzednia_id = stara_pk
    nowa.status = Status.ROBOCZA
    nowa.data_wystawienia = timezone.localdate()
    nowa.data_wyslania = None
    nowa.data_rozstrzygniecia = None
    nowa.nastepny_kontakt = None
    nowa.powod_przegranej = ""
    nowa.powod_opis = ""
    if kto is not None and nowa.handlowiec_id is None:
        nowa.handlowiec = kto
    nowa.save()
    for w in warianty:
        kopiuj_wariant(w, nowa)
    return nowa


def kopiuj_wariant(wariant, oferta, nazwa=None):
    pozycje = list(wariant.pozycje.all())
    nowy = type(wariant).objects.create(
        oferta=oferta, nazwa=nazwa or wariant.nazwa, opis=wariant.opis,
        kolejnosc=oferta.warianty.count() + 1, wybrany=False,
    )
    for p in pozycje:
        p.pk = None
        p.id = None
        p._state.adding = True
        p.wariant = nowy
        p.save()
    return nowy
