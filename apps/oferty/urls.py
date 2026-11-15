from django.urls import path

from . import views

app_name = "oferty"

urlpatterns = [
    path("", views.OfertaListView.as_view(), name="lista"),
    path("nowa/", views.OfertaCreateView.as_view(), name="nowa"),
    path("<int:pk>/", views.OfertaDetailView.as_view(), name="szczegoly"),
    path("<int:pk>/edytuj/", views.OfertaUpdateView.as_view(), name="edytuj"),
    path("<int:pk>/wariant/<int:wpk>/", views.WariantView.as_view(), name="wariant"),
    path("<int:pk>/wariant/dodaj/", views.WariantDodajView.as_view(), name="wariant_dodaj"),
    path("<int:pk>/wariant/<int:wpk>/usun/", views.WariantUsunView.as_view(), name="wariant_usun"),
    path("<int:pk>/wyslana/", views.WyslanaView.as_view(), name="wyslana"),
    path("<int:pk>/kontakt/", views.KontaktView.as_view(), name="kontakt"),
    path("<int:pk>/rozstrzygnij/", views.RozstrzygnijView.as_view(), name="rozstrzygnij"),
    path("<int:pk>/przywroc/", views.PrzywrocView.as_view(), name="przywroc"),
    path("<int:pk>/nowa-wersja/", views.NowaWersjaView.as_view(), name="nowa_wersja"),
    path("<int:pk>/dokument/", views.DokumentView.as_view(), name="dokument"),
    path("cennik/", views.CennikListView.as_view(), name="cennik"),
    path("cennik/nowa/", views.CennikCreateView.as_view(), name="cennik_nowa"),
    path("cennik/<int:pk>/", views.CennikUpdateView.as_view(), name="cennik_edytuj"),
    path("statystyki/", views.StatystykiView.as_view(), name="statystyki"),
]
