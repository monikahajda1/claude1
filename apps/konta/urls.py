from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

app_name = "konta"

urlpatterns = [
    path(
        "logowanie/",
        auth_views.LoginView.as_view(template_name="konta/logowanie.html", redirect_authenticated_user=True),
        name="logowanie",
    ),
    path("wyloguj/", auth_views.LogoutView.as_view(), name="wyloguj"),
    path(
        "zmiana-hasla/",
        auth_views.PasswordChangeView.as_view(
            template_name="konta/zmiana_hasla.html", success_url=reverse_lazy("konta:haslo_zmienione")
        ),
        name="zmiana_hasla",
    ),
    path(
        "zmiana-hasla/gotowe/",
        auth_views.PasswordChangeDoneView.as_view(template_name="konta/haslo_zmienione.html"),
        name="haslo_zmienione",
    ),
]
