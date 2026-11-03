"""Motor conversacional determinista de AnahíBot.

El asistente responde únicamente con información consultada en la base de
datos. No genera cifras, productos ni proveedores que no existan y distingue
explícitamente entre un dato inexistente y un valor registrado en cero.
"""

import re
import unicodedata
from datetime import timedelta
from decimal import Decimal
from functools import reduce
from operator import or_

from django.db.models import F, Q
from django.utils import timezone

from compras.models import DetalleCompra, Proveedor
from inventario.models import Material, Producto
from reportes.services import (
    productos_mas_vendidos,
    reporte_inventario,
    resumen_ventas,
)
from ventas.utils import rango_fechas


MAX_MENSAJE = 500

PALABRAS_IGNORADAS = {
    "al",
    "algo",
    "articulo",
    "articulos",
    "actual",
    "ayuda",
    "busca",
    "buscar",
    "busco",
    "catalogo",
    "como",
    "con",
    "cual",
    "cuales",
    "cuando",
    "cuanta",
    "cuantas",
    "cuanto",
    "cuantos",
    "cuesta",
    "cuestan",
    "de",
    "del",
    "dame",
    "disponible",
    "disponibles",
    "donde",
    "el",
    "en",
    "es",
    "esta",
    "estan",
    "favor",
    "gracias",
    "adios",
    "ok",
    "vale",
    "perfecto",
    "hay",
    "historial",
    "historico",
    "info",
    "informacion",
    "inventario",
    "la",
    "las",
    "lista",
    "listar",
    "los",
    "me",
    "mi",
    "muestra",
    "mueble",
    "muebles",
    "necesito",
    "o",
    "para",
    "por",
    "precio",
    "precios",
    "producto",
    "productos",
    "proveedor",
    "proveedores",
    "compra",
    "compras",
    "reporte",
    "reportes",
    "recomendacion",
    "recomendaciones",
    "ingreso",
    "ingresos",
    "venta",
    "ventas",
    "puedes",
    "puedo",
    "que",
    "quiero",
    "registrado",
    "registrados",
    "registrada",
    "registradas",
    "sabes",
    "sin",
    "sistema",
    "sobre",
    "son",
    "stock",
    "su",
    "sus",
    "tiene",
    "tienen",
    "tu",
    "un",
    "una",
    "unos",
    "unas",
    "ver",
    "y",
}

SALUDOS = {
    "hola",
    "buenas",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "hey",
    "hi",
}

SUGERENCIAS_BASE = [
    "¿Qué productos tienen stock bajo?",
    "¿Qué me recomiendas reponer?",
]


def normalizar(texto):
    """Pasa el texto a minúsculas y elimina tildes y espacios repetidos."""

    descompuesto = unicodedata.normalize("NFKD", str(texto or "").lower())
    sin_tildes = "".join(
        caracter
        for caracter in descompuesto
        if not unicodedata.combining(caracter)
    )
    return re.sub(r"\s+", " ", sin_tildes).strip()


def _palabras(texto):
    return re.findall(r"[a-z0-9]+", normalizar(texto))


def _singular(palabra):
    if palabra.endswith("ces") and len(palabra) > 4:
        return f"{palabra[:-3]}z"
    if palabra.endswith("es") and len(palabra) > 4:
        return palabra[:-2]
    if palabra.endswith("s") and len(palabra) > 3:
        return palabra[:-1]
    return palabra


def _terminos(texto):
    terminos = set()

    for palabra in _palabras(texto):
        if palabra.isdigit() or len(palabra) < 3:
            continue
        if palabra in PALABRAS_IGNORADAS:
            continue

        terminos.add(palabra)
        singular = _singular(palabra)

        if len(singular) >= 3:
            terminos.add(singular)

    return terminos


def formato_moneda(valor):
    return f"Bs {Decimal(valor):.2f}".replace(".", ",")


def _cantidad(valor):
    return f"{Decimal(valor):.2f}".replace(".", ",")


def _estado_producto(producto):
    if producto.stock == 0:
        return "Agotado"
    if producto.stock <= producto.stock_minimo:
        return "Stock bajo"
    return "Disponible"


def _estado_material(material):
    if material.stock == 0:
        return "Agotado"
    if material.stock <= material.stock_minimo:
        return "Stock bajo"
    return "Disponible"


def _sugerencias(usuario):
    sugerencias = []

    producto = (
        Producto.objects
        .filter(activo=True)
        .order_by("nombre")
        .first()
    )

    if producto:
        sugerencias.append(f"¿Cuánto cuesta {producto.nombre}?")

    sugerencias.extend(SUGERENCIAS_BASE)

    if getattr(usuario, "is_staff", False):
        sugerencias.extend(
            [
                "¿Cuánto vendí este mes?",
                "¿Qué productos se vendieron más?",
                "Proveedores registrados",
            ]
        )

    return sugerencias[:5]


def _resultado(texto, intencion, usuario):
    return {
        "respuesta": texto,
        "intencion": intencion,
        "sugerencias": _sugerencias(usuario),
    }


def sugerencias_iniciales(usuario):
    """Sugerencias de ejemplo construidas con datos reales del catálogo."""

    return _sugerencias(usuario)


def _sin_permiso(tema, usuario):
    return _resultado(
        (
            f"Para consultar {tema} necesitas permisos de administración. "
            "Tu usuario está autenticado, pero no tiene acceso a esa "
            "información. No mostraré datos sensibles sin permiso."
        ),
        "permiso_denegado",
        usuario,
    )


def _detalle_producto(producto):
    lineas = [
        f"{producto.nombre} ({producto.codigo})",
        f"Categoría: {producto.categoria.nombre}",
        f"Precio registrado: {formato_moneda(producto.precio)}",
        (
            f"Stock: {producto.stock} unidad(es) · "
            f"{_estado_producto(producto)}"
        ),
        f"Stock mínimo configurado: {producto.stock_minimo}.",
    ]

    if not producto.activo:
        lineas.append(
            "El producto está inactivo en el catálogo y no se ofrece "
            "para la venta."
        )

    if producto.stock == 0:
        lineas.append(
            "El producto existe y su stock registrado es cero: "
            "no hay unidades disponibles."
        )

    return "\n".join(lineas)


def _detalle_material(material):
    lineas = [
        f"{material.nombre} ({material.codigo})",
        f"Tipo: material · Unidad: {material.get_unidad_medida_display()}",
        f"Stock: {_cantidad(material.stock)} · {_estado_material(material)}",
        f"Stock mínimo: {_cantidad(material.stock_minimo)}",
        f"Costo de referencia: {formato_moneda(material.costo_referencia)}",
    ]

    if not material.activo:
        lineas.append("El material está inactivo en el catálogo.")

    if material.stock == 0:
        lineas.append(
            "El material existe y su stock registrado es cero: "
            "no hay existencias disponibles."
        )

    return "\n".join(lineas)


def _buscar_productos(texto):
    normalizado = normalizar(texto)

    codigo = re.search(r"\b([a-z]{2,6}-?\d{2,6})\b", normalizado)
    if codigo:
        exactos = list(
            Producto.objects
            .select_related("categoria")
            .filter(codigo__iexact=codigo.group(1))
        )
        if exactos:
            return exactos

    terminos = _terminos(normalizado)
    if not terminos:
        return []

    consulta = reduce(
        or_,
        [
            Q(nombre__icontains=termino)
            | Q(codigo__icontains=termino)
            | Q(categoria__nombre__icontains=termino)
            for termino in terminos
        ],
    )

    candidatos = (
        Producto.objects
        .select_related("categoria")
        .filter(consulta)
        .order_by("nombre")[:100]
    )

    puntuados = []
    for producto in candidatos:
        contenido = normalizar(
            f"{producto.codigo} {producto.nombre} "
            f"{producto.categoria.nombre}"
        )
        puntaje = sum(
            1 for termino in terminos if termino in contenido
        )
        if puntaje:
            puntuados.append((puntaje, producto))

    if not puntuados:
        return []

    mejor = max(puntaje for puntaje, _ in puntuados)
    return [
        producto
        for puntaje, producto in puntuados
        if puntaje == mejor
    ]


def _buscar_materiales(texto):
    normalizado = normalizar(texto)

    codigo = re.search(r"\b([a-z]{2,6}-?\d{2,6})\b", normalizado)
    if codigo:
        exactos = list(
            Material.objects.filter(codigo__iexact=codigo.group(1))
        )
        if exactos:
            return exactos

    terminos = _terminos(normalizado)
    if not terminos:
        return []

    consulta = reduce(
        or_,
        [
            Q(nombre__icontains=termino)
            | Q(codigo__icontains=termino)
            for termino in terminos
        ],
    )

    candidatos = (
        Material.objects
        .filter(consulta)
        .order_by("nombre")[:100]
    )

    puntuados = []
    for material in candidatos:
        contenido = normalizar(f"{material.codigo} {material.nombre}")
        puntaje = sum(
            1 for termino in terminos if termino in contenido
        )
        if puntaje:
            puntuados.append((puntaje, material))

    if not puntuados:
        return []

    mejor = max(puntaje for puntaje, _ in puntuados)
    return [
        material
        for puntaje, material in puntuados
        if puntaje == mejor
    ]


def _respuesta_producto(texto, usuario):
    productos = _buscar_productos(texto)

    if productos:
        if len(productos) > 1:
            lineas = [
                (
                    f"Encontré {len(productos)} productos que coinciden. "
                    "Indícame el código o un nombre más exacto:"
                )
            ]
            for producto in productos[:5]:
                lineas.append(
                    f"- {producto.nombre} ({producto.codigo}) · "
                    f"{formato_moneda(producto.precio)} · "
                    f"stock {producto.stock}"
                )
            if len(productos) > 5:
                lineas.append(f"… y {len(productos) - 5} más.")
            return _resultado("\n".join(lineas), "producto_ambigüo", usuario)

        return _resultado(
            _detalle_producto(productos[0]),
            "producto",
            usuario,
        )

    materiales = _buscar_materiales(texto)

    if materiales:
        if len(materiales) > 1:
            lineas = [
                (
                    f"Encontré {len(materiales)} materiales que coinciden. "
                    "Indícame el código o un nombre más exacto:"
                )
            ]
            for material in materiales[:5]:
                lineas.append(
                    f"- {material.nombre} ({material.codigo}) · "
                    f"stock {_cantidad(material.stock)}"
                )
            if len(materiales) > 5:
                lineas.append(f"… y {len(materiales) - 5} más.")
            return _resultado("\n".join(lineas), "material_ambigüo", usuario)

        return _resultado(
            _detalle_material(materiales[0]),
            "material",
            usuario,
        )

    terminos = _terminos(texto)
    consulta = " ".join(sorted(terminos)) or texto.strip()

    return _resultado(
        (
            f"No encontré ningún producto ni material que coincida con "
            f"«{consulta}». No hay datos registrados para esa búsqueda; "
            "verifica el nombre o el código."
        ),
        "sin_resultados",
        usuario,
    )


def _lista_stock_bajo(usuario):
    productos = list(
        Producto.objects
        .filter(activo=True, stock__lte=F("stock_minimo"))
        .order_by("stock", "nombre")
    )
    materiales = list(
        Material.objects
        .filter(activo=True, stock__lte=F("stock_minimo"))
        .order_by("stock", "nombre")
    )

    if not productos and not materiales:
        return _resultado(
            (
                "No hay productos ni materiales activos con stock bajo "
                "o agotado en este momento (0 registros)."
            ),
            "stock_bajo",
            usuario,
        )

    lineas = ["Registros que requieren reposición (datos reales):"]

    if productos:
        lineas.append("Productos:")
        for producto in productos[:10]:
            estado = (
                "agotado"
                if producto.stock == 0
                else (
                    f"stock {producto.stock}, "
                    f"mínimo {producto.stock_minimo}"
                )
            )
            lineas.append(
                f"- {producto.nombre} ({producto.codigo}): {estado}"
            )
        if len(productos) > 10:
            lineas.append(f"… y {len(productos) - 10} productos más.")

    if materiales:
        lineas.append("Materiales:")
        for material in materiales[:10]:
            estado = (
                "agotado"
                if material.stock == 0
                else (
                    f"stock {_cantidad(material.stock)}, "
                    f"mínimo {_cantidad(material.stock_minimo)}"
                )
            )
            lineas.append(
                f"- {material.nombre} ({material.codigo}): {estado}"
            )
        if len(materiales) > 10:
            lineas.append(f"… y {len(materiales) - 10} materiales más.")

    return _resultado("\n".join(lineas), "stock_bajo", usuario)


def _lista_agotados(usuario):
    productos = list(
        Producto.objects
        .filter(activo=True, stock=0)
        .order_by("nombre")
    )
    materiales = list(
        Material.objects
        .filter(activo=True, stock=0)
        .order_by("nombre")
    )

    if not productos and not materiales:
        return _resultado(
            (
                "No hay productos ni materiales activos agotados en este "
                "momento (0 registros)."
            ),
            "agotados",
            usuario,
        )

    lineas = ["Registros agotados (stock registrado en cero):"]

    if productos:
        lineas.append("Productos:")
        lineas.extend(
            f"- {producto.nombre} ({producto.codigo})"
            for producto in productos[:10]
        )
        if len(productos) > 10:
            lineas.append(f"… y {len(productos) - 10} productos más.")

    if materiales:
        lineas.append("Materiales:")
        lineas.extend(
            f"- {material.nombre} ({material.codigo})"
            for material in materiales[:10]
        )
        if len(materiales) > 10:
            lineas.append(f"… y {len(materiales) - 10} materiales más.")

    return _resultado("\n".join(lineas), "agotados", usuario)


def _resumen_inventario(usuario):
    datos = reporte_inventario()
    productos = datos["resumen_productos"]
    materiales = datos["resumen_materiales"]

    if not productos["total"] and not materiales["total"]:
        return _resultado(
            (
                "No hay productos ni materiales activos registrados en el "
                "inventario (0 registros)."
            ),
            "inventario",
            usuario,
        )

    lineas = [
        "Inventario actual (solo registros activos):",
        (
            f"- Productos: {productos['total']} registrados · "
            f"{productos['agotados']} agotados · "
            f"{productos['bajos']} con stock bajo · "
            f"{productos['disponibles']} disponibles."
        ),
        (
            f"- Materiales: {materiales['total']} registrados · "
            f"{materiales['agotados']} agotados · "
            f"{materiales['bajos']} con stock bajo · "
            f"{materiales['disponibles']} disponibles."
        ),
        (
            f"- Valor del inventario de productos: "
            f"{formato_moneda(productos['valor'])}."
        ),
        (
            f"- Valor del inventario de materiales: "
            f"{formato_moneda(materiales['valor'])}."
        ),
    ]

    return _resultado("\n".join(lineas), "inventario", usuario)


def _lista_productos(usuario):
    productos = Producto.objects.filter(activo=True).order_by("nombre")
    total = productos.count()

    if not total:
        return _resultado(
            "No hay productos activos registrados en el catálogo (0).",
            "catalogo",
            usuario,
        )

    lineas = [f"Hay {total} producto(s) activo(s) en el catálogo:"]

    for producto in productos[:10]:
        lineas.append(
            f"- {producto.nombre} ({producto.codigo}) · "
            f"{formato_moneda(producto.precio)} · "
            f"stock {producto.stock} · {_estado_producto(producto)}"
        )

    if total > 10:
        lineas.append(f"… y {total - 10} producto(s) más.")

    return _resultado("\n".join(lineas), "catalogo", usuario)


def _respuesta_inventario(texto, usuario):
    if re.search(r"\bagotad|\bsin stock|\bno hay stock", texto):
        return _lista_agotados(usuario)

    if (
        "stock bajo" in texto
        or "bajo stock" in texto
        or "reponer" in texto
        or "reposicion" in texto
    ):
        return _lista_stock_bajo(usuario)

    if "inventario" in texto:
        return _resumen_inventario(usuario)

    return _lista_productos(usuario)


def _periodo_consulta(texto):
    hoy = timezone.localdate()
    desde = None
    hasta = None
    etiqueta = "este mes"

    if re.search(r"\bhoy\b", texto):
        desde = hasta = hoy
        etiqueta = "hoy"
    elif re.search(r"\bayer\b", texto):
        desde = hasta = hoy - timedelta(days=1)
        etiqueta = "ayer"
    elif re.search(r"\bsemanas?\b", texto):
        desde = hoy - timedelta(days=6)
        hasta = hoy
        etiqueta = "los últimos 7 días"
    elif re.search(r"\banos?\b", texto):
        desde = hoy.replace(month=1, day=1)
        hasta = hoy
        etiqueta = "este año"
    elif re.search(r"\bmes(es)?\b", texto):
        desde = hoy.replace(day=1)
        hasta = hoy
        etiqueta = "este mes"
    elif any(
        palabra in texto
        for palabra in (
            "historico",
            "historial",
            "totales",
            "todas",
            "todos",
            "siempre",
        )
    ):
        etiqueta = "el histórico completo"

    inicio, fin = rango_fechas(
        desde.isoformat() if desde else None,
        hasta.isoformat() if hasta else None,
    )

    return inicio, fin, etiqueta


def _respuesta_ventas(texto, usuario):
    if not getattr(usuario, "is_staff", False):
        return _sin_permiso("ventas, ingresos y reportes", usuario)

    inicio, fin, etiqueta = _periodo_consulta(texto)

    if (
        "mas vendido" in texto
        or "mas vendidos" in texto
        or ("top" in texto and "vendid" in texto)
        or (
            "mas" in _palabras(texto)
            and (
                "vendid" in texto
                or "vendier" in texto
            )
        )
    ):
        productos = productos_mas_vendidos(inicio, fin, limite=5)

        if not productos:
            return _resultado(
                (
                    f"No hay productos vendidos en {etiqueta} "
                    "(0 unidades). El dato es cero, no un error de lectura."
                ),
                "productos_mas_vendidos",
                usuario,
            )

        lineas = [f"Productos más vendidos en {etiqueta}:"]
        for indice, producto in enumerate(productos, start=1):
            lineas.append(
                f"{indice}. {producto['nombre']} "
                f"({producto['codigo']}) · "
                f"{producto['cantidad']} unidad(es) · "
                f"{formato_moneda(producto['ingresos'])}"
            )

        return _resultado(
            "\n".join(lineas),
            "productos_mas_vendidos",
            usuario,
        )

    resumen = resumen_ventas(inicio, fin)

    if resumen["cantidad"] == 0:
        return _resultado(
            (
                f"No hay ventas completadas registradas en {etiqueta}. "
                f"Total: {formato_moneda(resumen['total'])}. "
                "El dato es cero, no un error de lectura."
            ),
            "ventas",
            usuario,
        )

    lineas = [
        f"Ventas completadas en {etiqueta}: {resumen['cantidad']}",
        f"- Ingresos: {formato_moneda(resumen['total'])}",
        f"- Ticket promedio: {formato_moneda(resumen['promedio'])}",
        f"- Unidades vendidas: {resumen['unidades']}",
        (
            f"- Ventas anuladas: {resumen['anuladas_cantidad']} · "
            f"{formato_moneda(resumen['anuladas_total'])}"
        ),
    ]

    return _resultado("\n".join(lineas), "ventas", usuario)


def _respuesta_proveedores(texto, usuario):
    if not getattr(usuario, "is_staff", False):
        return _sin_permiso("proveedores y compras", usuario)

    materiales = _buscar_materiales(texto)

    if materiales:
        lineas = []

        for material in materiales[:3]:
            lineas.append(
                f"{material.nombre} ({material.codigo}):"
            )

            detalles = list(
                DetalleCompra.objects
                .filter(material=material)
                .select_related("compra__proveedor")
                .order_by("-compra__fecha")
            )

            if not detalles:
                lineas.append(
                    "  El material existe, pero no tiene compras "
                    "registradas (0 compras); por eso no hay proveedor "
                    "asociado en el sistema."
                )
                continue

            proveedores = {}

            for detalle in detalles:
                proveedor = detalle.compra.proveedor
                registro = proveedores.setdefault(
                    proveedor.pk,
                    {
                        "proveedor": proveedor,
                        "compras": 0,
                        "ultima": detalle.compra.fecha,
                    },
                )
                registro["compras"] += 1
                if detalle.compra.fecha > registro["ultima"]:
                    registro["ultima"] = detalle.compra.fecha

            for registro in proveedores.values():
                proveedor = registro["proveedor"]
                contacto = " · ".join(
                    valor
                    for valor in (
                        proveedor.telefono,
                        proveedor.email,
                    )
                    if valor
                )
                detalle_contacto = (
                    f" · {contacto}" if contacto else ""
                )
                ultima = timezone.localtime(
                    registro["ultima"]
                ).strftime("%d/%m/%Y")
                lineas.append(
                    f"  - {proveedor.nombre} · "
                    f"{registro['compras']} compra(s) · "
                    f"última: {ultima}{detalle_contacto}"
                )

        return _resultado("\n".join(lineas), "proveedores", usuario)

    terminos = _terminos(texto)

    if terminos:
        consulta = " ".join(sorted(terminos))
        return _resultado(
            (
                f"No encontré ningún material que coincida con "
                f"«{consulta}». Sin ese dato no puedo asociar proveedores."
            ),
            "proveedores_sin_resultados",
            usuario,
        )

    proveedores = Proveedor.objects.filter(activo=True).order_by("nombre")

    if not proveedores.exists():
        return _resultado(
            "No hay proveedores activos registrados (0).",
            "proveedores",
            usuario,
        )

    lineas = ["Proveedores activos registrados:"]
    for proveedor in proveedores:
        contacto = " · ".join(
            valor
            for valor in (
                proveedor.nit,
                proveedor.telefono,
                proveedor.email,
            )
            if valor
        )
        detalle_contacto = f" · {contacto}" if contacto else ""
        lineas.append(f"- {proveedor.nombre}{detalle_contacto}")

    return _resultado("\n".join(lineas), "proveedores", usuario)


def _respuesta_recomendaciones(usuario):
    productos = list(
        Producto.objects
        .filter(activo=True, stock__lte=F("stock_minimo"))
        .order_by("stock", "nombre")[:8]
    )

    lineas = ["Recomendaciones basadas en datos reales del sistema:"]

    if productos:
        lineas.append("Reponer o revisar:")
        for producto in productos:
            if producto.stock == 0:
                estado = "agotado"
            else:
                estado = (
                    f"stock {producto.stock}, "
                    f"mínimo {producto.stock_minimo}"
                )
            lineas.append(
                f"- {producto.nombre} ({producto.codigo}): {estado}"
            )
    else:
        lineas.append(
            "No hay productos activos con stock bajo o agotado (0)."
        )

    if getattr(usuario, "is_staff", False):
        inicio, fin, etiqueta = _periodo_consulta("este mes")
        mas_vendidos = productos_mas_vendidos(inicio, fin, limite=3)

        if mas_vendidos:
            lineas.append(f"Priorizar ventas de {etiqueta}:")
            for producto in mas_vendidos:
                lineas.append(
                    f"- {producto['nombre']} ({producto['codigo']}) · "
                    f"{producto['cantidad']} unidad(es) vendidas"
                )
        else:
            lineas.append(
                f"No hay ventas completadas en {etiqueta} para priorizar "
                "productos (0)."
            )

    return _resultado(
        "\n".join(lineas),
        "recomendaciones",
        usuario,
    )


def _respuesta_ayuda(usuario):
    lineas = [
        (
            "Soy AnahíBot y consulto información real del sistema. "
            "Puedo ayudarte con:"
        ),
        "- Precio, stock y estado de un producto por nombre o código.",
        "- Stock bajo, productos agotados y resumen del inventario.",
        "- Stock y costo de referencia de materiales.",
        "- Recomendaciones de reposición según los datos registrados.",
    ]

    if getattr(usuario, "is_staff", False):
        lineas.extend(
            [
                "- Ventas, ingresos y ticket promedio por periodo.",
                "- Productos más vendidos.",
                "- Proveedores registrados y proveedores de un material.",
            ]
        )
    else:
        lineas.append(
            "Las consultas de ventas, ingresos y proveedores requieren "
            "permisos de administración."
        )

    lineas.append(
        "No invento datos: si un registro no existe te lo digo y si un "
        "valor está en cero también."
    )

    return _resultado("\n".join(lineas), "ayuda", usuario)


def _es_saludo(texto):
    if texto in SALUDOS:
        return True

    if len(texto.split()) > 3:
        return False

    return bool(
        re.match(
            r"^(hola|buen[oa]s? (dias|tardes|noches)|hey|hi)\b",
            texto,
        )
    )


def _es_ayuda(texto):
    return any(
        frase in texto
        for frase in (
            "ayuda",
            "que puedes hacer",
            "como funciona",
            "comandos",
            "opciones",
            "que sabes",
        )
    )


def _es_recomendacion(texto):
    return any(
        frase in texto
        for frase in (
            "recomiend",
            "recomendacion",
            "sugerencia",
            "sugerencias",
            "que comprar",
            "que reponer",
        )
    )


def _es_inventario(texto):
    return any(
        frase in texto
        for frase in (
            "inventario",
            "stock bajo",
            "bajo stock",
            "agotad",
            "sin stock",
            "reponer",
            "reposicion",
        )
    )


def _es_ventas(texto):
    return any(
        frase in texto
        for frase in (
            "venta",
            "vendi",
            "vendid",
            "ingreso",
            "factur",
            "recaudad",
            "caja",
            "reporte",
        )
    )


def responder_mensaje(mensaje, usuario=None):
    """Devuelve la respuesta de AnahíBot para un mensaje del usuario."""

    texto = normalizar(mensaje)

    if not texto:
        return _respuesta_ayuda(usuario)

    if _es_saludo(texto):
        return _resultado(
            (
                "¡Hola! Soy AnahíBot. Consulto inventario, precios, "
                "proveedores y ventas directamente de la base de datos. "
                "¿Qué necesitas saber?"
            ),
            "saludo",
            usuario,
        )

    if _es_ayuda(texto):
        return _respuesta_ayuda(usuario)

    if _es_recomendacion(texto):
        return _respuesta_recomendaciones(usuario)

    if "proveedor" in texto:
        return _respuesta_proveedores(texto, usuario)

    if _es_inventario(texto):
        return _respuesta_inventario(texto, usuario)

    if _es_ventas(texto):
        return _respuesta_ventas(texto, usuario)

    if _terminos(texto) or re.search(
        r"\b([a-z]{2,6}-?\d{2,6})\b",
        texto,
    ):
        return _respuesta_producto(texto, usuario)

    if "producto" in texto or "catalogo" in texto:
        return _lista_productos(usuario)

    if "stock" in texto:
        return _resumen_inventario(usuario)

    return _resultado(
        (
            "No entendí la consulta y no voy a inventar una respuesta. "
            "Puedo buscar precios y stock de productos, revisar el "
            "inventario o, si eres administrador, consultar ventas y "
            "proveedores. Escribe «ayuda» para ver las opciones."
        ),
        "no_entendido",
        usuario,
    )
