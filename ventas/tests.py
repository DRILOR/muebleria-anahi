from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from inventario.models import Categoria, Producto

from .forms import ClienteForm
from .models import (
    Cliente,
    DetalleVenta,
    Ingreso,
    MovimientoProducto,
    Venta,
)
from .services import anular_venta, registrar_venta


class BaseVentaTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ventas_test",
            password="Test12345!",
        )
        self.staff = get_user_model().objects.create_user(
            username="staff_test",
            password="Test12345!",
            is_staff=True,
        )
        self.cliente = Cliente.objects.create(
            nombre="María Fernanda López",
            nit="12345678",
            telefono="70012345",
            email="maria@example.com",
        )
        self.cliente_inactivo = Cliente.objects.create(
            nombre="Cliente Inactivo",
            activo=False,
        )
        self.categoria = Categoria.objects.create(
            nombre="Dormitorio",
        )
        self.producto = Producto.objects.create(
            codigo="CAM-001",
            nombre="Cama matrimonial",
            categoria=self.categoria,
            precio=Decimal("250.50"),
            stock=10,
            stock_minimo=2,
        )
        self.producto_2 = Producto.objects.create(
            codigo="VEL-001",
            nombre="Velador de madera",
            categoria=self.categoria,
            precio=Decimal("100.00"),
            stock=2,
            stock_minimo=1,
        )

    def crear_venta(self, **kwargs):
        datos = {
            "cliente": self.cliente,
            "items": [
                {"producto": self.producto, "cantidad": 2},
                {"producto": self.producto_2, "cantidad": 1},
            ],
            "usuario": self.user,
        }
        datos.update(kwargs)
        return registrar_venta(**datos)


class ClienteModelTests(BaseVentaTestCase):
    def test_cliente_str_y_propiedades(self):
        venta = self.crear_venta()

        self.assertEqual(str(self.cliente), "María Fernanda López")
        self.assertEqual(self.cliente.cantidad_ventas, 1)
        self.assertEqual(
            self.cliente.total_comprado,
            venta.total,
        )

    def test_cliente_sin_ventas_total_cero(self):
        self.assertEqual(self.cliente.cantidad_ventas, 0)
        self.assertEqual(
            self.cliente.total_comprado,
            Decimal("0.00"),
        )

    def test_cliente_form_valida_nombre_y_nit(self):
        form = ClienteForm(
            data={
                "nombre": "  Ana Pérez  ",
                "nit": " abc-1 ",
                "telefono": " 70000000 ",
                "email": "",
                "direccion": "",
                "activo": "on",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["nombre"], "Ana Pérez")
        self.assertEqual(form.cleaned_data["nit"], "ABC-1")
        self.assertEqual(form.cleaned_data["telefono"], "70000000")

    def test_cliente_form_rechaza_nombre_corto(self):
        form = ClienteForm(
            data={
                "nombre": "Al",
                "activo": "on",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("nombre", form.errors)


class VentaModelTests(BaseVentaTestCase):
    def test_numero_se_genera_al_guardar(self):
        venta = Venta.objects.create(cliente=self.cliente)

        self.assertEqual(venta.numero, f"VEN-{venta.pk:06d}")
        self.assertFalse(venta.esta_anulada)

    def test_str_de_modelos(self):
        venta = self.crear_venta()
        detalle = venta.detalles.first()
        ingreso = venta.ingreso
        movimiento = MovimientoProducto.objects.filter(
            venta=venta
        ).first()

        self.assertIn(venta.numero, str(venta))
        self.assertIn("Cama matrimonial", str(detalle))
        self.assertIn(venta.numero, str(ingreso))
        self.assertIn("SALIDA", str(movimiento))


class VentaServiceTests(BaseVentaTestCase):
    def test_registrar_venta_completa_operacion(self):
        venta = self.crear_venta(
            metodo_pago=Ingreso.TRANSFERENCIA,
            referencia_pago=" TRF-001 ",
            observaciones="Entrega a domicilio",
        )

        self.producto.refresh_from_db()
        self.producto_2.refresh_from_db()
        venta.refresh_from_db()

        self.assertEqual(venta.total, Decimal("601.00"))
        self.assertEqual(venta.estado, Venta.ESTADO_COMPLETADA)
        self.assertEqual(self.producto.stock, 8)
        self.assertEqual(self.producto_2.stock, 1)
        self.assertEqual(venta.detalles.count(), 2)
        self.assertEqual(venta.ingreso.monto, Decimal("601.00"))
        self.assertEqual(
            venta.ingreso.metodo_pago,
            Ingreso.TRANSFERENCIA,
        )
        self.assertEqual(venta.ingreso.referencia, "TRF-001")
        self.assertEqual(
            MovimientoProducto.objects.filter(
                venta=venta,
                tipo=MovimientoProducto.SALIDA,
            ).count(),
            2,
        )
        self.assertEqual(venta.observaciones, "Entrega a domicilio")

    def test_agrupa_lineas_del_mismo_producto(self):
        venta = self.crear_venta(
            items=[
                {"producto": self.producto, "cantidad": 2},
                {"producto": self.producto, "cantidad": 3},
            ]
        )
        self.producto.refresh_from_db()

        self.assertEqual(self.producto.stock, 5)
        self.assertEqual(venta.detalles.count(), 1)
        self.assertEqual(venta.detalles.first().cantidad, 5)

    def test_precio_se_toma_de_la_base_de_datos(self):
        venta = registrar_venta(
            cliente=self.cliente.pk,
            items=[
                {
                    "producto": self.producto.pk,
                    "cantidad": "2",
                    "precio_unitario": "1.00",
                },
            ],
            usuario=self.user,
        )

        self.assertEqual(venta.total, Decimal("501.00"))

    def test_rechaza_stock_insuficiente_sin_cambios(self):
        with self.assertRaises(ValidationError):
            registrar_venta(
                cliente=self.cliente,
                items=[
                    {"producto": self.producto, "cantidad": 20},
                ],
                usuario=self.user,
            )

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
        self.assertEqual(Venta.objects.count(), 0)

    def test_rechaza_venta_sin_productos(self):
        with self.assertRaises(ValidationError):
            registrar_venta(
                cliente=self.cliente,
                items=[],
                usuario=self.user,
            )

    def test_rechaza_cantidades_invalidas(self):
        cantidades_invalidas = [0, -1, "abc", Decimal("1.5"), None]

        for cantidad in cantidades_invalidas:
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(ValidationError):
                    registrar_venta(
                        cliente=self.cliente,
                        items=[
                            {
                                "producto": self.producto,
                                "cantidad": cantidad,
                            },
                        ],
                        usuario=self.user,
                    )

    def test_rechaza_cliente_inactivo(self):
        with self.assertRaises(ValidationError):
            registrar_venta(
                cliente=self.cliente_inactivo,
                items=[
                    {"producto": self.producto, "cantidad": 1},
                ],
                usuario=self.user,
            )

    def test_rechaza_cliente_inexistente(self):
        with self.assertRaises(ValidationError):
            registrar_venta(
                cliente=99999,
                items=[
                    {"producto": self.producto, "cantidad": 1},
                ],
                usuario=self.user,
            )

    def test_rechaza_producto_inexistente(self):
        with self.assertRaises(ValidationError):
            registrar_venta(
                cliente=self.cliente,
                items=[
                    {"producto": 99999, "cantidad": 1},
                ],
                usuario=self.user,
            )

    def test_rechaza_producto_inactivo(self):
        self.producto.activo = False
        self.producto.save(update_fields=["activo"])

        with self.assertRaises(ValidationError):
            registrar_venta(
                cliente=self.cliente,
                items=[
                    {"producto": self.producto, "cantidad": 1},
                ],
                usuario=self.user,
            )

    def test_rechaza_metodo_pago_invalido(self):
        with self.assertRaises(ValidationError):
            registrar_venta(
                cliente=self.cliente,
                items=[
                    {"producto": self.producto, "cantidad": 1},
                ],
                usuario=self.user,
                metodo_pago="BITCOIN",
            )

    def test_rechaza_item_sin_producto(self):
        with self.assertRaises(ValidationError):
            registrar_venta(
                cliente=self.cliente,
                items=[{"producto": None, "cantidad": 1}],
                usuario=self.user,
            )

    def test_anular_venta_restaura_stock(self):
        venta = self.crear_venta()

        anulada = anular_venta(
            venta=venta,
            usuario=self.staff,
            motivo="Devolución",
        )

        anulada.refresh_from_db()
        self.producto.refresh_from_db()
        self.producto_2.refresh_from_db()

        self.assertEqual(anulada.estado, Venta.ESTADO_ANULADA)
        self.assertEqual(self.producto.stock, 10)
        self.assertEqual(self.producto_2.stock, 2)
        self.assertEqual(
            MovimientoProducto.objects.filter(
                venta=venta,
                tipo=MovimientoProducto.ENTRADA,
            ).count(),
            2,
        )

    def test_no_permite_anular_dos_veces(self):
        venta = self.crear_venta()
        anular_venta(venta=venta, usuario=self.staff)

        with self.assertRaises(ValidationError):
            anular_venta(venta=venta, usuario=self.staff)


class ClienteViewTests(BaseVentaTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(
            username="ventas_test",
            password="Test12345!",
        )

    def test_lista_clientes_y_busqueda(self):
        response = self.client.get(
            reverse("ventas:cliente_lista")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "María Fernanda López")

        response = self.client.get(
            reverse("ventas:cliente_lista"),
            {"q": "12345678"},
        )
        self.assertContains(response, "María Fernanda López")

        response = self.client.get(
            reverse("ventas:cliente_lista"),
            {"estado": "inactivos"},
        )
        self.assertContains(response, "Cliente Inactivo")
        self.assertNotContains(response, "María Fernanda López")

        response = self.client.get(
            reverse("ventas:cliente_lista"),
            {"estado": "todos"},
        )
        self.assertContains(response, "Cliente Inactivo")
        self.assertContains(response, "María Fernanda López")

    def test_crear_cliente(self):
        response = self.client.post(
            reverse("ventas:cliente_crear"),
            {
                "nombre": "Carlos Rojas",
                "nit": "998877",
                "telefono": "71111111",
                "email": "carlos@example.com",
                "direccion": "Centro",
                "activo": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse("ventas:cliente_lista"),
        )
        self.assertTrue(
            Cliente.objects.filter(
                nombre="Carlos Rojas",
            ).exists()
        )

    def test_editar_cliente(self):
        response = self.client.post(
            reverse(
                "ventas:cliente_editar",
                args=[self.cliente.pk],
            ),
            {
                "nombre": "María López Actualizada",
                "nit": "12345678",
                "telefono": "70012345",
                "email": "maria@example.com",
                "direccion": "Nueva dirección",
                "activo": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse("ventas:cliente_lista"),
        )
        self.cliente.refresh_from_db()
        self.assertEqual(
            self.cliente.nombre,
            "María López Actualizada",
        )

    def test_desactivar_cliente_es_logico(self):
        venta = self.crear_venta()

        response = self.client.post(
            reverse(
                "ventas:cliente_eliminar",
                args=[self.cliente.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("ventas:cliente_lista"),
        )
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.activo)
        self.assertTrue(
            Venta.objects.filter(pk=venta.pk).exists()
        )

    def test_desactivar_cliente_ya_inactivo(self):
        response = self.client.post(
            reverse(
                "ventas:cliente_eliminar",
                args=[self.cliente_inactivo.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("ventas:cliente_lista"),
        )

    def test_detalle_cliente(self):
        self.crear_venta()

        response = self.client.get(
            reverse(
                "ventas:cliente_detalle",
                args=[self.cliente.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "María Fernanda López")
        self.assertContains(response, "VEN-")

    def test_paginacion_clientes(self):
        for indice in range(18):
            Cliente.objects.create(
                nombre=f"Cliente paginado {indice:02d}"
            )

        response = self.client.get(
            reverse("ventas:cliente_lista"),
            {"page": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)


class VentaViewTests(BaseVentaTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(
            username="ventas_test",
            password="Test12345!",
        )

    def test_lista_ventas_y_filtros(self):
        venta = self.crear_venta()

        response = self.client.get(reverse("ventas:venta_lista"))
        self.assertContains(response, venta.numero)

        response = self.client.get(
            reverse("ventas:venta_lista"),
            {"q": venta.numero},
        )
        self.assertContains(response, venta.numero)

        response = self.client.get(
            reverse("ventas:venta_lista"),
            {"estado": Venta.ESTADO_ANULADA},
        )
        self.assertNotContains(response, venta.numero)

        response = self.client.get(
            reverse("ventas:venta_lista"),
            {
                "desde": timezone.localdate().isoformat(),
                "hasta": timezone.localdate().isoformat(),
            },
        )
        self.assertContains(response, venta.numero)

    def test_lista_ventas_fecha_invalida(self):
        response = self.client.get(
            reverse("ventas:venta_lista"),
            {"desde": "fecha-mala"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "debe tener el formato AAAA-MM-DD",
        )

    def test_formulario_venta_get(self):
        response = self.client.get(reverse("ventas:venta_crear"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registrar venta")
        self.assertContains(response, "productos-datos")

    def test_crear_venta_desde_vista(self):
        response = self.client.post(
            reverse("ventas:venta_crear"),
            {
                "cliente": self.cliente.pk,
                "metodo_pago": Ingreso.EFECTIVO,
                "referencia_pago": "",
                "observaciones": "Venta de prueba",
                "detalle-TOTAL_FORMS": "2",
                "detalle-INITIAL_FORMS": "0",
                "detalle-MIN_NUM_FORMS": "1",
                "detalle-MAX_NUM_FORMS": "1000",
                "detalle-0-producto": self.producto.pk,
                "detalle-0-cantidad": "2",
                "detalle-1-producto": self.producto_2.pk,
                "detalle-1-cantidad": "1",
            },
        )

        venta = Venta.objects.get()

        self.assertRedirects(
            response,
            reverse("ventas:venta_detalle", args=[venta.pk]),
        )
        self.assertEqual(venta.total, Decimal("601.00"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)

    def test_venta_sin_lineas_muestra_error(self):
        response = self.client.post(
            reverse("ventas:venta_crear"),
            {
                "cliente": self.cliente.pk,
                "metodo_pago": Ingreso.EFECTIVO,
                "referencia_pago": "",
                "observaciones": "",
                "detalle-TOTAL_FORMS": "1",
                "detalle-INITIAL_FORMS": "0",
                "detalle-MIN_NUM_FORMS": "1",
                "detalle-MAX_NUM_FORMS": "1000",
                "detalle-0-producto": "",
                "detalle-0-cantidad": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "al menos un producto",
        )

    def test_venta_con_stock_insuficiente_muestra_error(self):
        response = self.client.post(
            reverse("ventas:venta_crear"),
            {
                "cliente": self.cliente.pk,
                "metodo_pago": Ingreso.EFECTIVO,
                "referencia_pago": "",
                "observaciones": "",
                "detalle-TOTAL_FORMS": "1",
                "detalle-INITIAL_FORMS": "0",
                "detalle-MIN_NUM_FORMS": "1",
                "detalle-MAX_NUM_FORMS": "1000",
                "detalle-0-producto": self.producto_2.pk,
                "detalle-0-cantidad": "50",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stock insuficiente")
        self.assertEqual(Venta.objects.count(), 0)

    def test_detalle_comprobante_y_pdf(self):
        venta = self.crear_venta(observaciones="Prueba PDF")

        for nombre in (
            "ventas:venta_detalle",
            "ventas:venta_comprobante",
        ):
            response = self.client.get(
                reverse(nombre, args=[venta.pk])
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, venta.numero)

        response = self.client.get(
            reverse(
                "ventas:venta_comprobante_pdf",
                args=[venta.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/pdf",
        )
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn(
            "attachment",
            response["Content-Disposition"],
        )

    def test_comprobante_pdf_venta_anulada_sin_ingreso(self):
        venta = self.crear_venta()
        anular_venta(venta=venta, usuario=self.staff)
        Ingreso.objects.filter(venta=venta).delete()

        response = self.client.get(
            reverse(
                "ventas:venta_comprobante_pdf",
                args=[venta.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_anular_venta_desde_vista_staff(self):
        venta = self.crear_venta()
        self.client.logout()
        self.client.login(
            username="staff_test",
            password="Test12345!",
        )

        response = self.client.get(
            reverse("ventas:venta_anular", args=[venta.pk])
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("ventas:venta_anular", args=[venta.pk]),
            {"motivo": "Devolución"},
        )

        self.assertRedirects(
            response,
            reverse("ventas:venta_detalle", args=[venta.pk]),
        )
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.ESTADO_ANULADA)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_anular_venta_ya_anulada_muestra_mensaje(self):
        venta = self.crear_venta()
        anular_venta(venta=venta, usuario=self.staff)
        self.client.logout()
        self.client.login(
            username="staff_test",
            password="Test12345!",
        )

        response = self.client.post(
            reverse("ventas:venta_anular", args=[venta.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ya se encuentra anulada")

    def test_usuario_no_staff_no_puede_anular(self):
        venta = self.crear_venta()

        response = self.client.get(
            reverse("ventas:venta_anular", args=[venta.pk])
        )

        self.assertEqual(response.status_code, 302)

    def test_venta_no_encontrada(self):
        response = self.client.get(
            reverse("ventas:venta_detalle", args=[99999])
        )
        self.assertEqual(response.status_code, 404)

    def test_lista_ventas_paginada(self):
        for indice in range(17):
            Venta.objects.create(
                cliente=self.cliente,
                total=Decimal("10.00"),
            )

        response = self.client.get(
            reverse("ventas:venta_lista"),
            {"page": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)

    def test_venta_anulada_aparece_con_etiqueta(self):
        venta = self.crear_venta()
        anular_venta(venta=venta, usuario=self.staff)

        response = self.client.get(
            reverse("ventas:venta_lista"),
            {"estado": Venta.ESTADO_ANULADA},
        )

        self.assertContains(response, "Anulada")


class VentaSecurityTests(BaseVentaTestCase):
    def test_vistas_requieren_autenticacion(self):
        for nombre in (
            "ventas:cliente_lista",
            "ventas:cliente_crear",
            "ventas:venta_lista",
            "ventas:venta_crear",
        ):
            with self.subTest(nombre=nombre):
                response = self.client.get(reverse(nombre))
                self.assertEqual(response.status_code, 302)
                self.assertIn("/admin/login/", response.url)

    def test_rango_de_fechas_invertido(self):
        from .utils import rango_fechas

        with self.assertRaises(ValueError):
            rango_fechas("2026-12-31", "2026-01-01")

    def test_fecha_futura_no_incluye_venta(self):
        self.client.login(
            username="ventas_test",
            password="Test12345!",
        )
        self.crear_venta()
        manana = timezone.localdate() + timedelta(days=1)

        response = self.client.get(
            reverse("ventas:venta_lista"),
            {"desde": manana.isoformat()},
        )

        self.assertNotContains(response, "VEN-")
