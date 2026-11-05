import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from compras.models import Compra, DetalleCompra, Proveedor
from inventario.models import Categoria, Material, Producto
from ventas.models import Cliente, Ingreso
from ventas.services import registrar_venta

from .services import responder_mensaje, sugerencias_iniciales


class AnahiBotBaseTestCase(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="bot_staff",
            password="Test12345!",
            is_staff=True,
        )
        self.usuario = get_user_model().objects.create_user(
            username="bot_user",
            password="Test12345!",
        )
        self.categoria = Categoria.objects.create(
            nombre="Dormitorio",
        )
        self.categoria_comedor = Categoria.objects.create(
            nombre="Comedor",
        )
        self.producto = Producto.objects.create(
            codigo="CAM-001",
            nombre="Cama matrimonial",
            categoria=self.categoria,
            precio=Decimal("250.00"),
            stock=10,
            stock_minimo=3,
        )
        self.producto_agotado = Producto.objects.create(
            codigo="MES-001",
            nombre="Mesa de comedor",
            categoria=self.categoria_comedor,
            precio=Decimal("500.00"),
            stock=0,
            stock_minimo=2,
        )
        self.producto_bajo = Producto.objects.create(
            codigo="SIL-001",
            nombre="Silla baja",
            categoria=self.categoria_comedor,
            precio=Decimal("100.00"),
            stock=1,
            stock_minimo=5,
        )
        self.producto_inactivo = Producto.objects.create(
            codigo="INA-001",
            nombre="Producto inactivo",
            categoria=self.categoria,
            precio=Decimal("999.00"),
            stock=5,
            stock_minimo=1,
            activo=False,
        )
        self.producto_vendido = Producto.objects.create(
            codigo="COM-001",
            nombre="Comedor vendido",
            categoria=self.categoria_comedor,
            precio=Decimal("500.00"),
            stock=50,
            stock_minimo=5,
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
        self.proveedor = Proveedor.objects.create(
            nombre="Maderas del Sur",
            nit="123456",
            telefono="70000000",
            email="compras@maderas.example",
        )
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            numero_documento="FAC-001",
            total=Decimal("800.00"),
            creado_por=self.staff,
        )
        DetalleCompra.objects.create(
            compra=compra,
            material=self.material,
            cantidad=Decimal("10.00"),
            costo_unitario=Decimal("80.00"),
        )
        self.cliente = Cliente.objects.create(nombre="Cliente Bot")
        self.venta = registrar_venta(
            cliente=self.cliente,
            items=[
                {
                    "producto": self.producto_vendido,
                    "cantidad": 2,
                }
            ],
            usuario=self.staff,
            metodo_pago=Ingreso.EFECTIVO,
        )

    def preguntar(self, texto, usuario=None):
        return responder_mensaje(texto, usuario or self.staff)


class AnahiBotServiceTests(AnahiBotBaseTestCase):
    def test_saludo(self):
        respuesta = self.preguntar("Hola")

        self.assertEqual(respuesta["intencion"], "saludo")
        self.assertIn("AnahíBot", respuesta["respuesta"])
        self.assertTrue(respuesta["sugerencias"])

    def test_ayuda_muestra_capacidades(self):
        respuesta = self.preguntar("¿Qué puedes hacer?")

        self.assertEqual(respuesta["intencion"], "ayuda")
        self.assertIn("Precio, stock", respuesta["respuesta"])
        self.assertIn("Ventas, ingresos", respuesta["respuesta"])
        self.assertIn("No invento datos", respuesta["respuesta"])

    def test_ayuda_usuario_sin_permisos(self):
        respuesta = self.preguntar("ayuda", self.usuario)

        self.assertIn(
            "requieren permisos de administración",
            respuesta["respuesta"],
        )

    def test_producto_por_nombre(self):
        respuesta = self.preguntar(
            "¿Cuánto cuesta la cama matrimonial?"
        )

        self.assertEqual(respuesta["intencion"], "producto")
        self.assertIn("Cama matrimonial (CAM-001)", respuesta["respuesta"])
        self.assertIn("Bs 250,00", respuesta["respuesta"])
        self.assertIn("Stock: 10 unidad(es)", respuesta["respuesta"])
        self.assertIn("Disponible", respuesta["respuesta"])

    def test_producto_por_codigo(self):
        respuesta = self.preguntar("stock de CAM-001")

        self.assertEqual(respuesta["intencion"], "producto")
        self.assertIn("Cama matrimonial", respuesta["respuesta"])
        self.assertIn("Bs 250,00", respuesta["respuesta"])

    def test_producto_agotado_distingue_cero(self):
        respuesta = self.preguntar("precio de mesa de comedor")

        self.assertIn("Agotado", respuesta["respuesta"])
        self.assertIn(
            "stock registrado es cero",
            respuesta["respuesta"],
        )
        self.assertIn("Bs 500,00", respuesta["respuesta"])

    def test_producto_inexistente_no_inventa(self):
        respuesta = self.preguntar("precio de lámpara")

        self.assertEqual(respuesta["intencion"], "sin_resultados")
        self.assertIn(
            "No encontré ningún producto ni material",
            respuesta["respuesta"],
        )
        self.assertIn("No hay datos registrados", respuesta["respuesta"])

    def test_material_por_nombre(self):
        respuesta = self.preguntar("stock de madera roble")

        self.assertEqual(respuesta["intencion"], "material")
        self.assertIn("Madera roble (MAD-001)", respuesta["respuesta"])
        self.assertIn("Costo de referencia: Bs 80,00", respuesta["respuesta"])
        self.assertIn("Stock bajo", respuesta["respuesta"])

    def test_productos_ambiguos_pide_precision(self):
        Producto.objects.create(
            codigo="CAM-002",
            nombre="Cama individual",
            categoria=self.categoria,
            precio=Decimal("200.00"),
            stock=4,
            stock_minimo=1,
        )

        respuesta = self.preguntar("precio de cama")

        self.assertEqual(respuesta["intencion"], "producto_ambigüo")
        self.assertIn("Encontré 2 productos", respuesta["respuesta"])
        self.assertIn("CAM-001", respuesta["respuesta"])
        self.assertIn("CAM-002", respuesta["respuesta"])

    def test_acentos_y_plurales(self):
        respuesta = self.preguntar("cuanto cuestan las camas")

        self.assertEqual(respuesta["intencion"], "producto")
        self.assertIn("Cama matrimonial", respuesta["respuesta"])

    def test_stock_bajo_lista_productos_y_materiales(self):
        respuesta = self.preguntar(
            "¿Qué productos tienen stock bajo?"
        )

        self.assertEqual(respuesta["intencion"], "stock_bajo")
        self.assertIn("requieren reposición", respuesta["respuesta"])
        self.assertIn("Mesa de comedor", respuesta["respuesta"])
        self.assertIn("Silla baja", respuesta["respuesta"])
        self.assertIn("Madera roble", respuesta["respuesta"])
        self.assertIn("Pegamento", respuesta["respuesta"])

    def test_agotados(self):
        respuesta = self.preguntar("¿Qué está agotado?")

        self.assertEqual(respuesta["intencion"], "agotados")
        self.assertIn("Mesa de comedor", respuesta["respuesta"])
        self.assertIn("Pegamento", respuesta["respuesta"])
        self.assertNotIn("Cama matrimonial", respuesta["respuesta"])

    def test_resumen_inventario(self):
        respuesta = self.preguntar("inventario")

        self.assertEqual(respuesta["intencion"], "inventario")
        self.assertIn("Productos: 4 registrados", respuesta["respuesta"])
        self.assertIn("1 agotados", respuesta["respuesta"])
        self.assertIn("1 con stock bajo", respuesta["respuesta"])
        self.assertIn("2 disponibles", respuesta["respuesta"])
        self.assertIn("Bs 26600,00", respuesta["respuesta"])
        self.assertIn("Materiales: 2 registrados", respuesta["respuesta"])

    def test_resumen_inventario_desde_consulta_de_stock(self):
        respuesta = self.preguntar("stock")

        self.assertEqual(respuesta["intencion"], "inventario")
        self.assertIn("Inventario actual", respuesta["respuesta"])

    def test_catalogo_productos(self):
        respuesta = self.preguntar("¿Qué productos hay?")

        self.assertEqual(respuesta["intencion"], "catalogo")
        self.assertIn("Hay 4 producto(s) activo(s)", respuesta["respuesta"])
        self.assertIn("Cama matrimonial", respuesta["respuesta"])
        self.assertNotIn("Producto inactivo", respuesta["respuesta"])

    def test_proveedores_lista_solo_staff(self):
        respuesta = self.preguntar("proveedores registrados")

        self.assertEqual(respuesta["intencion"], "proveedores")
        self.assertIn("Maderas del Sur", respuesta["respuesta"])
        self.assertIn("70000000", respuesta["respuesta"])

    def test_proveedor_de_material_con_compras(self):
        respuesta = self.preguntar("proveedores de madera")

        self.assertEqual(respuesta["intencion"], "proveedores")
        self.assertIn("Madera roble", respuesta["respuesta"])
        self.assertIn("Maderas del Sur", respuesta["respuesta"])
        self.assertIn("1 compra(s)", respuesta["respuesta"])

    def test_proveedor_de_material_sin_compras(self):
        respuesta = self.preguntar("proveedores de pegamento")

        self.assertIn("Pegamento", respuesta["respuesta"])
        self.assertIn(
            "no tiene compras registradas (0 compras)",
            respuesta["respuesta"],
        )

    def test_proveedor_de_material_inexistente(self):
        respuesta = self.preguntar("proveedores de acero")

        self.assertEqual(
            respuesta["intencion"],
            "proveedores_sin_resultados",
        )
        self.assertIn(
            "No encontré ningún material",
            respuesta["respuesta"],
        )

    def test_proveedores_sin_registros(self):
        Proveedor.objects.update(activo=False)

        respuesta = self.preguntar("proveedores")

        self.assertIn(
            "No hay proveedores activos registrados (0)",
            respuesta["respuesta"],
        )

    def test_proveedores_requiere_staff(self):
        respuesta = self.preguntar("proveedores", self.usuario)

        self.assertEqual(respuesta["intencion"], "permiso_denegado")
        self.assertIn("permisos de administración", respuesta["respuesta"])
        self.assertNotIn("Maderas del Sur", respuesta["respuesta"])

    def test_ventas_resumen_mes(self):
        respuesta = self.preguntar("¿Cuánto vendí este mes?")

        self.assertEqual(respuesta["intencion"], "ventas")
        self.assertIn(
            "Ventas completadas en este mes: 1",
            respuesta["respuesta"],
        )
        self.assertIn("Ingresos: Bs 1000,00", respuesta["respuesta"])
        self.assertIn("Ticket promedio: Bs 1000,00", respuesta["respuesta"])
        self.assertIn("Unidades vendidas: 2", respuesta["respuesta"])

    def test_ventas_sin_datos_distingue_cero(self):
        respuesta = self.preguntar("¿Cuánto vendí ayer?")

        self.assertIn(
            "No hay ventas completadas registradas en ayer",
            respuesta["respuesta"],
        )
        self.assertIn("Total: Bs 0,00", respuesta["respuesta"])
        self.assertIn("dato es cero", respuesta["respuesta"])

    def test_ventas_requiere_staff(self):
        respuesta = self.preguntar("¿Cuánto vendí este mes?", self.usuario)

        self.assertEqual(respuesta["intencion"], "permiso_denegado")
        self.assertIn("permisos de administración", respuesta["respuesta"])
        self.assertNotIn("Bs 1000,00", respuesta["respuesta"])

    def test_productos_mas_vendidos(self):
        respuesta = self.preguntar("¿Qué productos se vendieron más?")

        self.assertEqual(
            respuesta["intencion"],
            "productos_mas_vendidos",
        )
        self.assertIn("Comedor vendido (COM-001)", respuesta["respuesta"])
        self.assertIn("2 unidad(es)", respuesta["respuesta"])
        self.assertIn("Bs 1000,00", respuesta["respuesta"])

    def test_productos_mas_vendidos_sin_datos(self):
        respuesta = self.preguntar("productos más vendidos ayer")

        self.assertIn(
            "No hay productos vendidos en ayer (0 unidades)",
            respuesta["respuesta"],
        )

    def test_recomendaciones_staff(self):
        respuesta = self.preguntar("¿Qué me recomiendas reponer?")

        self.assertEqual(respuesta["intencion"], "recomendaciones")
        self.assertIn("Reponer o revisar", respuesta["respuesta"])
        self.assertIn("Mesa de comedor", respuesta["respuesta"])
        self.assertIn(
            "Priorizar ventas de este mes",
            respuesta["respuesta"],
        )
        self.assertIn("Comedor vendido", respuesta["respuesta"])

    def test_recomendaciones_usuario_sin_ventas(self):
        respuesta = self.preguntar(
            "\u00bfQu\u00e9 me recomiendas reponer?",
            self.usuario,
        )

        self.assertEqual(
            respuesta["intencion"],
            "permiso_denegado",
        )
        self.assertIn(
            "permisos de administraci\u00f3n",
            respuesta["respuesta"],
        )
        self.assertNotIn(
            "Priorizar ventas",
            respuesta["respuesta"],
        )

    def test_no_entendido(self):
        respuesta = self.preguntar("gracias")

        self.assertEqual(respuesta["intencion"], "no_entendido")
        self.assertIn("No entendí la consulta", respuesta["respuesta"])
        self.assertIn("no voy a inventar", respuesta["respuesta"])

    def test_sugerencias_iniciales_con_datos_reales(self):
        staff = sugerencias_iniciales(self.staff)
        usuario = sugerencias_iniciales(self.usuario)

        self.assertIn(
            "¿Cuánto cuesta Cama matrimonial?",
            staff,
        )
        self.assertIn("¿Cuánto vendí este mes?", staff)
        self.assertNotIn("¿Cuánto vendí este mes?", usuario)


class AnahiBotViewTests(AnahiBotBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(
            username="bot_staff",
            password="Test12345!",
        )

    def test_pagina_requiere_login(self):
        self.client.logout()

        respuesta = self.client.get(reverse("anahibot:index"))

        self.assertEqual(respuesta.status_code, 302)

    def test_pagina_muestra_chat(self):
        respuesta = self.client.get(reverse("anahibot:index"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "AnahíBot")
        self.assertContains(respuesta, "chat-form")
        self.assertContains(
            respuesta,
            reverse("anahibot:responder"),
        )
        self.assertContains(respuesta, "Datos en vivo")

    def test_api_requiere_login(self):
        self.client.logout()

        respuesta = self.client.post(
            reverse("anahibot:responder"),
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 302)

    def test_api_requiere_post(self):
        respuesta = self.client.get(reverse("anahibot:responder"))

        self.assertEqual(respuesta.status_code, 405)

    def test_api_json_invalido(self):
        respuesta = self.client.post(
            reverse("anahibot:responder"),
            data="{no-json",
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("JSON válido", respuesta.json()["error"])

    def test_api_json_no_objeto(self):
        respuesta = self.client.post(
            reverse("anahibot:responder"),
            data=json.dumps(["hola"]),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("objeto JSON", respuesta.json()["error"])

    def test_api_mensaje_invalido(self):
        respuesta = self.client.post(
            reverse("anahibot:responder"),
            data=json.dumps({"mensaje": 123}),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("campo «mensaje»", respuesta.json()["error"])

    def test_api_mensaje_vacio(self):
        respuesta = self.client.post(
            reverse("anahibot:responder"),
            data=json.dumps({"mensaje": "   "}),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Escribe una consulta", respuesta.json()["error"])

    def test_api_mensaje_muy_largo(self):
        respuesta = self.client.post(
            reverse("anahibot:responder"),
            data=json.dumps({"mensaje": "x" * 501}),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("500 caracteres", respuesta.json()["error"])

    def test_api_respuesta_valida(self):
        respuesta = self.client.post(
            reverse("anahibot:responder"),
            data=json.dumps(
                {"mensaje": "¿Cuánto cuesta la cama matrimonial?"}
            ),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["intencion"], "producto")
        self.assertIn("Cama matrimonial", datos["respuesta"])
        self.assertIn("Bs 250,00", datos["respuesta"])
        self.assertTrue(datos["sugerencias"])

    def test_api_respeta_permisos(self):
        self.client.logout()
        self.client.login(
            username="bot_user",
            password="Test12345!",
        )

        respuesta = self.client.post(
            reverse("anahibot:responder"),
            data=json.dumps({"mensaje": "¿Cuánto vendí este mes?"}),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["intencion"], "permiso_denegado")
        self.assertNotIn("Bs 1000,00", datos["respuesta"])

    def test_api_exige_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.login(
            username="bot_staff",
            password="Test12345!",
        )

        sin_token = cliente.post(
            reverse("anahibot:responder"),
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        self.assertEqual(sin_token.status_code, 403)

        cliente.get(reverse("anahibot:index"))
        token = cliente.cookies["csrftoken"].value

        con_token = cliente.post(
            reverse("anahibot:responder"),
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(con_token.status_code, 200)
