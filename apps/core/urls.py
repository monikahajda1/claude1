from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("dziennik-zmian/", views.DziennikZmianView.as_view(), name="dziennik"),
]
