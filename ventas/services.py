from collections import OrderedDict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from inventario.models import Producto

from .models import (
    Cliente,
    DetalleVenta,
    Ingreso,
    MovimientoProducto,
    Venta,
    PedidoCliente,
    DetallePedido,
)


CENTAVO = Decimal("0.01")


def _normalizar_cantidad(valor):
    try:
        cantidad_decimal = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(
            "La cantidad debe ser un número entero mayor que cero."
        )

    if (
        not cantidad_decimal.is_finite()
        or cantidad_decimal != cantidad_decimal.to_integral_value()
    ):
        raise ValidationError(
            "La cantidad debe ser un número entero."
        )

    cantidad = int(cantidad_decimal)

    if cantidad <= 0:
        raise ValidationError(
            "La cantidad debe ser mayor que cero."
        )

    return cantidad


def _obtener_cliente(cliente):
    if isinstance(cliente, Cliente):
        return cliente

    try:
        return Cliente.objects.get(pk=cliente)
    except (Cliente.DoesNotExist, TypeError, ValueError):
        raise ValidationError("El cliente seleccionado no existe.")


def _agrupar_items(items):
    if not items:
        raise ValidationError(
            "La venta debe incluir al menos un producto."
        )

    agrupados = OrderedDict()

    for item in items:
        producto = item.get("producto")
        cantidad = _normalizar_cantidad(item.get("cantidad"))

        if producto is None:
            raise ValidationError(
                "Debe seleccionar un producto en cada línea."
            )

        producto_id = (
            producto.pk
            if isinstance(producto, Producto)
            else producto
        )

        try:
            producto_id = int(producto_id)
        except (TypeError, ValueError):
            raise ValidationError(
                "El producto seleccionado no es válido."
            )

        agrupados[producto_id] = (
            agrupados.get(producto_id, 0) + cantidad
        )

    return agrupados


def _validar_metodo_pago(metodo_pago):
    metodos = dict(Ingreso.METODOS_PAGO)

    if metodo_pago not in metodos:
        raise ValidationError("El método de pago no es válido.")


@transaction.atomic
def registrar_venta(
    cliente,
    items,
    usuario=None,
    observaciones="",
    metodo_pago=Ingreso.EFECTIVO,
    referencia_pago="",
):
    """Registra una venta completa de forma atómica.

    Los precios siempre se toman de la base de datos para evitar que el
    navegador pueda alterar el importe. El stock se bloquea con
    ``select_for_update`` para impedir ventas simultáneas sin existencias.
    """

    cliente = _obtener_cliente(cliente)

    if not cliente.activo:
        raise ValidationError(
            "No se puede registrar una venta para un cliente inactivo."
        )

    _validar_metodo_pago(metodo_pago)

    cantidades = _agrupar_items(items)

    productos = (
        Producto.objects
        .select_for_update()
        .filter(pk__in=sorted(cantidades))
        .order_by("pk")
    )
    productos_por_id = {
        producto.pk: producto
        for producto in productos
    }

    if len(productos_por_id) != len(cantidades):
        raise ValidationError(
            "Uno de los productos seleccionados no existe."
        )

    for producto_id, cantidad in cantidades.items():
        producto = productos_por_id[producto_id]

        if not producto.activo:
            raise ValidationError(
                f"El producto {producto.nombre} está inactivo."
            )

        if cantidad > producto.stock:
            raise ValidationError(
                f"Stock insuficiente para {producto.nombre}. "
                f"Disponible: {producto.stock} unidad(es)."
            )

    venta = Venta.objects.create(
        cliente=cliente,
        observaciones=observaciones,
        creado_por=usuario,
    )

    total = Decimal("0.00")

    for producto_id, cantidad in cantidades.items():
        producto = productos_por_id[producto_id]
        stock_anterior = producto.stock
        precio_unitario = Decimal(producto.precio).quantize(CENTAVO)
        subtotal = (
            precio_unitario * cantidad
        ).quantize(CENTAVO, rounding=ROUND_HALF_UP)

        if precio_unitario < 0:
            raise ValidationError(
                f"El precio de {producto.nombre} no es válido."
            )

        producto.stock = stock_anterior - cantidad
        producto.save(
            update_fields=[
                "stock",
                "actualizado_en",
            ]
        )

        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            subtotal=subtotal,
        )

        MovimientoProducto.objects.create(
            producto=producto,
            tipo=MovimientoProducto.SALIDA,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_resultante=producto.stock,
            motivo="Venta de producto",
            referencia=venta.numero or f"Venta #{venta.pk}",
            venta=venta,
            creado_por=usuario,
        )

        total += subtotal

    venta.total = total.quantize(CENTAVO)
    venta.save(update_fields=["total", "actualizado_en"])

    Ingreso.objects.create(
        venta=venta,
        monto=venta.total,
        metodo_pago=metodo_pago,
        referencia=(referencia_pago or "").strip(),
        registrado_por=usuario,
    )

    return venta


@transaction.atomic
def anular_venta(venta, usuario=None, motivo=""):
    """Anula una venta y devuelve sus productos al inventario."""

    try:
        venta_bloqueada = (
            Venta.objects
            .select_for_update()
            .get(pk=venta.pk)
        )
    except Venta.DoesNotExist:
        raise ValidationError("La venta indicada no existe.")

    if venta_bloqueada.estado == Venta.ESTADO_ANULADA:
        raise ValidationError(
            "La venta ya se encuentra anulada."
        )

    for detalle in venta_bloqueada.detalles.select_related("producto"):
        producto = (
            Producto.objects
            .select_for_update()
            .get(pk=detalle.producto_id)
        )
        stock_anterior = producto.stock
        producto.stock = stock_anterior + detalle.cantidad
        producto.save(
            update_fields=[
                "stock",
                "actualizado_en",
            ]
        )

        MovimientoProducto.objects.create(
            producto=producto,
            tipo=MovimientoProducto.ENTRADA,
            cantidad=detalle.cantidad,
            stock_anterior=stock_anterior,
            stock_resultante=producto.stock,
            motivo=motivo or "Anulación de venta",
            referencia=venta_bloqueada.numero or f"Venta #{venta_bloqueada.pk}",
            venta=venta_bloqueada,
            creado_por=usuario,
        )

    venta_bloqueada.estado = Venta.ESTADO_ANULADA
    venta_bloqueada.save(
        update_fields=["estado", "actualizado_en"]
    )

    return venta_bloqueada


@transaction.atomic
def crear_pedido(cliente, items, telefono="", direccion=""):
    """Create a pending customer order without reserving or changing stock."""
    cliente = _obtener_cliente(cliente)
    if not cliente.activo:
        raise ValidationError("No se puede crear un pedido para un cliente inactivo.")
    cantidades = _agrupar_items(items)
    productos = {p.pk: p for p in Producto.objects.filter(pk__in=cantidades, activo=True)}
    if len(productos) != len(cantidades):
        raise ValidationError("Uno de los productos ya no está disponible.")
    pedido = PedidoCliente.objects.create(
        cliente=cliente, telefono_contacto=telefono.strip(), direccion_entrega=direccion.strip(),
    )
    total = Decimal("0.00")
    for producto_id, cantidad in cantidades.items():
        producto = productos[producto_id]
        if cantidad > producto.stock:
            raise ValidationError(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}.")
        precio = Decimal(producto.precio).quantize(CENTAVO)
        subtotal = (precio * cantidad).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        DetallePedido.objects.create(pedido=pedido, producto=producto, cantidad=cantidad,
                                     precio_unitario=precio, subtotal=subtotal)
        total += subtotal
    pedido.total = total
    pedido.save(update_fields=["total", "actualizado_en"])
    return pedido


@transaction.atomic
def confirmar_pedido(pedido, usuario=None):
    """Idempotently convert a pending request through the official sale service."""
    try:
        pedido = PedidoCliente.objects.select_for_update().select_related("cliente").get(pk=pedido.pk)
    except PedidoCliente.DoesNotExist:
        raise ValidationError("El pedido indicado no existe.")
    if pedido.venta_id:
        return pedido.venta
    if pedido.estado != PedidoCliente.PENDIENTE:
        raise ValidationError("Solo se pueden confirmar pedidos pendientes.")
    items = [
        {"producto": detalle.producto_id, "cantidad": detalle.cantidad}
        for detalle in pedido.detalles.all()
    ]
    venta = registrar_venta(
        cliente=pedido.cliente, items=items, usuario=usuario,
        observaciones=f"Pedido web {pedido.numero}",
    )
    # registrar_venta usa los precios vigentes al confirmar; guardar el mismo total y desglose.
    pedido.total = venta.total
    ventas_por_producto = {d.producto_id: d for d in venta.detalles.all()}
    for detalle in pedido.detalles.all():
        venta_detalle = ventas_por_producto[detalle.producto_id]
        detalle.precio_unitario = venta_detalle.precio_unitario
        detalle.subtotal = venta_detalle.subtotal
        detalle.save(update_fields=["precio_unitario", "subtotal"])
    pedido.estado = PedidoCliente.CONFIRMADO
    pedido.venta = venta
    pedido.cambiado_por = usuario
    pedido.save(update_fields=["total", "estado", "venta", "cambiado_por", "actualizado_en"])
    return venta


@transaction.atomic
def cambiar_estado_pedido(pedido, estado, usuario=None):
    pedido = PedidoCliente.objects.select_for_update().get(pk=pedido.pk)
    if estado == PedidoCliente.CONFIRMADO:
        return confirmar_pedido(pedido, usuario)
    if estado == PedidoCliente.CANCELADO and pedido.estado == PedidoCliente.PENDIENTE:
        pedido.estado = estado
    elif estado == PedidoCliente.ENTREGADO and pedido.estado == PedidoCliente.CONFIRMADO and pedido.venta_id:
        pedido.estado = estado
    else:
        raise ValidationError("La transición solicitada no es válida.")
    pedido.cambiado_por = usuario
    pedido.save(update_fields=["estado", "cambiado_por", "actualizado_en"])
    return pedido
