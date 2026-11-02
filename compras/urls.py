from django.urls import path

from . import views


app_name = "compras"


urlpatterns = [
    path(
        "proveedores/",
        views.proveedor_lista,
        name="proveedor_lista",
    ),

    path(
        "proveedores/nuevo/",
        views.proveedor_crear,
        name="proveedor_crear",
    ),

    path(
        "proveedores/<int:pk>/editar/",
        views.proveedor_editar,
        name="proveedor_editar",
    ),

    path(
        "compras/",
        views.compra_lista,
        name="compra_lista",
    ),

    path(
        "compras/nueva/",
        views.compra_crear,
        name="compra_crear",
    ),
]