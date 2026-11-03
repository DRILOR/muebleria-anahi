from datetime import date, datetime, time, timedelta

from django.utils import timezone


def parsear_fecha(valor, nombre_campo="fecha"):
    """Convierte una fecha ISO (YYYY-MM-DD) en ``date``.

    Devuelve ``None`` cuando el valor está vacío y lanza ``ValueError``
    con un mensaje entendible cuando el formato es inválido.
    """

    if not valor:
        return None

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    try:
        return datetime.strptime(
            str(valor).strip(),
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        raise ValueError(
            f"La {nombre_campo} debe tener el formato AAAA-MM-DD."
        )


def rango_fechas(desde=None, hasta=None):
    """Devuelve un rango aware ``[inicio, fin)`` para filtrar por fecha."""

    fecha_desde = parsear_fecha(desde, "fecha inicial")
    fecha_hasta = parsear_fecha(hasta, "fecha final")

    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise ValueError(
            "La fecha inicial no puede ser mayor que la fecha final."
        )

    inicio = (
        timezone.make_aware(
            datetime.combine(fecha_desde, time.min)
        )
        if fecha_desde
        else None
    )

    fin = (
        timezone.make_aware(
            datetime.combine(
                fecha_hasta + timedelta(days=1),
                time.min,
            )
        )
        if fecha_hasta
        else None
    )

    return inicio, fin


def fecha_actual():
    return timezone.localdate()


def primer_dia_mes(fecha=None):
    fecha = fecha or fecha_actual()
    return fecha.replace(day=1)
