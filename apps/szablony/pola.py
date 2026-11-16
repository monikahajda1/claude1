"""Rejestr: przykładowe dane i opisy pól dla każdego rodzaju szablonu."""


def _oferta():
    from apps.oferty.dokument import kontekst_przykladowy

    return kontekst_przykladowy()


def _oferta_pola():
    from apps.oferty.dokument import POLA

    return POLA


def _kzm():
    from apps.wejscie.dokumenty import kontekst_kzm_przykladowy

    return kontekst_kzm_przykladowy()


def _kzm_pola():
    from apps.wejscie.dokumenty import POLA_KZM

    return POLA_KZM


def _ibwr():
    from apps.wejscie.dokumenty import kontekst_ibwr_przykladowy

    return kontekst_ibwr_przykladowy()


def _ibwr_pola():
    from apps.wejscie.dokumenty import POLA_IBWR

    return POLA_IBWR


PRZYKLADY = {"oferta": _oferta, "kzm": _kzm, "ibwr": _ibwr}
OPISY_POL = {"oferta": _oferta_pola, "kzm": _kzm_pola, "ibwr": _ibwr_pola}
