from datetime import datetime, time, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from inventario.models import Categoria, Material, Producto
from ventas.models import Ingreso
from ventas.services import anular_venta, registrar_venta

from .builders import (
    construir_reporte_inventario,
    construir_reporte_ingresos,
    construir_reporte_productos,
    construir_reporte_ventas,
)
from .exporters import (
    _titulo_hoja,
    generar_excel_reporte,
    generar_pdf_reporte,
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


class BaseReporteTestCase(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="reportes_staff",
            password="Test12345!",
            is_staff=True,
        )
        self.usuario = get_user_model().objects.create_user(
            username="reportes_user",
            password="Test12345!",
        )
        self.categoria = Categoria.objects.create(
            nombre="Dormitorio",
        )
        self.categoria_2 = Categoria.objects.create(
            nombre="Comedor",
        )
        self.producto = Producto.objects.create(
            codigo="CAM-001",
            nombre="Cama matrimonial",
            categoria=self.categoria,
            precio=Decimal("250.00"),
            stock=20,
            stock_minimo=5,
        )
        self.producto_2 = Producto.objects.create(
            codigo="MES-001",
            nombre="Mesa de comedor",
            categoria=self.categoria_2,
            precio=Decimal("500.00"),
            stock=1,
            stock_minimo=5,
        )
        self.producto_agotado = Producto.objects.create(
            codigo="SIL-001",
            nombre="Silla agotada",
            categoria=self.categoria,
            precio=Decimal("100.00"),
            stock=0,
            stock_minimo=2,
        )
        self.producto_inactivo = Producto.objects.create(
            codigo="ARM-001",
            nombre="Armario inactivo",
            categoria=self.categoria,
            precio=Decimal("900.00"),
            stock=4,
            stock_minimo=1,
            activo=False,
        )
        self.material = Material.objects.create(
            codigo="MAD-001",
            nombre="Madera roble",
            unidad_medida=Material.TABLON,
            stock=Decimal("10.00"),
            stock_minimo=Decimal("20.00"),
            costo_referencia=Decimal("80.00"),
        )
        self.material_agotado = Material.objects.create(
            codigo="PEG-001",
            nombre="Pegamento",
            unidad_medida=Material.LITRO,
            stock=Decimal("0.00"),
            stock_minimo=Decimal("2.00"),
            costo_referencia=Decimal("25.00"),
        )
        self.material_inactivo = Material.objects.create(
            codigo="CLA-001",
            nombre="Clavos",
            unidad_medida=Material.KILOGRAMO,
            stock=Decimal("5.00"),
            stock_minimo=Decimal("1.00"),
            costo_referencia=Decimal("10.00"),
            activo=False,
        )
        self.hoy = timezone.localdate()
        self.ayer = self.hoy - timedelta(days=1)
        self.venta_hoy = self.crear_venta(
            [(self.producto, 2), (self.producto_2, 1)],
            metodo=Ingreso.EFECTIVO,
            fecha=datetime.combine(self.hoy, time(10, 0)),
        )
        self.venta_ayer = self.crear_venta(
            [(self.producto, 5)],
            metodo=Ingreso.TRANSFERENCIA,
            fecha=datetime.combine(self.ayer, time(15, 0)),
            referencia="TRF-001",
        )
        self.venta_anulada = self.crear_venta(
            [(self.producto, 1)],
            metodo=Ingreso.TARJETA,
            fecha=datetime.combine(self.ayer, time(17, 0)),
        )
        anular_venta(
            venta=self.venta_anulada,
            usuario=self.staff,
        )

    def crear_venta(
        self,
        items,
        metodo=Ingreso.EFECTIVO,
        fecha=None,
        referencia="",
    ):
        venta = registrar_venta(
            cliente=self._cliente(),
            items=[
                {"producto": producto, "cantidad": cantidad}
                for producto, cantidad in items
            ],
            usuario=self.staff,
            metodo_pago=metodo,
            referencia_pago=referencia,
        )

        if fecha:
            fecha_aware = timezone.make_aware(fecha)
            type(venta).objects.filter(pk=venta.pk).update(
                fecha=fecha_aware
            )
            venta.refresh_from_db()

        return venta

    def _cliente(self):
        from ventas.models import Cliente

        cliente, _ = Cliente.objects.get_or_create(
            nombre="Cliente Reporte",
            defaults={"nit": "123456"},
        )
        return cliente

    def reponer_stock(self):
        """Restaura el stock inicial para probar el reporte de inventario."""

        Producto.objects.filter(pk=self.producto.pk).update(stock=20)
        Producto.objects.filter(pk=self.producto_2.pk).update(stock=1)


class ReporteServiceTests(BaseReporteTestCase):
    def test_resumen_ventas_excluye_anuladas(self):
        resumen = resumen_ventas()

        self.assertEqual(resumen["cantidad"], 2)
        self.assertEqual(resumen["total"], Decimal("2250.00"))
        self.assertEqual(resumen["unidades"], Decimal("8"))
        self.assertEqual(resumen["promedio"], Decimal("1125.00"))
        self.assertEqual(resumen["anuladas_cantidad"], 1)
        self.assertEqual(resumen["anuladas_total"], Decimal("250.00"))

    def test_resumen_ventas_filtra_por_fecha(self):
        inicio = timezone.make_aware(
            datetime.combine(self.ayer, time.min)
        )
        fin = timezone.make_aware(
            datetime.combine(self.hoy, time.min)
        )

        resumen = resumen_ventas(inicio, fin)

        self.assertEqual(resumen["cantidad"], 1)
        self.assertEqual(resumen["total"], Decimal("1250.00"))

    def test_resumen_ventas_sin_datos(self):
        resumen = resumen_ventas(
            timezone.make_aware(
                datetime.combine(self.hoy + timedelta(days=5), time.min)
            ),
            None,
        )

        self.assertEqual(resumen["cantidad"], 0)
        self.assertEqual(resumen["total"], Decimal("0.00"))
        self.assertEqual(resumen["unidades"], 0)

    def test_ventas_periodo(self):
        ventas = ventas_periodo()

        self.assertEqual(ventas.count(), 2)
        self.assertNotIn(
            self.venta_anulada.pk,
            list(ventas.values_list("pk", flat=True)),
        )

    def test_productos_mas_vendidos(self):
        productos = productos_mas_vendidos()

        self.assertEqual(len(productos), 2)
        self.assertEqual(productos[0]["codigo"], "CAM-001")
        self.assertEqual(productos[0]["cantidad"], 7)
        self.assertEqual(productos[0]["ingresos"], Decimal("1750.00"))
        self.assertEqual(productos[1]["codigo"], "MES-001")
        self.assertEqual(productos[1]["cantidad"], 1)

    def test_productos_mas_vendidos_limite_y_fechas(self):
        inicio = timezone.make_aware(
            datetime.combine(self.hoy, time.min)
        )

        productos = productos_mas_vendidos(inicio, None, limite=1)

        self.assertEqual(len(productos), 1)
        self.assertEqual(productos[0]["codigo"], "CAM-001")
        self.assertEqual(productos[0]["cantidad"], 2)

    def test_productos_mas_vendidos_sin_ventas(self):
        productos = productos_mas_vendidos(
            timezone.make_aware(
                datetime.combine(self.hoy + timedelta(days=10), time.min)
            ),
            None,
        )

        self.assertEqual(productos, [])

    def test_resumen_productos_vendidos(self):
        resumen = resumen_productos_vendidos()

        self.assertEqual(resumen["unidades"], Decimal("8"))
        self.assertEqual(resumen["ingresos"], Decimal("2250.00"))
        self.assertEqual(resumen["productos"], 2)
        self.assertEqual(resumen["ventas"], 2)

    def test_ingresos_y_resumen_por_metodo(self):
        ingresos = ingresos_periodo()

        self.assertEqual(ingresos.count(), 2)

        resumen = resumen_ingresos()

        self.assertEqual(resumen["cantidad"], 2)
        self.assertEqual(resumen["total"], Decimal("2250.00"))
        self.assertEqual(resumen["promedio"], Decimal("1125.00"))
        self.assertEqual(len(resumen["por_metodo"]), 4)

        metodos = {
            metodo["codigo"]: metodo
            for metodo in resumen["por_metodo"]
        }

        self.assertEqual(
            metodos[Ingreso.EFECTIVO]["total"],
            Decimal("1000.00"),
        )
        self.assertEqual(
            metodos[Ingreso.TRANSFERENCIA]["total"],
            Decimal("1250.00"),
        )
        self.assertEqual(
            metodos[Ingreso.TARJETA]["cantidad"],
            0,
        )
        self.assertEqual(
            metodos[Ingreso.QR]["total"],
            Decimal("0.00"),
        )

    def test_resumen_ingresos_sin_datos(self):
        resumen = resumen_ingresos(
            timezone.make_aware(
                datetime.combine(self.hoy + timedelta(days=10), time.min)
            ),
            None,
        )

        self.assertEqual(resumen["cantidad"], 0)
        self.assertEqual(resumen["total"], Decimal("0.00"))
        self.assertEqual(resumen["promedio"], Decimal("0.00"))

    def test_reporte_inventario_general(self):
        self.reponer_stock()
        datos = reporte_inventario()

        self.assertEqual(datos["resumen_productos"]["total"], 3)
        self.assertEqual(datos["resumen_productos"]["agotados"], 1)
        self.assertEqual(datos["resumen_productos"]["bajos"], 1)
        self.assertEqual(datos["resumen_productos"]["disponibles"], 1)
        self.assertEqual(
            datos["resumen_productos"]["valor"],
            Decimal("5500.00"),
        )
        self.assertEqual(datos["resumen_materiales"]["total"], 2)
        self.assertEqual(datos["resumen_materiales"]["agotados"], 1)
        self.assertEqual(datos["resumen_materiales"]["bajos"], 1)
        self.assertEqual(
            datos["resumen_materiales"]["valor"],
            Decimal("800.00"),
        )

    def test_reporte_inventario_filtros(self):
        self.reponer_stock()
        datos = reporte_inventario(
            busqueda="cama",
            categoria_id=self.categoria.pk,
            estado="disponible",
        )

        self.assertEqual(
            list(datos["productos"].values_list("codigo", flat=True)),
            ["CAM-001"],
        )

        datos = reporte_inventario(estado="agotado")

        self.assertEqual(
            list(datos["productos"].values_list("codigo", flat=True)),
            ["SIL-001"],
        )
        self.assertEqual(
            list(datos["materiales"].values_list("codigo", flat=True)),
            ["PEG-001"],
        )

        datos = reporte_inventario(estado="bajo")
        self.assertEqual(
            list(datos["productos"].values_list("codigo", flat=True)),
            ["MES-001"],
        )

    def test_reporte_inventario_incluye_inactivos(self):
        datos = reporte_inventario(solo_activos=False)
        codigos = set(
            datos["productos"].values_list("codigo", flat=True)
        )
        materiales = set(
            datos["materiales"].values_list("codigo", flat=True)
        )

        self.assertIn("ARM-001", codigos)
        self.assertIn("CLA-001", materiales)


class ReporteBuilderTests(BaseReporteTestCase):
    def _datos(self):
        return {
            "resumen": resumen_ventas(),
            "ingresos": resumen_ingresos(),
            "ventas": ventas_periodo(),
            "productos": productos_mas_vendidos(),
            "resumen_productos": resumen_productos_vendidos(),
            "inventario": reporte_inventario(),
            "ingresos_lista": ingresos_periodo(),
        }

    def test_construir_reporte_ventas(self):
        datos = self._datos()
        reporte = construir_reporte_ventas(
            datos["ventas"],
            datos["resumen"],
            datos["ingresos"],
            self.ayer,
            self.hoy,
            "staff",
        )

        self.assertEqual(
            reporte["titulo"],
            "Reporte general de ventas",
        )
        self.assertEqual(len(reporte["secciones"]), 2)
        self.assertEqual(len(reporte["secciones"][0]["filas"]), 2)
        self.assertIn("2026", reporte["nombre_archivo"])

    def test_construir_reporte_productos(self):
        datos = self._datos()
        reporte = construir_reporte_productos(
            datos["productos"],
            datos["resumen_productos"],
            self.ayer,
            self.hoy,
            10,
            "staff",
        )

        self.assertEqual(
            reporte["secciones"][0]["filas"][0][1],
            "CAM-001",
        )
        self.assertEqual(reporte["resumen"][1][1], Decimal("8"))

    def test_construir_reporte_inventario(self):
        datos = self._datos()
        reporte = construir_reporte_inventario(
            datos["inventario"]["productos"],
            datos["inventario"]["materiales"],
            datos["inventario"]["resumen_productos"],
            datos["inventario"]["resumen_materiales"],
            "staff",
        )

        self.assertEqual(len(reporte["secciones"]), 2)
        self.assertTrue(
            any(
                fila[-1] == "Agotado"
                for fila in reporte["secciones"][0]["filas"]
            )
        )

    def test_construir_reporte_ingresos(self):
        datos = self._datos()
        reporte = construir_reporte_ingresos(
            datos["ingresos_lista"],
            datos["ingresos"],
            self.ayer,
            self.hoy,
            "staff",
        )

        self.assertEqual(reporte["resumen"][0][1], 2)
        self.assertEqual(len(reporte["secciones"][0]["filas"]), 2)

    def test_reportes_sin_registros(self):
        reporte_ventas = construir_reporte_ventas(
            [],
            resumen_ventas(
                timezone.make_aware(
                    datetime.combine(
                        self.hoy + timedelta(days=30),
                        time.min,
                    )
                ),
                None,
            ),
            resumen_ingresos(
                timezone.make_aware(
                    datetime.combine(
                        self.hoy + timedelta(days=30),
                        time.min,
                    )
                ),
                None,
            ),
            None,
            None,
            "",
        )
        reporte_productos = construir_reporte_productos(
            [],
            {
                "unidades": 0,
                "ingresos": Decimal("0.00"),
                "productos": 0,
                "ventas": 0,
            },
            None,
            None,
            10,
            "",
        )
        datos_inventario = reporte_inventario(busqueda="no-existe")
        reporte_inventario_vacio = construir_reporte_inventario(
            datos_inventario["productos"],
            datos_inventario["materiales"],
            datos_inventario["resumen_productos"],
            datos_inventario["resumen_materiales"],
            "",
        )
        reporte_ingresos = construir_reporte_ingresos(
            [],
            {"cantidad": 0, "total": Decimal("0.00"),
             "promedio": Decimal("0.00"),
             "por_metodo": []},
            None,
            None,
            "",
        )

        for reporte in (
            reporte_ventas,
            reporte_productos,
            reporte_inventario_vacio,
            reporte_ingresos,
        ):
            with self.subTest(titulo=reporte["titulo"]):
                pdf = generar_pdf_reporte(reporte)
                excel = generar_excel_reporte(reporte)
                self.assertTrue(pdf.startswith(b"%PDF"))
                self.assertTrue(excel.startswith(b"PK"))
                self.assertIn("Sin registros", pdf.decode("latin-1"))


class ExportadorTests(BaseReporteTestCase):
    def test_titulo_hoja_se_limpia_y_evita_duplicados(self):
        existentes = {"Resumen"}
        primero = _titulo_hoja("Ventas [2026]:*?/", existentes)
        segundo = _titulo_hoja("Ventas [2026]:*?/", existentes)

        self.assertEqual(primero, "Ventas 2026")
        self.assertNotEqual(primero, segundo)
        self.assertLessEqual(len(segundo), 31)

    def test_excel_contiene_hojas_y_datos(self):
        datos = reporte_inventario()
        reporte = construir_reporte_inventario(
            datos["productos"],
            datos["materiales"],
            datos["resumen_productos"],
            datos["resumen_materiales"],
            "staff",
        )

        contenido = generar_excel_reporte(reporte)
        libro = load_workbook(BytesIO(contenido))

        self.assertIn("Resumen", libro.sheetnames)
        self.assertGreaterEqual(len(libro.sheetnames), 3)
        self.assertEqual(
            libro["Resumen"]["A1"].value,
            "MUEBLERÍA ANAHÍ",
        )

        hoja_productos = libro[libro.sheetnames[1]]
        self.assertEqual(
            hoja_productos["A4"].value,
            "Código",
        )

    def test_pdf_con_todas_las_secciones(self):
        datos = reporte_inventario()
        reporte = construir_reporte_inventario(
            datos["productos"],
            datos["materiales"],
            datos["resumen_productos"],
            datos["resumen_materiales"],
            "staff",
        )

        contenido = generar_pdf_reporte(reporte)

        self.assertTrue(contenido.startswith(b"%PDF"))
        self.assertIn(
            b"INVENTARIO DE PRODUCTOS",
            contenido.upper(),
        )


class ReporteViewTests(BaseReporteTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(
            username="reportes_staff",
            password="Test12345!",
        )

    def test_acceso_requiere_staff(self):
        self.client.logout()

        response = self.client.get(reverse("reportes:ventas"))
        self.assertEqual(response.status_code, 302)

        self.client.login(
            username="reportes_user",
            password="Test12345!",
        )
        response = self.client.get(reverse("reportes:ventas"))
        self.assertEqual(response.status_code, 302)

    def test_paginas_de_reportes(self):
        casos = [
            ("reportes:ventas", "Reporte general"),
            ("reportes:productos", "Productos más vendidos"),
            ("reportes:inventario", "Estado real del inventario"),
            ("reportes:ingresos", "Resumen de ingresos"),
        ]

        for nombre, texto in casos:
            with self.subTest(nombre=nombre):
                response = self.client.get(reverse(nombre))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, texto)

    def test_reporte_ventas_muestra_datos_y_filtros(self):
        response = self.client.get(
            reverse("reportes:ventas"),
            {
                "desde": self.hoy.isoformat(),
                "hasta": self.hoy.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["resumen"]["cantidad"], 1)
        self.assertContains(response, self.venta_hoy.numero)
        self.assertNotContains(response, self.venta_ayer.numero)

    def test_reporte_ventas_fecha_invalida(self):
        response = self.client.get(
            reverse("reportes:ventas"),
            {"desde": "2026-99-99"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "debe tener el formato AAAA-MM-DD",
        )

    def test_reporte_productos_limite_invalido(self):
        response = self.client.get(
            reverse("reportes:productos"),
            {"limite": "999"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["limite"], 10)

    def test_reporte_productos_limite_valido(self):
        response = self.client.get(
            reverse("reportes:productos"),
            {"limite": "5"},
        )

        self.assertEqual(response.context["limite"], 5)

    def test_reporte_productos_sin_datos(self):
        futuro = (self.hoy + timedelta(days=20)).isoformat()
        response = self.client.get(
            reverse("reportes:productos"),
            {"desde": futuro, "hasta": futuro},
        )

        self.assertContains(
            response,
            "No hay productos vendidos",
        )

    def test_reporte_inventario_filtros(self):
        response = self.client.get(
            reverse("reportes:inventario"),
            {
                "q": "cama",
                "categoria": self.categoria.pk,
                "estado": "disponible",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cama matrimonial")
        self.assertNotContains(response, "Mesa de comedor")

    def test_reporte_inventario_categoria_invalida(self):
        response = self.client.get(
            reverse("reportes:inventario"),
            {"categoria": "no-es-numero"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["categoria_id"])

    def test_exportaciones_pdf_y_excel(self):
        nombres = [
            "ventas",
            "productos",
            "inventario",
            "ingresos",
        ]

        for nombre in nombres:
            with self.subTest(nombre=nombre):
                respuesta_pdf = self.client.get(
                    reverse(f"reportes:{nombre}_pdf")
                )
                self.assertEqual(respuesta_pdf.status_code, 200)
                self.assertEqual(
                    respuesta_pdf["Content-Type"],
                    "application/pdf",
                )
                self.assertTrue(
                    respuesta_pdf.content.startswith(b"%PDF")
                )
                self.assertIn(
                    "attachment",
                    respuesta_pdf["Content-Disposition"],
                )

                respuesta_excel = self.client.get(
                    reverse(f"reportes:{nombre}_excel")
                )
                self.assertEqual(respuesta_excel.status_code, 200)
                self.assertEqual(
                    respuesta_excel["Content-Type"],
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet",
                )
                self.assertTrue(
                    respuesta_excel.content.startswith(b"PK")
                )
                self.assertIn(
                    "attachment",
                    respuesta_excel["Content-Disposition"],
                )

    def test_exportacion_inventario_respeta_filtros(self):
        response = self.client.get(
            reverse("reportes:inventario_excel"),
            {"q": "cama"},
        )

        libro = load_workbook(BytesIO(response.content))
        hoja = libro[libro.sheetnames[1]]
        valores = [
            celda.value
            for fila in hoja.iter_rows(min_row=5)
            for celda in fila
            if celda.value
        ]

        self.assertIn("Cama matrimonial", valores)
        self.assertNotIn("Mesa de comedor", valores)

    def test_paginacion_reporte_ventas(self):
        Producto.objects.filter(pk=self.producto.pk).update(stock=100)

        for indice in range(25):
            self.crear_venta(
                [(self.producto, 1)],
                fecha=datetime.combine(self.hoy, time(12, indice % 60)),
            )

        response = self.client.get(
            reverse("reportes:ventas"),
            {"page": 2},
        )

        self.assertEqual(response.context["page_obj"].number, 2)
