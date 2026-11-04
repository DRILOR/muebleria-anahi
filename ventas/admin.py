from django.contrib import admin

from .models import (
    Cliente,
    DetalleVenta,
    Ingreso,
    MovimientoProducto,
    PedidoCliente,
    DetallePedido,
    Venta,
)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "nit",
        "telefono",
        "email",
        "activo",
        "creado_en",
    )
    search_fields = (
        "nombre",
        "nit",
        "telefono",
        "email",
    )
    list_filter = ("activo",)


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = (
        "precio_unitario",
        "subtotal",
    )


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "cliente",
        "total",
        "estado",
        "creado_por",
        "fecha",
    )
    search_fields = (
        "numero",
        "cliente__nombre",
        "cliente__nit",
    )
    list_filter = (
        "estado",
        "fecha",
    )
    readonly_fields = (
        "numero",
        "total",
        "fecha",
        "actualizado_en",
    )
    inlines = [DetalleVentaInline]


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = (
        "venta",
        "monto",
        "metodo_pago",
        "fecha",
        "registrado_por",
    )
    list_filter = (
        "metodo_pago",
        "fecha",
    )
    search_fields = (
        "venta__numero",
        "referencia",
    )


@admin.register(MovimientoProducto)
class MovimientoProductoAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "producto",
        "tipo",
        "cantidad",
        "stock_anterior",
        "stock_resultante",
    )
    list_filter = (
        "tipo",
        "fecha",
    )
    search_fields = (
        "producto__codigo",
        "producto__nombre",
        "referencia",
    )


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ("producto", "cantidad", "precio_unitario", "subtotal")
    can_delete = False


@admin.register(PedidoCliente)
class PedidoClienteAdmin(admin.ModelAdmin):
    list_display = ("numero", "creado_en", "cliente", "total", "estado", "venta")
    list_filter = ("estado", "creado_en")
    search_fields = ("numero", "cliente__nombre", "cliente__email", "cliente__telefono")
    readonly_fields = ("numero", "cliente", "total", "venta", "creado_en", "actualizado_en", "cambiado_por")
    inlines = [DetallePedidoInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff
