from django.urls import path

from . import views


app_name = "ventas"


urlpatterns = [
    path(
        "clientes/",
        views.cliente_lista,
        name="cliente_lista",
    ),
    path(
        "clientes/nuevo/",
        views.cliente_crear,
        name="cliente_crear",
    ),
    path(
        "clientes/<int:pk>/",
        views.cliente_detalle,
        name="cliente_detalle",
    ),
    path(
        "clientes/<int:pk>/editar/",
        views.cliente_editar,
        name="cliente_editar",
    ),
    path(
        "clientes/<int:pk>/eliminar/",
        views.cliente_eliminar,
        name="cliente_eliminar",
    ),
    path(
        "ventas/",
        views.venta_lista,
        name="venta_lista",
    ),
    path(
        "ventas/nueva/",
        views.venta_crear,
        name="venta_crear",
    ),
    path(
        "ventas/<int:pk>/",
        views.venta_detalle,
        name="venta_detalle",
    ),
    path(
        "ventas/<int:pk>/comprobante/",
        views.venta_comprobante,
        name="venta_comprobante",
    ),
    path(
        "ventas/<int:pk>/comprobante/pdf/",
        views.venta_comprobante_pdf,
        name="venta_comprobante_pdf",
    ),
    path(
        "ventas/<int:pk>/anular/",
        views.venta_anular,
        name="venta_anular",
    ),
]
