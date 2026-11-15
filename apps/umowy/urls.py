from django.urls import path

from . import views

app_name = "umowy"

urlpatterns = [
    path("z-oferty/<int:pk>/", views.UtworzBudoweView.as_view(), name="z_oferty"),
    path("budowa/<int:pk>/", views.UmowaEdytujView.as_view(), name="edytuj"),
    path("budowa/<int:pk>/zakres/", views.ZakresView.as_view(), name="zakres"),
    path("budowa/<int:pk>/aneks/", views.AneksView.as_view(), name="aneks_nowy"),
    path("budowa/<int:pk>/aneks/<int:apk>/", views.AneksView.as_view(), name="aneks"),
    path("budowa/<int:pk>/skan/", views.SkanView.as_view(), name="skan"),
    path("budowa/<int:pk>/aneks/<int:apk>/skan/", views.SkanView.as_view(), name="skan_aneksu"),
]
