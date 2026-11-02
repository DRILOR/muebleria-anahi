from decimal import Decimal

from django.db import transaction

from inventario.models import MovimientoInventario
from inventario.services import registrar_movimiento

from .models import Compra, DetalleCompra


@transaction.atomic
def registrar_compra(
    proveedor,
    detalles,
    usuario,
    numero_documento="",
    observaciones="",
):
    compra = Compra.objects.create(
        proveedor=proveedor,
        numero_documento=numero_documento,
        observaciones=observaciones,
        creado_por=usuario,
    )

    total = Decimal("0")

    for item in detalles:
        material = item["material"]
        cantidad = item["cantidad"]
        costo = item["costo_unitario"]

        DetalleCompra.objects.create(
            compra=compra,
            material=material,
            cantidad=cantidad,
            costo_unitario=costo,
        )

        total += cantidad * costo

        registrar_movimiento(
            material_id=material.pk,
            tipo=MovimientoInventario.ENTRADA,
            cantidad=cantidad,
            motivo="Compra de material",
            referencia=f"Compra #{compra.pk}",
            usuario=usuario,
        )

    compra.total = total

    compra.save(
        update_fields=["total"]
    )

    return compra