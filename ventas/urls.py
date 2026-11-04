from django.urls import path

from . import views
from . import client_views as views_registro


app_name = "ventas"


urlpatterns = [
    path("administracion/pedidos-clientes/", views.pedido_lista, name="pedido_lista"),
    path("administracion/pedidos-clientes/<int:pk>/estado/", views.pedido_cambiar_estado, name="pedido_cambiar_estado"),
    path("clientes/registro/", views_registro.registro, name="cliente_registro"),
    path("clientes/login/", views_registro.acceso, name="cliente_login"),
    path("clientes/logout/", views_registro.salir, name="cliente_logout"),
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
