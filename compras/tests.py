from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventario.models import (
    Material,
    MovimientoInventario,
)

from .models import (
    Compra,
    DetalleCompra,
    Proveedor,
)
from .services import registrar_compra


class CompraServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="compras_test",
            password="Test12345!",
        )

        self.proveedor = Proveedor.objects.create(
            nombre="Maderas del Sur",
            nit="123456",
        )

        self.material = Material.objects.create(
            codigo="MAD-001",
            nombre="Madera roble",
            unidad_medida=Material.TABLON,
            stock=Decimal("45"),
            stock_minimo=Decimal("10"),
            costo_referencia=Decimal("80"),
        )

    def test_registrar_compra_actualiza_total_y_stock(self):
        compra = registrar_compra(
            proveedor=self.proveedor,
            detalles=[
                {
                    "material": self.material,
                    "cantidad": Decimal("10"),
                    "costo_unitario": Decimal("80"),
                }
            ],
            usuario=self.user,
            numero_documento="FAC-001",
        )

        self.material.refresh_from_db()
        compra.refresh_from_db()

        self.assertEqual(
            compra.total,
            Decimal("800"),
        )

        self.assertEqual(
            self.material.stock,
            Decimal("55"),
        )

        self.assertEqual(
            DetalleCompra.objects.count(),
            1,
        )

        movimiento = (
            MovimientoInventario.objects
            .latest("fecha")
        )

        self.assertEqual(
            movimiento.tipo,
            MovimientoInventario.ENTRADA,
        )

        self.assertEqual(
            movimiento.stock_anterior,
            Decimal("45"),
        )

        self.assertEqual(
            movimiento.stock_resultante,
            Decimal("55"),
        )


class ProveedorViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="proveedor_test",
            password="Test12345!",
        )

        self.client.login(
            username="proveedor_test",
            password="Test12345!",
        )

    def test_crear_proveedor(self):
        response = self.client.post(
            reverse(
                "compras:proveedor_crear"
            ),
            {
                "nombre": "Proveedor Test",
                "nit": "999",
                "telefono": "70000000",
                "email": "test@example.com",
                "direccion": "Yacuiba",
                "activo": "on",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            Proveedor.objects.filter(
                nombre="Proveedor Test"
            ).exists()
        )

    def test_lista_proveedores(self):
        response = self.client.get(
            reverse(
                "compras:proveedor_lista"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )


class CompraViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="venta_test",
            password="Test12345!",
        )

        self.client.login(
            username="venta_test",
            password="Test12345!",
        )

        self.proveedor = Proveedor.objects.create(
            nombre="Maderas del Sur",
        )

        self.material = Material.objects.create(
            codigo="MAD-001",
            nombre="Madera roble",
            unidad_medida=Material.TABLON,
            stock=Decimal("45"),
            stock_minimo=Decimal("10"),
            costo_referencia=Decimal("80"),
        )

    def test_lista_compras(self):
        response = self.client.get(
            reverse(
                "compras:compra_lista"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_registrar_compra_desde_vista(self):
        response = self.client.post(
            reverse(
                "compras:compra_crear"
            ),
            {
                "proveedor": self.proveedor.pk,
                "numero_documento": "FAC-002",
                "observaciones": "Compra automática",

                "form-TOTAL_FORMS": "5",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "1",
                "form-MAX_NUM_FORMS": "1000",

                "form-0-material": self.material.pk,
                "form-0-cantidad": "10",
                "form-0-costo_unitario": "80",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        compra = Compra.objects.get(
            numero_documento="FAC-002"
        )

        self.assertEqual(
            compra.total,
            Decimal("800"),
        )

        self.material.refresh_from_db()

        self.assertEqual(
            self.material.stock,
            Decimal("55"),
        )

    def test_editar_proveedor(self):
        url = reverse("compras:proveedor_editar", args=[self.proveedor.pk])
        get_res = self.client.get(url)
        self.assertEqual(get_res.status_code, 200)

        post_res = self.client.post(
            url,
            {
                "nombre": "Maderas del Sur S.R.L.",
                "nit": "987654",
                "telefono": "71112233",
                "email": "contacto@maderasdelsur.com",
                "direccion": "Av. Principal 123",
                "activo": "on",
            },
        )
        self.assertEqual(post_res.status_code, 302)
        self.proveedor.refresh_from_db()
        self.assertEqual(self.proveedor.nombre, "Maderas del Sur S.R.L.")

    def test_compra_sin_materiales_muestra_error(self):
        response = self.client.post(
            reverse("compras:compra_crear"),
            {
                "proveedor": self.proveedor.pk,
                "numero_documento": "FAC-003",
                "observaciones": "",
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "1",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-material": "",
                "form-0-cantidad": "",
                "form-0-costo_unitario": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este campo es obligatorio")


    def test_str_proveedor_y_compra(self):
        self.assertEqual(str(self.proveedor), self.proveedor.nombre)
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            numero_documento="FAC-999",
            creado_por=self.user,
        )
        self.assertIn(str(compra.pk), str(compra))
