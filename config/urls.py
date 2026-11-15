from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from apps.core import views as core_views

admin.site.site_header = settings.NAZWA_APLIKACJI + " – administracja"
admin.site.site_title = settings.NAZWA_APLIKACJI
admin.site.index_title = "Panel administratora (konta, role, słowniki)"

urlpatterns = [
    path("", include("apps.pulpit.urls")),
    path("konto/", include("apps.konta.urls")),
    path("budowy/", include("apps.budowy.urls")),
    path("bhp/", include("apps.bhp.urls")),
    path("oferty/", include("apps.oferty.urls")),
    path("szablony/", include("apps.szablony.urls")),
    path("umowy/", include("apps.umowy.urls")),
    path("system/", include("apps.core.urls")),
    path("admin/", admin.site.urls),
    # PWA
    path("manifest.webmanifest", core_views.manifest, name="manifest"),
    path("sw.js", core_views.service_worker, name="service_worker"),
    path("offline/", core_views.offline, name="offline"),
    # Przesłane pliki – zawsze przez kontrolę uprawnień
    re_path(r"^pliki/(?P<sciezka>.+)$", core_views.pobierz_plik, name="plik"),
]
