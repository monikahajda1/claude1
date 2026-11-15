from django.urls import path

from . import views

app_name = "bhp"


def trasy(rodzaj, prefiks, lista, pojedynczy):
    return [
        path(f"{prefiks}/", views.ListaView.as_view(rodzaj=rodzaj), name=lista),
        path(f"{prefiks}/nowy/", views.NowyView.as_view(rodzaj=rodzaj), name=f"{pojedynczy}_nowy"),
        path(f"{prefiks}/<int:pk>/", views.SzczegolyView.as_view(rodzaj=rodzaj), name=pojedynczy),
        path(f"{prefiks}/<int:pk>/edytuj/", views.EdytujView.as_view(rodzaj=rodzaj), name=f"{pojedynczy}_edytuj"),
        path(
            f"{prefiks}/<int:wlasciciel_pk>/dokumenty/nowy/",
            views.DokumentNowyView.as_view(rodzaj=rodzaj),
            name=f"{pojedynczy}_dokument_nowy",
        ),
        path(
            f"{prefiks}/<int:wlasciciel_pk>/dokumenty/<int:pk>/",
            views.DokumentEdytujView.as_view(rodzaj=rodzaj),
            name=f"{pojedynczy}_dokument_edytuj",
        ),
        path(
            f"{prefiks}/<int:wlasciciel_pk>/dokumenty/<int:pk>/usun/",
            views.DokumentUsunView.as_view(rodzaj=rodzaj),
            name=f"{pojedynczy}_dokument_usun",
        ),
    ]


urlpatterns = (
    trasy("pracownik", "pracownicy", "pracownicy", "pracownik")
    + trasy("sprzet", "sprzet", "sprzety", "sprzet")
    + [path("alerty/", views.AlertyView.as_view(), name="alerty")]
)
