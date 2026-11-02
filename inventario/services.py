from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Material, MovimientoInventario


@transaction.atomic
def registrar_movimiento(
    material_id,
    tipo,
    cantidad,
    motivo,
    usuario=None,
    referencia="",
):
    cantidad = Decimal(str(cantidad))

    if cantidad <= 0:
        raise ValidationError(
            "La cantidad debe ser mayor que cero."
        )

    material = (
        Material.objects
        .select_for_update()
        .get(pk=material_id)
    )

    stock_anterior = material.stock

    if tipo == MovimientoInventario.ENTRADA:
        stock_resultante = stock_anterior + cantidad

    elif tipo == MovimientoInventario.SALIDA:
        if cantidad > stock_anterior:
            raise ValidationError(
                f"Stock insuficiente. Disponible: "
                f"{stock_anterior} {material.get_unidad_medida_display()}."
            )

        stock_resultante = stock_anterior - cantidad

    else:
        raise ValidationError(
            "Tipo de movimiento inválido."
        )

    material.stock = stock_resultante
    material.save(
        update_fields=[
            "stock",
            "actualizado_en",
        ]
    )

    movimiento = MovimientoInventario.objects.create(
        material=material,
        tipo=tipo,
        cantidad=cantidad,
        stock_anterior=stock_anterior,
        stock_resultante=stock_resultante,
        motivo=motivo,
        referencia=referencia,
        creado_por=usuario,
    )

    return movimiento