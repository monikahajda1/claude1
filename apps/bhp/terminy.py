"""Liczenie, czy dokument jest ważny, wygasa wkrótce, czy już wygasł."""

from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone


@dataclass(frozen=True)
class Status:
    kod: str  # bezterminowy / wazny / wkrotce / pilne / wygasl / brak
    opis: str
    kolor: str  # kolor Bootstrapa
    dni: int | None = None  # ile dni zostało (ujemne = po terminie)

    @property
    def alert(self):
        return self.kod in ("wkrotce", "pilne", "wygasl", "brak")

    @property
    def waga(self):
        """Do sortowania – im mniejsza, tym pilniejsze."""
        return {"wygasl": 0, "brak": 1, "pilne": 2, "wkrotce": 3}.get(self.kod, 9)


BRAK = Status("brak", "brak dokumentu", "danger")


def odmien_dni(n):
    n = abs(n)
    return "dzień" if n == 1 else "dni"


def status_terminu(data_waznosci, dzis=None):
    if data_waznosci is None:
        return Status("bezterminowy", "bezterminowy", "secondary")
    dzis = dzis or timezone.localdate()
    dni = (data_waznosci - dzis).days
    if dni < 0:
        return Status("wygasl", f"wygasł {abs(dni)} {odmien_dni(dni)} temu", "danger", dni)
    if dni == 0:
        return Status("pilne", "wygasa dziś", "danger", dni)
    if dni <= settings.ALERT_DNI_PILNE:
        return Status("pilne", f"wygasa za {dni} {odmien_dni(dni)}", "danger", dni)
    if dni <= settings.ALERT_DNI_OSTRZEZENIE:
        return Status("wkrotce", f"wygasa za {dni} dni", "warning", dni)
    return Status("wazny", "ważny", "success", dni)
