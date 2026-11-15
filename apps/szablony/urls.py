from django.urls import path

from . import views

app_name = "szablony"

urlpatterns = [
    path("pola/<str:rodzaj>/", views.PolaView.as_view(), name="pola"),
    path("wzor/<str:rodzaj>/", views.WzorView.as_view(), name="wzor"),
    path("przyklad/<str:rodzaj>/", views.PrzykladView.as_view(), name="przyklad"),
]
