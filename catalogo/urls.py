from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("catalogo/", views.lista, name="lista"),
    path("catalogo/<int:pk>/", views.detalle, name="detalle"),
    path("carrito/", views.carrito, name="carrito"),
    path("carrito/agregar/<int:pk>/", views.carrito_agregar, name="carrito_agregar"),
    path("carrito/actualizar/<int:pk>/", views.carrito_actualizar, name="carrito_actualizar"),
    path("carrito/vaciar/", views.carrito_vaciar, name="carrito_vaciar"),
    path("carrito/confirmar/", views.confirmar_carrito, name="confirmar_carrito"),
    path("pedido/<int:pk>/confirmacion/", views.pedido_exito, name="pedido_exito"),
]
