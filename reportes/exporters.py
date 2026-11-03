from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
BORDER = colors.HexColor("#ded6cd")
MUTED = colors.HexColor("#756b64")


def _e(texto):
    return escape(str(texto))


def _estilo_celda(alineacion="left"):
    estilos = getSampleStyleSheet()
    return ParagraphStyle(
        f"celda_{alineacion}",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=7.6,
        leading=9.5,
        alignment={
            "left": TA_LEFT,
            "center": TA_CENTER,
            "right": TA_RIGHT,
        }.get(alineacion, TA_LEFT),
    )


def _pie_de_pagina(canvas, documento):
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(
        documento.leftMargin,
        1.15 * cm,
        A4[0] - documento.rightMargin,
        1.15 * cm,
    )
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        documento.leftMargin,
        0.8 * cm,
        "Mueblería Anahí · Sistema Inteligente de Gestión de Inventario",
    )
    canvas.drawRightString(
        A4[0] - documento.rightMargin,
        0.8 * cm,
        f"Página {documento.page}",
    )
    canvas.restoreState()


def generar_pdf_reporte(reporte):
    """Genera un PDF profesional a partir de la estructura del reporte."""

    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.35 * cm,
        bottomMargin=1.5 * cm,
        title=reporte.get("titulo", "Reporte"),
        author="Mueblería Anahí",
        pageCompression=0,
    )

    estilos = getSampleStyleSheet()

    titulo_empresa = ParagraphStyle(
        "empresa",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    titulo_reporte = ParagraphStyle(
        "titulo_reporte",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    periodo = ParagraphStyle(
        "periodo",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=MUTED,
    )
    etiqueta = ParagraphStyle(
        "etiqueta",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=MUTED,
    )
    valor = ParagraphStyle(
        "valor",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=BROWN_DARK,
    )
    seccion = ParagraphStyle(
        "seccion",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=BROWN_DARK,
        spaceBefore=8,
        spaceAfter=5,
    )
    vacio = ParagraphStyle(
        "vacio",
        parent=estilos["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceBefore=6,
        spaceAfter=6,
    )
    nota = ParagraphStyle(
        "nota",
        parent=estilos["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=MUTED,
        spaceBefore=6,
    )
    encabezado = ParagraphStyle(
        "encabezado",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.6,
        leading=9.5,
        textColor=colors.white,
        alignment=TA_LEFT,
    )

    disponibles = A4[0] - documento.leftMargin - documento.rightMargin

    elementos = []

    cabecera = Table(
        [
            [
                Paragraph("MUEBLERÍA ANAHÍ", titulo_empresa),
                Paragraph(
                    _e(reporte.get("titulo", "Reporte")),
                    titulo_reporte,
                ),
            ]
        ],
        colWidths=[disponibles * .58, disponibles * .42],
    )
    cabecera.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BROWN),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 10),
                ("RIGHTPADDING", (1, 0), (1, 0), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    elementos.append(cabecera)
    elementos.append(Spacer(1, 8))
    elementos.append(
        Paragraph(_e(reporte.get("subtitulo", "")), periodo)
    )
    elementos.append(Spacer(1, 6))

    metadatos = reporte.get("metadatos") or []

    if metadatos:
        filas_meta = []
        for indice in range(0, len(metadatos), 2):
            par = metadatos[indice:indice + 2]
            fila = []
            for dato in par:
                fila.extend(
                    [
                        Paragraph(_e(dato[0]), etiqueta),
                        Paragraph(_e(dato[1]), valor),
                    ]
                )
            while len(fila) < 4:
                fila.append("")
            filas_meta.append(fila)

        tabla_meta = Table(
            filas_meta,
            colWidths=[
                disponibles * .22,
                disponibles * .28,
                disponibles * .22,
                disponibles * .28,
            ],
        )
        tabla_meta.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        elementos.append(tabla_meta)

    resumen = reporte.get("resumen") or []

    if resumen:
        filas_resumen = []
        for indice in range(0, len(resumen), 2):
            par = resumen[indice:indice + 2]
            fila = []
            for dato in par:
                fila.extend(
                    [
                        Paragraph(_e(dato[0]), etiqueta),
                        Paragraph(_e(dato[1]), valor),
                    ]
                )
            while len(fila) < 4:
                fila.append("")
            filas_resumen.append(fila)

        tabla_resumen = Table(
            filas_resumen,
            colWidths=[
                disponibles * .28,
                disponibles * .22,
                disponibles * .28,
                disponibles * .22,
            ],
        )
        tabla_resumen.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), CREAM),
                    ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elementos.extend([Spacer(1, 8), tabla_resumen])

    for indice, bloque in enumerate(reporte.get("secciones", [])):
        if indice > 0:
            elementos.append(Spacer(1, 10))

        elementos.append(
            Paragraph(_e(bloque.get("titulo", "")), seccion)
        )

        filas = bloque.get("filas") or []

        if not filas:
            elementos.append(
                Paragraph(
                    "Sin registros para los filtros seleccionados.",
                    vacio,
                )
            )
            continue

        encabezados = bloque.get("encabezados") or []
        alineaciones = bloque.get("alineaciones") or [
            "left"
        ] * len(encabezados)

        datos = [
            [
                Paragraph(_e(celda), encabezado)
                for celda in encabezados
            ]
        ]

        for fila in filas:
            datos.append(
                [
                    Paragraph(
                        _e(celda),
                        _estilo_celda(
                            alineaciones[columna]
                            if columna < len(alineaciones)
                            else "left"
                        ),
                    )
                    for columna, celda in enumerate(fila)
                ]
            )

        anchos = bloque.get("anchos")

        if anchos and len(anchos) == len(encabezados):
            total_anchos = sum(anchos)
            col_widths = [
                disponibles * (ancho / total_anchos)
                for ancho in anchos
            ]
        else:
            col_widths = [
                disponibles / len(encabezados)
            ] * len(encabezados)

        tabla = Table(
            datos,
            colWidths=col_widths,
            repeatRows=1,
        )
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BROWN_DARK),
                    ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                    ("INNERGRID", (0, 1), (-1, -1), 0.25, BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CREAM]),
                ]
            )
        )
        elementos.append(tabla)

        totales = bloque.get("totales") or []

        if totales:
            filas_totales = [
                [
                    Paragraph(_e(fila[0]), etiqueta),
                    Paragraph(_e(fila[1]), valor),
                ]
                for fila in totales
            ]
            tabla_totales = Table(
                filas_totales,
                colWidths=[disponibles * .72, disponibles * .28],
            )
            tabla_totales.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                        ("LINEABOVE", (0, 0), (-1, 0), 0.7, BROWN),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            elementos.append(tabla_totales)

    if reporte.get("nota"):
        elementos.append(
            Paragraph(_e(reporte["nota"]), nota)
        )

    documento.build(
        elementos,
        onFirstPage=_pie_de_pagina,
        onLaterPages=_pie_de_pagina,
    )

    return buffer.getvalue()


def _titulo_hoja(titulo, existentes):
    limpio = "".join(
        caracter
        for caracter in str(titulo)
        if caracter not in "[]:*?/\\"
    ).strip() or "Reporte"
    limpio = limpio[:31]

    candidato = limpio
    contador = 2

    while candidato in existentes:
        sufijo = f" {contador}"
        candidato = f"{limpio[:31 - len(sufijo)]}{sufijo}"
        contador += 1

    existentes.add(candidato)
    return candidato


def generar_excel_reporte(reporte):
    """Genera un libro XLSX con resumen y una hoja por sección."""

    libro = Workbook()
    libro.properties.creator = "Mueblería Anahí"
    libro.properties.title = reporte.get("titulo", "Reporte")

    hoja = libro.active
    hoja.title = "Resumen"

    marron = "69452D"
    marron_oscuro = "49301F"
    crema = "F6F1EA"
    borde = "DED6CD"
    rojo = "A63D40"

    borde_fino = Border(
        left=Side(style="thin", color=borde),
        right=Side(style="thin", color=borde),
        top=Side(style="thin", color=borde),
        bottom=Side(style="thin", color=borde),
    )

    hoja.merge_cells("A1:D1")
    celda = hoja["A1"]
    celda.value = "MUEBLERÍA ANAHÍ"
    celda.font = Font(
        bold=True,
        size=18,
        color=marron_oscuro,
    )
    celda.alignment = Alignment(vertical="center")

    hoja.merge_cells("A2:D2")
    hoja["A2"] = reporte.get("titulo", "Reporte")
    hoja["A2"].font = Font(bold=True, size=13, color=marron)

    hoja.merge_cells("A3:D3")
    hoja["A3"] = reporte.get("subtitulo", "")
    hoja["A3"].font = Font(size=10, color="756B64")

    fila_actual = 5

    for etiqueta, valor in reporte.get("metadatos") or []:
        hoja.cell(fila_actual, 1, etiqueta).font = Font(
            bold=True,
            size=9,
            color="756B64",
        )
        hoja.merge_cells(
            start_row=fila_actual,
            start_column=2,
            end_row=fila_actual,
            end_column=4,
        )
        hoja.cell(fila_actual, 2, valor)
        fila_actual += 1

    fila_actual += 1
    hoja.cell(fila_actual, 1, "RESUMEN EJECUTIVO").font = Font(
        bold=True,
        size=11,
        color=marron_oscuro,
    )
    fila_actual += 1

    for etiqueta, valor in reporte.get("resumen") or []:
        celda_etiqueta = hoja.cell(fila_actual, 1, etiqueta)
        celda_etiqueta.font = Font(bold=True, size=9, color="756B64")
        celda_etiqueta.fill = PatternFill("solid", fgColor=crema)
        celda_etiqueta.border = borde_fino

        hoja.merge_cells(
            start_row=fila_actual,
            start_column=2,
            end_row=fila_actual,
            end_column=3,
        )
        celda_valor = hoja.cell(fila_actual, 2, valor)
        celda_valor.font = Font(bold=True, size=10, color=marron_oscuro)
        celda_valor.fill = PatternFill("solid", fgColor=crema)
        celda_valor.border = borde_fino
        fila_actual += 1

    hoja.column_dimensions["A"].width = 34
    hoja.column_dimensions["B"].width = 26
    hoja.column_dimensions["C"].width = 20
    hoja.column_dimensions["D"].width = 20

    existentes = {"Resumen"}

    for bloque in reporte.get("secciones", []):
        nombre_hoja = _titulo_hoja(
            bloque.get("titulo", "Sección"),
            existentes,
        )
        detalle = libro.create_sheet(nombre_hoja)

        detalle.merge_cells("A1:H1")
        detalle["A1"] = bloque.get("titulo", "Sección")
        detalle["A1"].font = Font(
            bold=True,
            size=14,
            color=marron_oscuro,
        )
        detalle["A1"].alignment = Alignment(vertical="center")

        detalle.merge_cells("A2:H2")
        detalle["A2"] = reporte.get("subtitulo", "")
        detalle["A2"].font = Font(size=9, color="756B64")

        encabezados = bloque.get("encabezados") or []
        fila_encabezado = 4

        for columna, encabezado in enumerate(encabezados, start=1):
            celda = detalle.cell(fila_encabezado, columna, encabezado)
            celda.font = Font(
                bold=True,
                color="FFFFFF",
                size=9,
            )
            celda.fill = PatternFill(
                "solid",
                fgColor=marron_oscuro,
            )
            celda.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )
            celda.border = borde_fino

        filas = bloque.get("filas") or []
        fila = fila_encabezado + 1

        if not filas:
            detalle.cell(
                fila,
                1,
                "Sin registros para los filtros seleccionados.",
            ).font = Font(italic=True, color="756B64")
        else:
            for datos in filas:
                for columna, valor in enumerate(datos, start=1):
                    celda = detalle.cell(fila, columna, valor)
                    celda.font = Font(size=9)
                    celda.border = borde_fino
                    celda.alignment = Alignment(
                        vertical="top",
                        wrap_text=True,
                    )

                    if fila % 2 == 0:
                        celda.fill = PatternFill(
                            "solid",
                            fgColor=crema,
                        )

                fila += 1

            detalle.auto_filter.ref = (
                f"A{fila_encabezado}:"
                f"{get_column_letter(len(encabezados))}"
                f"{fila - 1}"
            )

        fila += 1

        for etiqueta, valor in bloque.get("totales") or []:
            celda_etiqueta = detalle.cell(fila, 1, etiqueta)
            celda_etiqueta.font = Font(
                bold=True,
                size=9,
                color=marron_oscuro,
            )
            celda_etiqueta.border = borde_fino
            celda_etiqueta.fill = PatternFill(
                "solid",
                fgColor=crema,
            )

            celda_valor = detalle.cell(
                fila,
                max(2, len(encabezados)),
                valor,
            )
            celda_valor.font = Font(
                bold=True,
                size=10,
                color="A63D40" if "anulad" in etiqueta.lower() else marron_oscuro,
            )
            celda_valor.alignment = Alignment(horizontal="right")
            celda_valor.border = borde_fino
            fila += 1

        for columna, encabezado in enumerate(encabezados, start=1):
            largo = len(str(encabezado))

            for datos in filas:
                if columna <= len(datos):
                    largo = max(
                        largo,
                        len(str(datos[columna - 1])),
                    )

            detalle.column_dimensions[
                get_column_letter(columna)
            ].width = min(max(largo + 3, 11), 48)

        detalle.freeze_panes = f"A{fila_encabezado + 1}"

    if reporte.get("nota"):
        hoja.cell(
            fila_actual + 1,
            1,
            reporte["nota"],
        ).font = Font(italic=True, size=9, color="756B64")

    hoja.sheet_view.showGridLines = False

    buffer = BytesIO()
    libro.save(buffer)

    return buffer.getvalue()


def nombre_pdf(reporte):
    return f"{reporte.get('nombre_archivo', 'reporte')}.pdf"


def nombre_excel(reporte):
    return f"{reporte.get('nombre_archivo', 'reporte')}.xlsx"


def fecha_exportacion():
    return timezone.localtime().strftime("%d/%m/%Y %H:%M")
