from django.urls import path

from . import views

app_name = "materialy"

urlpatterns = [
    path("", views.ListaView.as_view(), name="lista"),
    path("nowy/", views.NowyView.as_view(), name="nowy"),
    path("<int:pk>/", views.SzczegolyView.as_view(), name="szczegoly"),
    path("<int:pk>/edytuj/", views.EdytujView.as_view(), name="edytuj"),
    path("<int:pk>/dokumenty/", views.DokumentDodajView.as_view(), name="dokument_dodaj"),
    path("<int:pk>/dokumenty/<int:dpk>/usun/", views.DokumentUsunView.as_view(), name="dokument_usun"),
]
