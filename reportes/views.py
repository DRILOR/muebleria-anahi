from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render

from ventas.utils import (
    fecha_actual,
    parsear_fecha,
    primer_dia_mes,
    rango_fechas,
)

from .builders import (
    construir_reporte_inventario,
    construir_reporte_ingresos,
    construir_reporte_productos,
    construir_reporte_ventas,
)
from .exporters import (
    generar_excel_reporte,
    generar_pdf_reporte,
    nombre_excel,
    nombre_pdf,
)
from .services import (
    ingresos_periodo,
    productos_mas_vendidos,
    reporte_inventario,
    resumen_ingresos,
    resumen_productos_vendidos,
    resumen_ventas,
    ventas_periodo,
)


LIMITES_PRODUCTOS = (5, 10, 20, 50)


def _periodo(request):
    desde_texto = request.GET.get("desde", "").strip()
    hasta_texto = request.GET.get("hasta", "").strip()
    error = ""

    if not desde_texto and not hasta_texto:
        desde = primer_dia_mes()
        hasta = fecha_actual()
        desde_texto = desde.isoformat()
        hasta_texto = hasta.isoformat()
    else:
        desde = None
        hasta = None

    try:
        inicio, fin = rango_fechas(desde_texto, hasta_texto)
        desde = parsear_fecha(desde_texto, "fecha inicial")
        hasta = parsear_fecha(hasta_texto, "fecha final")
    except ValueError as exc:
        error = str(exc)
        desde = primer_dia_mes()
        hasta = fecha_actual()
        desde_texto = desde.isoformat()
        hasta_texto = hasta.isoformat()
        inicio, fin = rango_fechas(desde_texto, hasta_texto)

    return {
        "desde": desde,
        "hasta": hasta,
        "desde_texto": desde_texto,
        "hasta_texto": hasta_texto,
        "inicio": inicio,
        "fin": fin,
        "error": error,
    }


def _paginar(request, queryset, por_pagina=20):
    paginador = Paginator(queryset, por_pagina)
    return paginador.get_page(request.GET.get("page"))


def _limite_productos(request):
    try:
        limite = int(request.GET.get("limite", 10))
    except (TypeError, ValueError):
        limite = 10

    if limite not in LIMITES_PRODUCTOS:
        limite = 10

    return limite


def _categoria_id(request):
    try:
        return int(request.GET.get("categoria", ""))
    except (TypeError, ValueError):
        return None


def _respuesta_pdf(reporte):
    response = HttpResponse(
        generar_pdf_reporte(reporte),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{nombre_pdf(reporte)}"'
    )
    return response


def _respuesta_excel(reporte):
    response = HttpResponse(
        generar_excel_reporte(reporte),
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{nombre_excel(reporte)}"'
    )
    return response


def _datos_ventas(request):
    periodo = _periodo(request)
    resumen = resumen_ventas(
        periodo["inicio"],
        periodo["fin"],
    )
    ingresos = resumen_ingresos(
        periodo["inicio"],
        periodo["fin"],
    )
    ventas = ventas_periodo(
        periodo["inicio"],
        periodo["fin"],
    )

    return periodo, resumen, ingresos, ventas


def _datos_productos(request):
    periodo = _periodo(request)
    limite = _limite_productos(request)
    productos = productos_mas_vendidos(
        periodo["inicio"],
        periodo["fin"],
        limite,
    )
    resumen = resumen_productos_vendidos(
        periodo["inicio"],
        periodo["fin"],
    )

    return periodo, limite, productos, resumen


def _datos_inventario(request):
    busqueda = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    activos = request.GET.get("activos", "1")
    categoria_id = _categoria_id(request)

    datos = reporte_inventario(
        busqueda=busqueda,
        categoria_id=categoria_id,
        estado=estado,
        solo_activos=activos != "0",
    )

    return {
        "busqueda": busqueda,
        "estado": estado,
        "activos": activos,
        "categoria_id": categoria_id,
        **datos,
    }


def _datos_ingresos(request):
    periodo = _periodo(request)
    resumen = resumen_ingresos(
        periodo["inicio"],
        periodo["fin"],
    )
    ingresos = ingresos_periodo(
        periodo["inicio"],
        periodo["fin"],
    )

    return periodo, resumen, ingresos


@staff_member_required
def reporte_ventas(request):
    periodo, resumen, ingresos, ventas = _datos_ventas(request)

    return render(
        request,
        "reportes/ventas.html",
        {
            "periodo": periodo,
            "resumen": resumen,
            "resumen_ingresos": ingresos,
            "page_obj": _paginar(request, ventas),
            "max_metodo": max(
                (
                    metodo["total"]
                    for metodo in ingresos["por_metodo"]
                ),
                default=0,
            ),
        },
    )


@staff_member_required
def reporte_ventas_pdf(request):
    periodo, resumen, ingresos, ventas = _datos_ventas(request)
    reporte = construir_reporte_ventas(
        ventas,
        resumen,
        ingresos,
        periodo["desde"],
        periodo["hasta"],
        request.user.get_username(),
    )
    return _respuesta_pdf(reporte)


@staff_member_required
def reporte_ventas_excel(request):
    periodo, resumen, ingresos, ventas = _datos_ventas(request)
    reporte = construir_reporte_ventas(
        ventas,
        resumen,
        ingresos,
        periodo["desde"],
        periodo["hasta"],
        request.user.get_username(),
    )
    return _respuesta_excel(reporte)


@staff_member_required
def reporte_productos(request):
    periodo, limite, productos, resumen = _datos_productos(request)

    return render(
        request,
        "reportes/productos.html",
        {
            "periodo": periodo,
            "limite": limite,
            "limites": LIMITES_PRODUCTOS,
            "productos": productos,
            "resumen": resumen,
            "max_cantidad": max(
                (producto["cantidad"] for producto in productos),
                default=0,
            ),
        },
    )


@staff_member_required
def reporte_productos_pdf(request):
    periodo, limite, productos, resumen = _datos_productos(request)
    reporte = construir_reporte_productos(
        productos,
        resumen,
        periodo["desde"],
        periodo["hasta"],
        limite,
        request.user.get_username(),
    )
    return _respuesta_pdf(reporte)


@staff_member_required
def reporte_productos_excel(request):
    periodo, limite, productos, resumen = _datos_productos(request)
    reporte = construir_reporte_productos(
        productos,
        resumen,
        periodo["desde"],
        periodo["hasta"],
        limite,
        request.user.get_username(),
    )
    return _respuesta_excel(reporte)


@staff_member_required
def reporte_inventario_view(request):
    return render(
        request,
        "reportes/inventario.html",
        _datos_inventario(request),
    )


@staff_member_required
def reporte_inventario_pdf(request):
    datos = _datos_inventario(request)
    reporte = construir_reporte_inventario(
        datos["productos"],
        datos["materiales"],
        datos["resumen_productos"],
        datos["resumen_materiales"],
        request.user.get_username(),
    )
    return _respuesta_pdf(reporte)


@staff_member_required
def reporte_inventario_excel(request):
    datos = _datos_inventario(request)
    reporte = construir_reporte_inventario(
        datos["productos"],
        datos["materiales"],
        datos["resumen_productos"],
        datos["resumen_materiales"],
        request.user.get_username(),
    )
    return _respuesta_excel(reporte)


@staff_member_required
def reporte_ingresos(request):
    periodo, resumen, ingresos = _datos_ingresos(request)

    return render(
        request,
        "reportes/ingresos.html",
        {
            "periodo": periodo,
            "resumen": resumen,
            "page_obj": _paginar(request, ingresos),
            "max_metodo": max(
                (
                    metodo["total"]
                    for metodo in resumen["por_metodo"]
                ),
                default=0,
            ),
        },
    )


@staff_member_required
def reporte_ingresos_pdf(request):
    periodo, resumen, ingresos = _datos_ingresos(request)
    reporte = construir_reporte_ingresos(
        ingresos,
        resumen,
        periodo["desde"],
        periodo["hasta"],
        request.user.get_username(),
    )
    return _respuesta_pdf(reporte)


@staff_member_required
def reporte_ingresos_excel(request):
    periodo, resumen, ingresos = _datos_ingresos(request)
    reporte = construir_reporte_ingresos(
        ingresos,
        resumen,
        periodo["desde"],
        periodo["hasta"],
        request.user.get_username(),
    )
    return _respuesta_excel(reporte)
