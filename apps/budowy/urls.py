from django.urls import path

from . import views

app_name = "budowy"

urlpatterns = [
    path("", views.BudowaListView.as_view(), name="lista"),
    path("nowa/", views.BudowaCreateView.as_view(), name="nowa"),
    path("<int:pk>/", views.BudowaDetailView.as_view(), name="szczegoly"),
    path("<int:pk>/edytuj/", views.BudowaUpdateView.as_view(), name="edytuj"),
    path("<int:pk>/ekipa/", views.ZespolBudowyView.as_view(), name="ekipa"),
    path("klienci/", views.KlientListView.as_view(), name="klienci"),
    path("klienci/nowy/", views.KlientCreateView.as_view(), name="klient_nowy"),
    path("klienci/<int:pk>/", views.KlientUpdateView.as_view(), name="klient_edytuj"),
]
