from decimal import Decimal

from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce

from inventario.models import Categoria, Material, Producto
from ventas.models import DetalleVenta, Ingreso, Venta


DECIMAL_CERO = Value(
    Decimal("0.00"),
    output_field=DecimalField(max_digits=16, decimal_places=2),
)


def _suma_decimal(expresion):
    return Coalesce(
        expresion,
        DECIMAL_CERO,
        output_field=DecimalField(max_digits=16, decimal_places=2),
    )


def filtrar_por_fechas(queryset, campo, inicio=None, fin=None):
    if inicio:
        queryset = queryset.filter(**{f"{campo}__gte": inicio})
    if fin:
        queryset = queryset.filter(**{f"{campo}__lt": fin})
    return queryset


def ventas_periodo(inicio=None, fin=None):
    ventas = (
        Venta.objects
        .filter(estado=Venta.ESTADO_COMPLETADA)
        .select_related("cliente", "creado_por", "ingreso")
        .prefetch_related("detalles__producto")
        .order_by("-fecha")
    )
    return filtrar_por_fechas(ventas, "fecha", inicio, fin)


def resumen_ventas(inicio=None, fin=None):
    ventas = filtrar_por_fechas(
        Venta.objects.filter(estado=Venta.ESTADO_COMPLETADA),
        "fecha",
        inicio,
        fin,
    )

    resumen = ventas.aggregate(
        cantidad=Count("pk"),
        total=_suma_decimal(Sum("total")),
    )

    resumen["promedio"] = (
        (resumen["total"] / resumen["cantidad"]).quantize(
            Decimal("0.01")
        )
        if resumen["cantidad"]
        else Decimal("0.00")
    )

    unidades = (
        DetalleVenta.objects
        .filter(venta__in=ventas)
        .aggregate(
            total=_suma_decimal(Sum("cantidad")),
        )["total"]
    )

    anuladas = filtrar_por_fechas(
        Venta.objects.filter(estado=Venta.ESTADO_ANULADA),
        "fecha",
        inicio,
        fin,
    ).aggregate(
        cantidad=Count("pk"),
        total=_suma_decimal(Sum("total")),
    )

    return {
        "cantidad": resumen["cantidad"],
        "total": resumen["total"],
        "promedio": resumen["promedio"],
        "unidades": int(unidades),
        "anuladas_cantidad": anuladas["cantidad"],
        "anuladas_total": anuladas["total"],
    }


def productos_mas_vendidos(inicio=None, fin=None, limite=10):
    detalles = DetalleVenta.objects.filter(
        venta__estado=Venta.ESTADO_COMPLETADA,
    )
    detalles = filtrar_por_fechas(
        detalles,
        "venta__fecha",
        inicio,
        fin,
    )

    filas = (
        detalles
        .values(
            "producto__codigo",
            "producto__nombre",
            "producto__precio",
            "producto__stock",
        )
        .annotate(
            cantidad=_suma_decimal(Sum("cantidad")),
            ingresos=_suma_decimal(Sum("subtotal")),
            ventas=Count("venta", distinct=True),
        )
        .order_by("-cantidad", "producto__nombre")[:limite]
    )

    return [
        {
            "codigo": fila["producto__codigo"],
            "nombre": fila["producto__nombre"],
            "precio": fila["producto__precio"],
            "stock": fila["producto__stock"],
            "cantidad": int(fila["cantidad"]),
            "ingresos": fila["ingresos"],
            "ventas": fila["ventas"],
        }
        for fila in filas
    ]


def resumen_productos_vendidos(inicio=None, fin=None):
    detalles = DetalleVenta.objects.filter(
        venta__estado=Venta.ESTADO_COMPLETADA,
    )
    detalles = filtrar_por_fechas(
        detalles,
        "venta__fecha",
        inicio,
        fin,
    )

    agregado = detalles.aggregate(
        unidades=_suma_decimal(Sum("cantidad")),
        ingresos=_suma_decimal(Sum("subtotal")),
        productos=Count("producto", distinct=True),
        ventas=Count("venta", distinct=True),
    )

    return {
        "unidades": int(agregado["unidades"]),
        "ingresos": agregado["ingresos"],
        "productos": agregado["productos"],
        "ventas": agregado["ventas"],
    }


def ingresos_periodo(inicio=None, fin=None):
    ingresos = (
        Ingreso.objects
        .filter(venta__estado=Venta.ESTADO_COMPLETADA)
        .select_related("venta", "venta__cliente", "registrado_por")
        .order_by("-fecha")
    )
    return filtrar_por_fechas(
        ingresos,
        "venta__fecha",
        inicio,
        fin,
    )


def resumen_ingresos(inicio=None, fin=None):
    ingresos = ingresos_periodo(inicio, fin)

    agregado = ingresos.aggregate(
        cantidad=Count("pk"),
        total=_suma_decimal(Sum("monto")),
    )

    totales_por_metodo = {
        fila["metodo_pago"]: fila
        for fila in ingresos.values("metodo_pago").annotate(
            cantidad=Count("pk"),
            total=_suma_decimal(Sum("monto")),
        )
    }

    por_metodo = []

    for codigo, nombre in Ingreso.METODOS_PAGO:
        fila = totales_por_metodo.get(codigo, {})
        por_metodo.append(
            {
                "codigo": codigo,
                "nombre": nombre,
                "cantidad": fila.get("cantidad", 0),
                "total": fila.get("total", Decimal("0.00")),
            }
        )

    return {
        "cantidad": agregado["cantidad"],
        "total": agregado["total"],
        "promedio": (
            (agregado["total"] / agregado["cantidad"]).quantize(
                Decimal("0.01")
            )
            if agregado["cantidad"]
            else Decimal("0.00")
        ),
        "por_metodo": por_metodo,
    }


def _anotar_valor_inventario(queryset, campo_precio):
    return queryset.annotate(
        valor_inventario=ExpressionWrapper(
            F("stock") * F(campo_precio),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
    )


def _filtrar_estado_stock(queryset, estado):
    if estado == "agotado":
        return queryset.filter(stock=0)
    if estado == "bajo":
        return queryset.filter(
            stock__gt=0,
            stock__lte=F("stock_minimo"),
        )
    if estado == "disponible":
        return queryset.filter(stock__gt=F("stock_minimo"))
    return queryset


def _resumen_stock(queryset):
    return {
        "total": queryset.count(),
        "agotados": queryset.filter(stock=0).count(),
        "bajos": queryset.filter(
            stock__gt=0,
            stock__lte=F("stock_minimo"),
        ).count(),
        "disponibles": queryset.filter(
            stock__gt=F("stock_minimo"),
        ).count(),
        "valor": queryset.aggregate(
            total=_suma_decimal(Sum("valor_inventario")),
        )["total"],
    }


def reporte_inventario(
    busqueda="",
    categoria_id=None,
    estado="",
    solo_activos=True,
):
    productos = Producto.objects.select_related("categoria")
    materiales = Material.objects.all()

    if solo_activos:
        productos = productos.filter(activo=True)
        materiales = materiales.filter(activo=True)

    if busqueda:
        productos = productos.filter(
            Q(codigo__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
            | Q(categoria__nombre__icontains=busqueda)
        )
        materiales = materiales.filter(
            Q(codigo__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
        )

    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    productos = _filtrar_estado_stock(productos, estado)
    materiales = _filtrar_estado_stock(materiales, estado)

    productos = _anotar_valor_inventario(productos, "precio")
    materiales = _anotar_valor_inventario(
        materiales,
        "costo_referencia",
    )

    return {
        "productos": productos.order_by("nombre"),
        "materiales": materiales.order_by("nombre"),
        "resumen_productos": _resumen_stock(productos),
        "resumen_materiales": _resumen_stock(materiales),
        "categorias": Categoria.objects.filter(
            activo=True,
        ).order_by("nombre"),
    }
