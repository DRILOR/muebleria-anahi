from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BROWN = colors.HexColor("#69452d")
BROWN_DARK = colors.HexColor("#49301f")
CREAM = colors.HexColor("#f6f1ea")
MUTED = colors.HexColor("#756b64")
RED = colors.HexColor("#a63d40")


def _paragraph(texto, estilo):
    return Paragraph(escape(str(texto)), estilo)


def generar_comprobante_pdf(venta):
    """Genera el comprobante de venta en PDF y devuelve sus bytes."""

    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Comprobante {venta.numero or venta.pk}",
        author="Mueblería Anahí",
    )

    estilos = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloAnahi",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=BROWN_DARK,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    subtitulo = ParagraphStyle(
        "SubtituloAnahi",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    etiqueta = ParagraphStyle(
        "EtiquetaAnahi",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=BROWN,
    )
    valor = ParagraphStyle(
        "ValorAnahi",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.black,
    )
    celda = ParagraphStyle(
        "CeldaAnahi",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
    )
    celda_derecha = ParagraphStyle(
        "CeldaDerechaAnahi",
        parent=celda,
        alignment=TA_RIGHT,
    )
    celda_centro = ParagraphStyle(
        "CeldaCentroAnahi",
        parent=celda,
        alignment=TA_CENTER,
    )
    encabezado = ParagraphStyle(
        "EncabezadoAnahi",
        parent=celda,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    encabezado_derecha = ParagraphStyle(
        "EncabezadoDerechaAnahi",
        parent=encabezado,
        alignment=TA_RIGHT,
    )
    encabezado_centro = ParagraphStyle(
        "EncabezadoCentroAnahi",
        parent=encabezado,
        alignment=TA_CENTER,
    )
    total_estilo = ParagraphStyle(
        "TotalAnahi",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=BROWN_DARK,
        alignment=TA_RIGHT,
    )

    elementos = [
        Paragraph("MUEBLERÍA ANAHÍ", titulo),
        Paragraph(
            "Carpintería y muebles a medida · Yacuiba, Bolivia",
            subtitulo,
        ),
    ]

    if venta.esta_anulada:
        anulada = ParagraphStyle(
            "Anulada",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=RED,
            alignment=TA_CENTER,
        )
        elementos.append(
            Paragraph("*** VENTA ANULADA ***", anulada)
        )
        elementos.append(Spacer(1, 8))

    fecha_local = timezone.localtime(venta.fecha)

    datos_venta = [
        [
            _paragraph("N° de comprobante", etiqueta),
            _paragraph(venta.numero or f"Venta #{venta.pk}", valor),
            _paragraph("Fecha", etiqueta),
            _paragraph(fecha_local.strftime("%d/%m/%Y %H:%M"), valor),
        ],
        [
            _paragraph("Cliente", etiqueta),
            _paragraph(venta.cliente.nombre, valor),
            _paragraph("NIT / Documento", etiqueta),
            _paragraph(venta.cliente.nit or "Sin registro", valor),
        ],
        [
            _paragraph("Teléfono", etiqueta),
            _paragraph(venta.cliente.telefono or "Sin registro", valor),
            _paragraph("Atendido por", etiqueta),
            _paragraph(
                venta.creado_por.get_username()
                if venta.creado_por
                else "Sistema",
                valor,
            ),
        ],
    ]

    tabla_datos = Table(
        datos_venta,
        colWidths=[3.4 * cm, 6.5 * cm, 3.4 * cm, 4.4 * cm],
    )
    tabla_datos.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CREAM),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#ded6cd")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ded6cd")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    elementos.extend(
        [
            tabla_datos,
            Spacer(1, 14),
            Paragraph("DETALLE DE PRODUCTOS", etiqueta),
            Spacer(1, 5),
        ]
    )

    filas = [
        [
            _paragraph("Producto", encabezado),
            _paragraph("Cantidad", encabezado_centro),
            _paragraph("Precio unitario", encabezado_derecha),
            _paragraph("Subtotal", encabezado_derecha),
        ]
    ]

    for detalle in venta.detalles.all():
        filas.append(
            [
                _paragraph(
                    f"{detalle.producto.codigo} - "
                    f"{detalle.producto.nombre}",
                    celda,
                ),
                _paragraph(detalle.cantidad, celda_centro),
                _paragraph(f"Bs {detalle.precio_unitario:.2f}", celda_derecha),
                _paragraph(f"Bs {detalle.subtotal:.2f}", celda_derecha),
            ]
        )

    tabla_detalle = Table(
        filas,
        colWidths=[8.6 * cm, 2.4 * cm, 3.3 * cm, 3.4 * cm],
        repeatRows=1,
    )
    tabla_detalle.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BROWN),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#ded6cd")),
                ("INNERGRID", (0, 1), (-1, -1), 0.25, colors.HexColor("#ded6cd")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CREAM]),
            ]
        )
    )

    elementos.extend(
        [
            tabla_detalle,
            Spacer(1, 10),
            Paragraph(f"TOTAL: Bs {venta.total:.2f}", total_estilo),
        ]
    )

    if hasattr(venta, "ingreso") and venta.ingreso:
        metodo = venta.ingreso.get_metodo_pago_display()
        referencia = (
            f" · Ref. {venta.ingreso.referencia}"
            if venta.ingreso.referencia
            else ""
        )
        elementos.append(
            Paragraph(
                f"Método de pago: {metodo}{referencia}",
                subtitulo,
            )
        )

    if venta.observaciones:
        elementos.extend(
            [
                Spacer(1, 6),
                Paragraph("Observaciones", etiqueta),
                Paragraph(escape(venta.observaciones), valor),
            ]
        )

    elementos.extend(
        [
            Spacer(1, 24),
            Paragraph(
                "Gracias por confiar en Mueblería Anahí. "
                "Este comprobante respalda su compra.",
                subtitulo,
            ),
        ]
    )

    documento.build(elementos)

    return buffer.getvalue()
