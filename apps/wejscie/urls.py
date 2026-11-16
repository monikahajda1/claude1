from django.urls import path

from . import views

app_name = "wejscie"

urlpatterns = [
    path("budowa/<int:pk>/", views.BudowaWejscieView.as_view(), name="budowa"),
    path("budowa/<int:pk>/materialy/", views.MaterialyAkcjaView.as_view(), name="materialy"),
    path("budowa/<int:pk>/kzm/", views.KZMUtworzView.as_view(), name="kzm_utworz"),
    path("budowa/<int:pk>/ibwr/", views.IBWRView.as_view(), name="ibwr"),
    path("budowa/<int:pk>/ibwr/dokument/", views.IBWRDokumentView.as_view(), name="ibwr_dokument"),
    path("budowa/<int:pk>/punkt/<int:ppk>/", views.OdhaczView.as_view(), name="odhacz"),
    path("kzm/<int:pk>/", views.KZMView.as_view(), name="kzm"),
    path("kzm/<int:pk>/dokument/", views.KZMDokumentView.as_view(), name="kzm_dokument"),
    path("kzm/<int:pk>/zalaczniki.zip", views.KZMZipView.as_view(), name="kzm_zip"),
    path("plik/<str:rodzaj>/<int:pk>/", views.PlikView.as_view(), name="plik"),
    path("firma/", views.FirmaListView.as_view(), name="firma"),
    path("firma/nowy/", views.FirmaNowyView.as_view(), name="firma_nowy"),
    path("firma/<int:pk>/", views.FirmaEdytujView.as_view(), name="firma_edytuj"),
]
