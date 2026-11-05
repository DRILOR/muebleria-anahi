from decimal import Decimal
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from .models import (
    Categoria,
    Material,
    MedidaProducto,
    MovimientoInventario,
    Producto,
)
from .services import registrar_movimiento
from .management.commands import cargar_imagenes_demo
from PIL import Image


class InventarioModelTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nombre="Dormitorio",
            descripcion="Muebles de dormitorio",
        )

        self.producto = Producto.objects.create(
            codigo="CAM-001",
            nombre="Cama matrimonial",
            categoria=self.categoria,
            precio=Decimal("2500.00"),
            stock=3,
            stock_minimo=1,
        )

    def test_categoria_str(self):
        self.assertEqual(
            str(self.categoria),
            "Dormitorio",
        )

    def test_producto_str(self):
        self.assertEqual(
            str(self.producto),
            "CAM-001 - Cama matrimonial",
        )

    def test_producto_stock_bajo(self):
        self.producto.stock = 1
        self.assertTrue(
            self.producto.stock_bajo
        )

        self.producto.stock = 5
        self.assertFalse(
            self.producto.stock_bajo
        )

    def test_medida_producto(self):
        medida = MedidaProducto.objects.create(
            producto=self.producto,
            alto_cm=Decimal("110"),
            ancho_cm=Decimal("160"),
            profundidad_cm=Decimal("200"),
        )

        self.assertIn(
            "Cama matrimonial",
            str(medida),
        )


class MovimientoInventarioTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester",
            password="Test12345!",
        )

        self.material = Material.objects.create(
            codigo="MAD-001",
            nombre="Madera roble",
            unidad_medida=Material.TABLON,
            stock=Decimal("0"),
            stock_minimo=Decimal("10"),
            costo_referencia=Decimal("80"),
        )

    def test_entrada_incrementa_stock(self):
        movimiento = registrar_movimiento(
            material_id=self.material.pk,
            tipo=MovimientoInventario.ENTRADA,
            cantidad=50,
            motivo="Stock inicial",
            usuario=self.user,
        )

        self.material.refresh_from_db()

        self.assertEqual(
            self.material.stock,
            Decimal("50"),
        )

        self.assertEqual(
            movimiento.stock_anterior,
            Decimal("0"),
        )

        self.assertEqual(
            movimiento.stock_resultante,
            Decimal("50"),
        )

    def test_salida_reduce_stock(self):
        registrar_movimiento(
            self.material.pk,
            MovimientoInventario.ENTRADA,
            50,
            "Stock inicial",
            self.user,
        )

        registrar_movimiento(
            self.material.pk,
            MovimientoInventario.SALIDA,
            5,
            "Fabricación",
            self.user,
        )

        self.material.refresh_from_db()

        self.assertEqual(
            self.material.stock,
            Decimal("45"),
        )

    def test_no_permite_stock_negativo(self):
        registrar_movimiento(
            self.material.pk,
            MovimientoInventario.ENTRADA,
            20,
            "Stock inicial",
            self.user,
        )

        with self.assertRaises(ValidationError):
            registrar_movimiento(
                self.material.pk,
                MovimientoInventario.SALIDA,
                100,
                "Salida inválida",
                self.user,
            )

        self.material.refresh_from_db()

        self.assertEqual(
            self.material.stock,
            Decimal("20"),
        )

    def test_rechaza_cantidad_cero(self):
        with self.assertRaises(
            ValidationError
        ):
            registrar_movimiento(
                self.material.pk,
                MovimientoInventario.ENTRADA,
                0,
                "Inválido",
                self.user,
            )


class ProductoViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin_test",
            password="Test12345!",
            is_staff=True,
        )

        self.client.login(
            username="admin_test",
            password="Test12345!",
        )

        self.categoria = Categoria.objects.create(
            nombre="Dormitorio",
        )

    def test_lista_productos(self):
        response = self.client.get(
            reverse(
                "inventario:producto_lista"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_crear_producto_con_medidas(self):
        response = self.client.post(
            reverse(
                "inventario:producto_crear"
            ),
            {
                "codigo": "MES-001",
                "nombre": "Mesa comedor",
                "descripcion": "Mesa de prueba",
                "categoria": self.categoria.pk,
                "precio": "1500.00",
                "stock": "2",
                "stock_minimo": "1",
                "activo": "on",
                "alto_cm": "80",
                "ancho_cm": "100",
                "profundidad_cm": "180",
                "observaciones": "",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        producto = Producto.objects.get(
            codigo="MES-001"
        )

        self.assertEqual(
            producto.nombre,
            "Mesa comedor",
        )

        self.assertTrue(
            MedidaProducto.objects.filter(
                producto=producto
            ).exists()
        )

    def test_editar_producto(self):
        producto = Producto.objects.create(
            codigo="SIL-001",
            nombre="Silla madera",
            categoria=self.categoria,
            precio=Decimal("300"),
            stock=5,
            stock_minimo=1,
        )

        MedidaProducto.objects.create(
            producto=producto,
            alto_cm=90,
            ancho_cm=45,
            profundidad_cm=45,
        )

        response = self.client.post(
            reverse(
                "inventario:producto_editar",
                args=[producto.pk],
            ),
            {
                "codigo": "SIL-001",
                "nombre": "Silla actualizada",
                "descripcion": "",
                "categoria": self.categoria.pk,
                "precio": "350",
                "stock": "5",
                "stock_minimo": "1",
                "activo": "on",
                "alto_cm": "90",
                "ancho_cm": "45",
                "profundidad_cm": "45",
                "observaciones": "",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.precio,
            Decimal("350"),
        )

    def test_desactivar_producto(self):
        producto = Producto.objects.create(
            codigo="ARM-001",
            nombre="Armario",
            categoria=self.categoria,
            precio=1000,
            stock=1,
            stock_minimo=1,
        )

        response = self.client.post(
            reverse(
                "inventario:producto_eliminar",
                args=[producto.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        producto.refresh_from_db()

        self.assertFalse(
            producto.activo
        )


class MaterialViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="material_test",
            password="Test12345!",
            is_staff=True,
        )

        self.client.login(
            username="material_test",
            password="Test12345!",
        )

        self.material = Material.objects.create(
            codigo="MAD-001",
            nombre="Madera roble",
            unidad_medida=Material.TABLON,
            stock=0,
            stock_minimo=10,
            costo_referencia=80,
        )

    def test_lista_materiales(self):
        response = self.client.get(
            reverse(
                "inventario:material_lista"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_registrar_movimiento_desde_vista(self):
        response = self.client.post(
            reverse(
                "inventario:movimiento_crear"
            ),
            {
                "material": self.material.pk,
                "tipo": MovimientoInventario.ENTRADA,
                "cantidad": "20",
                "motivo": "Prueba",
                "referencia": "TEST",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.material.refresh_from_db()

        self.assertEqual(
            self.material.stock,
            Decimal("20"),
        )

    def test_crear_material_vista_get_y_post(self):
        url = reverse("inventario:material_crear")
        get_res = self.client.get(url)
        self.assertEqual(get_res.status_code, 200)

        post_res = self.client.post(
            url,
            {
                "codigo": "BAR-001",
                "nombre": "Barniz poliuretano",
                "unidad_medida": Material.LITRO,
                "stock": "10.00",
                "stock_minimo": "2.00",
                "costo_referencia": "45.00",
                "activo": "on",
            },
        )
        self.assertEqual(post_res.status_code, 302)
        self.assertTrue(Material.objects.filter(codigo="BAR-001").exists())

    def test_editar_material_vista_get_y_post(self):
        url = reverse("inventario:material_editar", args=[self.material.pk])
        get_res = self.client.get(url)
        self.assertEqual(get_res.status_code, 200)

        post_res = self.client.post(
            url,
            {
                "codigo": "MAD-001",
                "nombre": "Madera roble seleccionada",
                "unidad_medida": Material.TABLON,
                "stock": "5.00",
                "stock_minimo": "10.00",
                "costo_referencia": "95.00",
                "activo": "on",
            },
        )
        self.assertEqual(post_res.status_code, 302)
        self.material.refresh_from_db()
        self.assertEqual(self.material.nombre, "Madera roble seleccionada")

    def test_historial_movimientos_vista(self):
        registrar_movimiento(
            material_id=self.material.pk,
            tipo=MovimientoInventario.ENTRADA,
            cantidad=15,
            motivo="Entrada prueba",
            usuario=self.user,
        )
        response = self.client.get(reverse("inventario:movimiento_historial"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entrada prueba")

    def test_lista_materiales_filtro_busqueda(self):
        response = self.client.get(reverse("inventario:material_lista") + "?q=roble")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Madera roble")

    def test_movimiento_crear_invalido_muestra_error(self):
        response = self.client.post(
            reverse("inventario:movimiento_crear"),
            {
                "material": self.material.pk,
                "tipo": MovimientoInventario.SALIDA,
                "cantidad": "999",
                "motivo": "Salida excesiva",
                "referencia": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stock insuficiente")


class CargarDemoCommandTests(TestCase):
    def test_cargar_demo_dry_run_no_modifica_db(self):
        from io import StringIO
        from django.core.management import call_command
        from compras.models import Compra
        from ventas.models import Venta

        out = StringIO()
        call_command("cargar_demo", dry_run=True, stdout=out)
        salida = out.getvalue()
        self.assertIn("MODO SIMULACIÓN", salida)
        self.assertIn("RESUMEN DE REGISTROS", salida)
        self.assertEqual(Producto.objects.count(), 0)
        self.assertEqual(Compra.objects.count(), 0)
        self.assertEqual(Venta.objects.count(), 0)

    def test_cargar_demo_ejecucion_real_e_idempotencia(self):
        from io import StringIO
        from django.core.management import call_command
        from compras.models import Compra, Proveedor
        from ventas.models import Cliente, Venta

        out1 = StringIO()
        call_command("cargar_demo", stdout=out1)
        self.assertIn("completada y guardada con éxito", out1.getvalue())


        self.assertGreaterEqual(Producto.objects.count(), 35)
        self.assertGreaterEqual(Material.objects.count(), 30)
        self.assertEqual(Proveedor.objects.count(), 12)
        self.assertEqual(Cliente.objects.count(), 40)
        self.assertEqual(Compra.objects.count(), 45)
        self.assertEqual(Venta.objects.count(), 100)
        self.assertEqual(Venta.objects.filter(estado=Venta.ESTADO_ANULADA).count(), 6)

        # Probar que AnahiBot y reportes responden con estos datos
        from anahibot.services import responder_mensaje
        user = get_user_model().objects.create_user(username="admin_test", is_staff=True)
        res_ventas = responder_mensaje("ventas de este mes", usuario=user)
        self.assertIn("ventas", res_ventas["respuesta"].lower())

        # Probar idempotencia: la segunda ejecución no duplica compras ni ventas.
        out2 = StringIO()
        call_command("cargar_demo", stdout=out2)
        self.assertEqual(Compra.objects.count(), 45)
        self.assertEqual(Venta.objects.count(), 100)


class CargarImagenesDemoCommandTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Imágenes demostrativas")

    def imagen_png(self):
        buffer = BytesIO()
        Image.new("RGB", (40, 30), "#806040").save(buffer, format="PNG")
        return buffer.getvalue()

    def test_asocia_por_codigo_optimiza_webp_y_no_reemplaza_fotografia_existente(self):
        with TemporaryDirectory() as media_dir, self.settings(MEDIA_ROOT=media_dir):
            nueva = Producto.objects.create(codigo="PRD-DOR-001", nombre="Cama", categoria=self.categoria, precio=100)
            existente = Producto.objects.create(codigo="PRD-DOR-002", nombre="Ropero", categoria=self.categoria, precio=200)
            existente.imagen.save("foto-propia.png", ContentFile(self.imagen_png()), save=True)
            nombre_original = existente.imagen.name
            original_bytes = existente.imagen.read()
            existente.imagen.close()
            with patch.object(cargar_imagenes_demo, "PRODUCT_IMAGES", {"PRD-DOR-001": "fuente", "PRD-DOR-002": "fuente"}), patch.object(cargar_imagenes_demo, "IMAGE_SOURCES", {"fuente": ("https://images.unsplash.com/photo-demo", "Autora", "https://unsplash.com/photos/demo")}), patch.object(cargar_imagenes_demo, "urlopen", return_value=BytesIO(self.imagen_png())) as urlopen_mock:
                call_command("cargar_imagenes_demo")
                nueva.refresh_from_db()
                existente.refresh_from_db()
                self.assertTrue(nueva.imagen.name.endswith(".webp"))
                with Image.open(nueva.imagen.path) as optimizada:
                    self.assertEqual(optimizada.format, "WEBP")
                self.assertEqual(existente.imagen.name, nombre_original)
                self.assertEqual(existente.imagen.read(), original_bytes)
                existente.imagen.close()
                self.assertEqual(urlopen_mock.call_count, 1)

    def test_simulacion_y_codigos_desconocidos_no_descargan_ni_modifican(self):
        producto = Producto.objects.create(codigo="PRD-DOR-001", nombre="Cama", categoria=self.categoria, precio=100)
        with patch.object(cargar_imagenes_demo, "PRODUCT_IMAGES", {"PRD-DOR-001": None, "PRD-XXX-999": "fuente"}), patch.object(cargar_imagenes_demo, "urlopen") as urlopen_mock:
            salida = StringIO()
            call_command("cargar_imagenes_demo", dry_run=True, stdout=salida)
            self.assertIn("Simulación completa", salida.getvalue())
            urlopen_mock.assert_not_called()
        producto.refresh_from_db()
        self.assertFalse(producto.imagen)

    def test_error_de_descarga_no_crea_imagen(self):
        from urllib.error import URLError

        producto = Producto.objects.create(codigo="PRD-DOR-001", nombre="Cama", categoria=self.categoria, precio=100)
        with patch.object(cargar_imagenes_demo, "PRODUCT_IMAGES", {"PRD-DOR-001": "fuente"}), patch.object(cargar_imagenes_demo, "IMAGE_SOURCES", {"fuente": ("https://images.unsplash.com/photo-demo", "Autora", "https://unsplash.com/photos/demo")}), patch.object(cargar_imagenes_demo, "urlopen", side_effect=URLError("sin conexión")):
            with self.assertRaises(CommandError):
                call_command("cargar_imagenes_demo")
        producto.refresh_from_db()
        self.assertFalse(producto.imagen)
