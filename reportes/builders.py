from django.utils import timezone


def _fecha_local(valor):
    return timezone.localtime(valor).strftime("%d/%m/%Y %H:%M")


def _periodo_texto(desde, hasta):
    if desde and hasta:
        return f"Del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}"
    if desde:
        return f"Desde el {desde:%d/%m/%Y}"
    if hasta:
        return f"Hasta el {hasta:%d/%m/%Y}"
    return "Todos los registros"


def _nombre_archivo(prefijo, desde, hasta):
    inicio = f"{desde:%Y%m%d}" if desde else "inicio"
    fin = f"{hasta:%Y%m%d}" if hasta else "hoy"
    return f"{prefijo}_{inicio}_{fin}"


def _estado_stock(stock, stock_minimo):
    if stock == 0:
        return "Agotado"
    if stock <= stock_minimo:
        return "Stock bajo"
    return "Disponible"


def construir_reporte_ventas(
    ventas,
    resumen,
    resumen_ingresos,
    desde,
    hasta,
    generado_por="",
):
    filas = []

    for venta in ventas:
        filas.append(
            [
                venta.numero or f"Venta #{venta.pk}",
                _fecha_local(venta.fecha),
                venta.cliente.nombre,
                venta.cliente.nit or "-",
                venta.detalles.count(),
                f"Bs {venta.total:.2f}",
                (
                    venta.ingreso.get_metodo_pago_display()
                    if hasattr(venta, "ingreso") and venta.ingreso
                    else "Sin registro"
                ),
                (
                    "Anulada"
                    if venta.estado == "ANULADA"
                    else "Completada"
                ),
            ]
        )

    filas_metodos = [
        [
            metodo["nombre"],
            metodo["cantidad"],
            f"Bs {metodo['total']:.2f}",
        ]
        for metodo in resumen_ingresos["por_metodo"]
    ]

    return {
        "titulo": "Reporte general de ventas",
        "subtitulo": _periodo_texto(desde, hasta),
        "nombre_archivo": _nombre_archivo(
            "reporte_ventas",
            desde,
            hasta,
        ),
        "metadatos": [
            ("Generado por", generado_por or "Sistema"),
            (
                "Fecha de generación",
                timezone.localtime().strftime("%d/%m/%Y %H:%M"),
            ),
        ],
        "resumen": [
            ("Ventas completadas", resumen["cantidad"]),
            ("Ingresos totales", f"Bs {resumen['total']:.2f}"),
            ("Ticket promedio", f"Bs {resumen['promedio']:.2f}"),
            ("Unidades vendidas", resumen["unidades"]),
            ("Ventas anuladas", resumen["anuladas_cantidad"]),
            (
                "Monto anulado",
                f"Bs {resumen['anuladas_total']:.2f}",
            ),
        ],
        "secciones": [
            {
                "titulo": "Ventas del periodo",
                "encabezados": [
                    "Comprobante",
                    "Fecha",
                    "Cliente",
                    "NIT",
                    "Productos",
                    "Total",
                    "Pago",
                    "Estado",
                ],
                "filas": filas,
                "totales": [
                    ["Total de ventas", f"Bs {resumen['total']:.2f}"],
                ],
                "anchos": [2.0, 2.3, 3.1, 1.6, 1.3, 1.8, 2.2, 1.6],
                "alineaciones": [
                    "left",
                    "left",
                    "left",
                    "left",
                    "center",
                    "right",
                    "left",
                    "center",
                ],
            },
            {
                "titulo": "Resumen de ingresos por método de pago",
                "encabezados": ["Método de pago", "Cantidad", "Total"],
                "filas": filas_metodos,
                "totales": [
                    [
                        "Total de ingresos",
                        f"Bs {resumen_ingresos['total']:.2f}",
                    ],
                ],
                "anchos": [6.0, 4.0, 5.0],
                "alineaciones": ["left", "center", "right"],
            },
        ],
        "nota": (
            "Los montos corresponden a ventas completadas. "
            "Las ventas anuladas se muestran solo para auditoría."
        ),
    }


def construir_reporte_productos(
    productos,
    resumen,
    desde,
    hasta,
    limite,
    generado_por="",
):
    filas = [
        [
            indice,
            producto["codigo"],
            producto["nombre"],
            producto["cantidad"],
            f"Bs {producto['ingresos']:.2f}",
            f"Bs {producto['precio']:.2f}",
            producto["stock"],
        ]
        for indice, producto in enumerate(productos, start=1)
    ]

    return {
        "titulo": "Productos más vendidos",
        "subtitulo": (
            f"{_periodo_texto(desde, hasta)} · Top {limite}"
        ),
        "nombre_archivo": _nombre_archivo(
            "productos_mas_vendidos",
            desde,
            hasta,
        ),
        "metadatos": [
            ("Generado por", generado_por or "Sistema"),
            (
                "Fecha de generación",
                timezone.localtime().strftime("%d/%m/%Y %H:%M"),
            ),
        ],
        "resumen": [
            ("Productos con ventas", resumen["productos"]),
            ("Unidades vendidas", resumen["unidades"]),
            ("Ingresos por productos", f"Bs {resumen['ingresos']:.2f}"),
            ("Ventas del periodo", resumen["ventas"]),
        ],
        "secciones": [
            {
                "titulo": f"Ranking de los {limite} productos más vendidos",
                "encabezados": [
                    "#",
                    "Código",
                    "Producto",
                    "Unidades",
                    "Ingresos",
                    "Precio actual",
                    "Stock actual",
                ],
                "filas": filas,
                "totales": [
                    [
                        "Total de unidades",
                        resumen["unidades"],
                    ],
                    [
                        "ingresos",
                        f"Bs {resumen['ingresos']:.2f}",
                    ],
                ],
                "anchos": [0.8, 2.0, 4.8, 1.5, 2.0, 1.7, 1.5],
                "alineaciones": [
                    "center",
                    "left",
                    "left",
                    "center",
                    "right",
                    "right",
                    "center",
                ],
            },
        ],
        "nota": (
            "El ranking se calcula únicamente con ventas completadas "
            "del periodo seleccionado."
        ),
    }


def construir_reporte_inventario(
    productos,
    materiales,
    resumen_productos,
    resumen_materiales,
    generado_por="",
):
    filas_productos = [
        [
            producto.codigo,
            producto.nombre,
            producto.categoria.nombre,
            producto.stock,
            producto.stock_minimo,
            f"Bs {producto.valor_inventario:.2f}",
            _estado_stock(producto.stock, producto.stock_minimo),
        ]
        for producto in productos
    ]

    filas_materiales = [
        [
            material.codigo,
            material.nombre,
            material.get_unidad_medida_display(),
            f"{material.stock:.2f}",
            f"{material.stock_minimo:.2f}",
            f"Bs {material.valor_inventario:.2f}",
            _estado_stock(material.stock, material.stock_minimo),
        ]
        for material in materiales
    ]

    return {
        "titulo": "Reporte de inventario",
        "subtitulo": "Productos terminados y materiales",
        "nombre_archivo": "reporte_inventario",
        "metadatos": [
            ("Generado por", generado_por or "Sistema"),
            (
                "Fecha de generación",
                timezone.localtime().strftime("%d/%m/%Y %H:%M"),
            ),
        ],
        "resumen": [
            ("Productos registrados", resumen_productos["total"]),
            ("Productos agotados", resumen_productos["agotados"]),
            ("Productos con stock bajo", resumen_productos["bajos"]),
            (
                "Valor del inventario de productos",
                f"Bs {resumen_productos['valor']:.2f}",
            ),
            ("Materiales registrados", resumen_materiales["total"]),
            ("Materiales con stock bajo", resumen_materiales["bajos"]),
            (
                "Valor del inventario de materiales",
                f"Bs {resumen_materiales['valor']:.2f}",
            ),
        ],
        "secciones": [
            {
                "titulo": "Inventario de productos terminados",
                "encabezados": [
                    "Código",
                    "Producto",
                    "Categoría",
                    "Stock",
                    "Stock mínimo",
                    "Valor",
                    "Estado",
                ],
                "filas": filas_productos,
                "totales": [
                    ["Productos", resumen_productos["total"]],
                    [
                        "Valor total",
                        f"Bs {resumen_productos['valor']:.2f}",
                    ],
                ],
                "anchos": [2.0, 3.8, 2.4, 1.3, 1.7, 2.0, 1.8],
                "alineaciones": [
                    "left",
                    "left",
                    "left",
                    "center",
                    "center",
                    "right",
                    "center",
                ],
            },
            {
                "titulo": "Inventario de materiales",
                "encabezados": [
                    "Código",
                    "Material",
                    "Unidad",
                    "Stock",
                    "Stock mínimo",
                    "Valor",
                    "Estado",
                ],
                "filas": filas_materiales,
                "totales": [
                    ["Materiales", resumen_materiales["total"]],
                    [
                        "Valor total",
                        f"Bs {resumen_materiales['valor']:.2f}",
                    ],
                ],
                "anchos": [2.0, 3.8, 2.0, 1.5, 1.8, 2.0, 1.8],
                "alineaciones": [
                    "left",
                    "left",
                    "left",
                    "center",
                    "center",
                    "right",
                    "center",
                ],
            },
        ],
        "nota": (
            "El valor del inventario se calcula con el precio de venta "
            "de los productos y el costo de referencia de los materiales."
        ),
    }


def construir_reporte_ingresos(
    ingresos,
    resumen,
    desde,
    hasta,
    generado_por="",
):
    filas = [
        [
            _fecha_local(ingreso.fecha),
            ingreso.venta.numero or f"Venta #{ingreso.venta_id}",
            ingreso.venta.cliente.nombre,
            ingreso.get_metodo_pago_display(),
            ingreso.referencia or "-",
            f"Bs {ingreso.monto:.2f}",
        ]
        for ingreso in ingresos
    ]

    filas_metodos = [
        [
            metodo["nombre"],
            metodo["cantidad"],
            f"Bs {metodo['total']:.2f}",
        ]
        for metodo in resumen["por_metodo"]
    ]

    return {
        "titulo": "Resumen de ingresos",
        "subtitulo": _periodo_texto(desde, hasta),
        "nombre_archivo": _nombre_archivo(
            "resumen_ingresos",
            desde,
            hasta,
        ),
        "metadatos": [
            ("Generado por", generado_por or "Sistema"),
            (
                "Fecha de generación",
                timezone.localtime().strftime("%d/%m/%Y %H:%M"),
            ),
        ],
        "resumen": [
            ("Pagos registrados", resumen["cantidad"]),
            ("Ingresos totales", f"Bs {resumen['total']:.2f}"),
        ],
        "secciones": [
            {
                "titulo": "Ingresos registrados",
                "encabezados": [
                    "Fecha",
                    "Comprobante",
                    "Cliente",
                    "Método",
                    "Referencia",
                    "Monto",
                ],
                "filas": filas,
                "totales": [
                    ["Total de ingresos", f"Bs {resumen['total']:.2f}"],
                ],
                "anchos": [2.3, 2.2, 3.5, 2.0, 2.2, 2.0],
                "alineaciones": [
                    "left",
                    "left",
                    "left",
                    "left",
                    "left",
                    "right",
                ],
            },
            {
                "titulo": "Ingresos por método de pago",
                "encabezados": ["Método de pago", "Cantidad", "Total"],
                "filas": filas_metodos,
                "totales": [
                    ["Total", f"Bs {resumen['total']:.2f}"],
                ],
                "anchos": [6.0, 4.0, 5.0],
                "alineaciones": ["left", "center", "right"],
            },
        ],
        "nota": (
            "Solo se incluyen ingresos asociados a ventas completadas."
        ),
    }
