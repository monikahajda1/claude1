from django.urls import path

from . import views

app_name = "pulpit"

urlpatterns = [
    path("", views.CoDzisView.as_view(), name="co_dzis"),
]
