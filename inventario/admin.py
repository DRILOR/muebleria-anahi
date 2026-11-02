from django.contrib import admin

from .models import (
    Categoria,
    Material,
    MedidaProducto,
    MovimientoInventario,
    Producto,
)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "activo",
        "creado_en",
    )
    search_fields = ("nombre",)
    list_filter = ("activo",)


class MedidaProductoInline(admin.StackedInline):
    model = MedidaProducto
    extra = 0
    max_num = 1


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nombre",
        "categoria",
        "precio",
        "stock",
        "stock_minimo",
        "activo",
    )
    search_fields = (
        "codigo",
        "nombre",
    )
    list_filter = (
        "categoria",
        "activo",
    )
    ordering = ("nombre",)
    inlines = [MedidaProductoInline]


@admin.register(MedidaProducto)
class MedidaProductoAdmin(admin.ModelAdmin):
    list_display = (
        "producto",
        "alto_cm",
        "ancho_cm",
        "profundidad_cm",
    )
    search_fields = (
        "producto__codigo",
        "producto__nombre",
    )
@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nombre",
        "unidad_medida",
        "stock",
        "stock_minimo",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
    )


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "material",
        "tipo",
        "cantidad",
        "stock_anterior",
        "stock_resultante",
    )

    list_filter = (
        "tipo",
        "fecha",
    )