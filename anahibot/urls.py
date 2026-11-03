from django.urls import path

from . import views


app_name = "anahibot"


urlpatterns = [
    path(
        "asistente/",
        views.index,
        name="index",
    ),
    path(
        "asistente/responder/",
        views.responder,
        name="responder",
    ),
]
