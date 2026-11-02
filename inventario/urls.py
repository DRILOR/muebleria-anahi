from django.urls import path

from . import views


app_name = "inventario"


urlpatterns = [
    path(
        "productos/",
        views.producto_lista,
        name="producto_lista",
    ),
    path(
        "productos/nuevo/",
        views.producto_crear,
        name="producto_crear",
    ),
    path(
        "productos/<int:pk>/editar/",
        views.producto_editar,
        name="producto_editar",
    ),
    path(
        "productos/<int:pk>/eliminar/",
        views.producto_eliminar,
        name="producto_eliminar",
    ),
]