from django.urls import path

from . import views


app_name = "reportes"


urlpatterns = [
    path(
        "reportes/ventas/",
        views.reporte_ventas,
        name="ventas",
    ),
    path(
        "reportes/ventas/pdf/",
        views.reporte_ventas_pdf,
        name="ventas_pdf",
    ),
    path(
        "reportes/ventas/excel/",
        views.reporte_ventas_excel,
        name="ventas_excel",
    ),
    path(
        "reportes/productos/",
        views.reporte_productos,
        name="productos",
    ),
    path(
        "reportes/productos/pdf/",
        views.reporte_productos_pdf,
        name="productos_pdf",
    ),
    path(
        "reportes/productos/excel/",
        views.reporte_productos_excel,
        name="productos_excel",
    ),
    path(
        "reportes/inventario/",
        views.reporte_inventario_view,
        name="inventario",
    ),
    path(
        "reportes/inventario/pdf/",
        views.reporte_inventario_pdf,
        name="inventario_pdf",
    ),
    path(
        "reportes/inventario/excel/",
        views.reporte_inventario_excel,
        name="inventario_excel",
    ),
    path(
        "reportes/ingresos/",
        views.reporte_ingresos,
        name="ingresos",
    ),
    path(
        "reportes/ingresos/pdf/",
        views.reporte_ingresos_pdf,
        name="ingresos_pdf",
    ),
    path(
        "reportes/ingresos/excel/",
        views.reporte_ingresos_excel,
        name="ingresos_excel",
    ),
]
