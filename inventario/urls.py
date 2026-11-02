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
    path(
        "materiales/",
        views.material_lista,
        name="material_lista",
    ),
    path(
        "materiales/nuevo/",
        views.material_crear,
        name="material_crear",
    ),
    path(
        "materiales/<int:pk>/editar/",
        views.material_editar,
        name="material_editar",
    ),
    path(
        "inventario/movimiento/",
        views.movimiento_crear,
        name="movimiento_crear",
    ),
    path(
        "inventario/historial/",
        views.movimiento_historial,
        name="movimiento_historial",
    ),
]
