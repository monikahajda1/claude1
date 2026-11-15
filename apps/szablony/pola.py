"""Rejestr: przykładowe dane i opisy pól dla każdego rodzaju szablonu."""


def _oferta():
    from apps.oferty.dokument import kontekst_przykladowy

    return kontekst_przykladowy()


def _oferta_pola():
    from apps.oferty.dokument import POLA

    return POLA


PRZYKLADY = {"oferta": _oferta}
OPISY_POL = {"oferta": _oferta_pola}
