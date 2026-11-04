from io import BytesIO
from decimal import Decimal
import re

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from inventario.models import Categoria, MedidaProducto, Producto, validar_imagen_producto
from ventas.models import Cliente
from ventas.models import PedidoCliente, Venta, Ingreso
from ventas.services import crear_pedido, confirmar_pedido, cambiar_estado_pedido


class CatalogoPublicoTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Dormitorio")
        self.producto = Producto.objects.create(codigo="CAM-1", nombre="Cama Roble", categoria=self.categoria, precio=Decimal("1200"), stock=2, descripcion="Madera maciza")
        MedidaProducto.objects.create(producto=self.producto, alto_cm=100, ancho_cm=160, profundidad_cm=200)
        Producto.objects.create(codigo="INAC-1", nombre="No mostrar", categoria=self.categoria, precio=200, activo=False)
        Producto.objects.create(codigo="AGOT-1", nombre="Mesa agotada", categoria=self.categoria, precio=500, stock=0)

    def test_catalogo_publico_muestra_activos_y_oculta_inactivos(self):
        response = self.client.get(reverse("catalogo:lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cama Roble")
        self.assertContains(response, "Mesa agotada")
        self.assertContains(response, "Agotado")
        self.assertNotContains(response, "No mostrar")

    def test_busqueda_filtro_y_paginacion(self):
        self.assertContains(self.client.get(reverse("catalogo:lista"), {"q": "Roble"}), "Cama Roble")
        self.assertNotContains(self.client.get(reverse("catalogo:lista"), {"disponibilidad": "disponible"}), "Mesa agotada")
        self.assertContains(self.client.get(reverse("catalogo:lista"), {"categoria": self.categoria.pk}), "Cama Roble")
        for n in range(13):
            Producto.objects.create(codigo=f"P-{n}", nombre=f"Producto {n}", categoria=self.categoria, precio=50)
        response = self.client.get(reverse("catalogo:lista"))
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 2)

    def test_categoria_disponibilidad_stock_bajo_combinados_y_busqueda(self):
        oficina = Categoria.objects.create(nombre="Oficina")
        escritorio = Producto.objects.create(codigo="ESC-1", nombre="Escritorio roble", categoria=oficina,
                                             precio=700, stock=1, stock_minimo=2)
        Producto.objects.create(codigo="CAM-2", nombre="Cama de pino", categoria=self.categoria,
                                precio=900, stock=1, stock_minimo=3)
        dormitorio = self.client.get(reverse("catalogo:lista"), {"categoria": self.categoria.pk})
        self.assertContains(dormitorio, "Cama Roble")
        self.assertNotContains(dormitorio, "Escritorio roble")
        oficina_response = self.client.get(reverse("catalogo:lista"), {"categoria": oficina.pk})
        self.assertContains(oficina_response, "Escritorio roble")
        self.assertNotContains(oficina_response, "Cama Roble")
        low = self.client.get(reverse("catalogo:lista"), {"disponibilidad": "bajo"})
        self.assertContains(low, "Escritorio roble")
        self.assertContains(low, "Cama de pino")
        self.assertNotContains(low, "Cama Roble")
        combo = self.client.get(reverse("catalogo:lista"), {"categoria": oficina.pk,
                                     "disponibilidad": "disponible", "q": "roble"})
        self.assertContains(combo, "Escritorio roble")
        self.assertNotContains(combo, "Cama de pino")
        self.assertContains(combo, 'name="disponibilidad"')

    def test_paginacion_conserva_todos_los_filtros(self):
        for n in range(13):
            Producto.objects.create(codigo=f"PG-{n}", nombre=f"Mueble paginado {n}", categoria=self.categoria,
                                    precio=10, stock=1)
        response = self.client.get(reverse("catalogo:lista"), {"categoria": self.categoria.pk,
                                      "disponibilidad": "disponible", "q": "Mueble", "page": 2})
        self.assertContains(response, f"categoria={self.categoria.pk}")
        self.assertContains(response, "disponibilidad=disponible")
        self.assertContains(response, "q=Mueble")

    def test_detalle_incluye_medidas_y_no_expone_costos(self):
        response = self.client.get(reverse("catalogo:detalle", args=[self.producto.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "160,00 cm")
        self.assertNotContains(response, "costo_referencia")
        self.producto.activo = False
        self.producto.save()
        self.assertEqual(self.client.get(reverse("catalogo:detalle", args=[self.producto.pk])).status_code, 404)

    @override_settings(MEDIA_ROOT="/tmp/muebleria-catalogo-test")
    def test_producto_admite_fotografia(self):
        buffer = BytesIO()
        Image.new("RGB", (10, 10), "brown").save(buffer, format="JPEG")
        image = SimpleUploadedFile("cama.jpg", buffer.getvalue(), content_type="image/jpeg")
        self.producto.imagen = image
        self.producto.save()
        self.assertEqual(self.client.get(reverse("catalogo:detalle", args=[self.producto.pk])).status_code, 200)


class ValidacionImagenTests(TestCase):
    def test_rechaza_extension_tamano_y_archivo_que_no_es_imagen(self):
        with self.assertRaises(ValidationError):
            validar_imagen_producto(SimpleUploadedFile("foto.gif", b"x"))
        with self.assertRaises(Exception):
            validar_imagen_producto(SimpleUploadedFile("foto.jpg", b"x" * (5 * 1024 * 1024 + 1)))
        with self.assertRaises(Exception):
            validar_imagen_producto(SimpleUploadedFile("foto.jpg", b"esto no es una imagen"))


class CuentaClienteTests(TestCase):
    def payload(self, **kwargs):
        return {"nombre": "Ana", "apellidos": "Rojas", "email": "ana@example.com", "password1": "UnicaClave!2026", "password2": "UnicaClave!2026", **kwargs}

    def test_registro_valida_correo_y_contrasena_y_crea_cliente_vinculado(self):
        url = reverse("ventas:cliente_registro")
        self.assertEqual(self.client.post(url, self.payload(password1="123", password2="x")).status_code, 200)
        self.assertEqual(get_user_model().objects.count(), 0)
        response = self.client.post(url, self.payload())
        self.assertRedirects(response, reverse("ventas:cliente_login"))
        user = get_user_model().objects.get(email="ana@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("UnicaClave!2026"))
        self.assertEqual(Cliente.objects.get(usuario=user).nombre, "Ana Rojas")
        self.assertEqual(self.client.post(url, self.payload()).status_code, 200)

    def test_login_redirige_al_catalogo_y_saludo_no_muestra_mi_cuenta(self):
        self.client.post(reverse("ventas:cliente_registro"), self.payload())
        response = self.client.post(reverse("ventas:cliente_login"), {"email": "ana@example.com", "password": "UnicaClave!2026"})
        self.assertRedirects(response, reverse("catalogo:lista"))
        catalog = self.client.get(reverse("catalogo:lista"))
        self.assertContains(catalog, "Hola, Ana")
        self.assertNotContains(catalog, "Mi cuenta")
        self.assertContains(catalog, "Salir")
        self.assertEqual(self.client.get(reverse("ventas:cliente_logout")).status_code, 405)
        self.assertEqual(self.client.post(reverse("ventas:cliente_logout")).status_code, 302)

    def test_login_invalido_y_redireccion_externa_se_descarta(self):
        self.assertEqual(self.client.post(reverse("ventas:cliente_login"), {"email": "nadie@example.com", "password": "incorrecta"}).status_code, 200)
        self.client.post(reverse("ventas:cliente_registro"), self.payload())
        response = self.client.post(reverse("ventas:cliente_login"), {"email": "ana@example.com", "password": "UnicaClave!2026", "next": "https://malicioso.example/"})
        self.assertRedirects(response, reverse("catalogo:lista"))

    def test_cliente_no_puede_entrar_a_vistas_administrativas(self):
        self.client.post(reverse("ventas:cliente_registro"), self.payload())
        self.client.post(reverse("ventas:cliente_login"), {"email": "ana@example.com", "password": "UnicaClave!2026"})
        for name in ("inventario:producto_lista", "compras:compra_lista", "ventas:venta_lista", "reportes:ventas"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)


class CarritoYPedidosTests(CatalogoPublicoTests):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(username="comprador", email="comprador@example.com",
                                                        password="UnaClaveSegura!26", first_name="Ana")
        self.cliente = Cliente.objects.create(usuario=self.user, nombre="Ana Compradora", email=self.user.email)
        self.admin = get_user_model().objects.create_user(username="gestor", password="AdminSegura!26", is_staff=True)

    def test_visitante_selecciona_y_preserva_carrito_hasta_acceso(self):
        response = self.client.post(reverse("catalogo:carrito_agregar", args=[self.producto.pk]), {"cantidad": 1})
        self.assertRedirects(response, "/clientes/login/?next=%2Fcarrito%2F")
        self.assertEqual(self.client.session["carrito"][str(self.producto.pk)], 1)
        self.assertEqual(self.client.get(reverse("catalogo:confirmar_carrito")).status_code, 302)

    def test_carrito_rechaza_cantidades_y_permuta_actualiza_quita_y_vacia(self):
        add = self.client.post(reverse("catalogo:carrito_agregar", args=[self.producto.pk]), {"cantidad": 0})
        self.assertEqual(add.status_code, 302)
        self.assertNotIn("carrito", self.client.session)
        self.client.force_login(self.user)
        self.client.post(reverse("catalogo:carrito_agregar", args=[self.producto.pk]), {"cantidad": 2})
        bad = self.client.post(reverse("catalogo:carrito_actualizar", args=[self.producto.pk]), {"cantidad": 3})
        self.assertEqual(bad.status_code, 302)
        self.assertEqual(self.client.session["carrito"][str(self.producto.pk)], 2)
        self.client.post(reverse("catalogo:carrito_actualizar", args=[self.producto.pk]), {"cantidad": 0})
        self.assertNotIn(str(self.producto.pk), self.client.session["carrito"])
        self.client.post(reverse("catalogo:carrito_agregar", args=[self.producto.pk]), {"cantidad": 1})
        self.client.post(reverse("catalogo:carrito_vaciar"))
        self.assertEqual(self.client.session["carrito"], {})

    def test_confirmar_carrito_crea_pedido_pendiente_sin_venta_ni_cambio_de_stock(self):
        self.client.force_login(self.user)
        self.client.post(reverse("catalogo:carrito_agregar", args=[self.producto.pk]), {"cantidad": 2})
        response = self.client.post(reverse("catalogo:confirmar_carrito"), {"telefono": "77712345", "direccion": "Calle 1"})
        pedido = PedidoCliente.objects.get()
        self.assertRedirects(response, reverse("catalogo:pedido_exito", args=[pedido.pk]))
        self.assertEqual(pedido.estado, PedidoCliente.PENDIENTE)
        self.assertIsNone(pedido.venta)
        self.assertEqual(pedido.cliente, self.cliente)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 2)
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(Ingreso.objects.count(), 0)
        self.assertContains(self.client.get(reverse("catalogo:pedido_exito", args=[pedido.pk])), pedido.numero)
        other = get_user_model().objects.create_user(username="otro", password="OtraClaveSegura!26")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("catalogo:pedido_exito", args=[pedido.pk])).status_code, 404)

    def test_confirmar_pedido_admin_registra_una_venta_y_descuenta_stock_solo_una_vez(self):
        pedido = crear_pedido(self.cliente, [{"producto": self.producto.pk, "cantidad": 1}])
        self.assertEqual(self.producto.stock, 2)
        venta = confirmar_pedido(pedido, self.admin)
        self.assertEqual(venta.estado, Venta.ESTADO_COMPLETADA)
        self.assertEqual(venta.total, self.producto.precio)
        pedido.refresh_from_db()
        self.assertEqual(pedido.venta, venta)
        self.assertEqual(pedido.estado, PedidoCliente.CONFIRMADO)
        self.assertEqual(confirmar_pedido(pedido, self.admin), venta)
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(Ingreso.objects.count(), 1)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 1)

    def test_stock_insuficiente_en_confirmacion_no_crea_venta_y_cancelacion_no_toca_stock(self):
        pedido = crear_pedido(self.cliente, [{"producto": self.producto.pk, "cantidad": 2}])
        Producto.objects.filter(pk=self.producto.pk).update(stock=1)
        with self.assertRaises(Exception):
            confirmar_pedido(pedido, self.admin)
        self.assertEqual(Venta.objects.count(), 0)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 1)
        cambiar_estado_pedido(pedido, PedidoCliente.CANCELADO, self.admin)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 1)

    def test_pedidos_admin_staff_only_y_cambios_csrf_post(self):
        pedido = crear_pedido(self.cliente, [{"producto": self.producto.pk, "cantidad": 1}])
        self.assertEqual(self.client.get(reverse("ventas:pedido_lista")).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("ventas:pedido_lista")).status_code, 302)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("ventas:pedido_lista")), pedido.numero)
        self.assertEqual(self.client.get(reverse("ventas:pedido_cambiar_estado", args=[pedido.pk])).status_code, 302)
        response = self.client.post(reverse("ventas:pedido_cambiar_estado", args=[pedido.pk]), {"estado": "ENTREGADO"})
        self.assertEqual(response.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, PedidoCliente.PENDIENTE)

    def test_todas_las_mutaciones_del_carrito_y_pedidos_exigen_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        routes = [
            (reverse("catalogo:carrito_agregar", args=[self.producto.pk]), {"cantidad": 1}),
            (reverse("catalogo:carrito_actualizar", args=[self.producto.pk]), {"cantidad": 1}),
            (reverse("catalogo:carrito_vaciar"), {}),
        ]
        for url, data in routes:
            with self.subTest(url=url):
                self.assertEqual(csrf_client.post(url, data).status_code, 403)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(reverse("catalogo:confirmar_carrito"), {}).status_code, 403)
        csrf_client.force_login(self.admin)
        pedido = crear_pedido(self.cliente, [{"producto": self.producto.pk, "cantidad": 1}])
        self.assertEqual(csrf_client.post(reverse("ventas:pedido_cambiar_estado", args=[pedido.pk]),
                                          {"estado": "CONFIRMADO"}).status_code, 403)


class FlujosCsrfClienteTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def token(self, response):
        match = re.search(rb'name="csrfmiddlewaretoken" value="([^"]+)"', response.content)
        self.assertIsNotNone(match, "La plantilla debe renderizar un token CSRF en sus formularios POST.")
        return match.group(1).decode()

    def datos_registro(self, token):
        return {"csrfmiddlewaretoken": token, "nombre": "Ana", "apellidos": "Rojas", "email": "ana.csrf@example.com", "password1": "UnicaClave!2026", "password2": "UnicaClave!2026"}

    def test_recorrido_completo_con_csrf_y_token_rotado(self):
        catalog = self.client.get(reverse("catalogo:lista"))
        self.assertEqual(catalog.status_code, 200)
        login_page = self.client.get(reverse("ventas:cliente_login"))
        self.assertEqual(login_page.status_code, 200)
        self.assertIn("csrftoken", self.client.cookies)

        register_page = self.client.get(reverse("ventas:cliente_registro"))
        registration_token = self.token(register_page)
        response = self.client.post(reverse("ventas:cliente_registro"), self.datos_registro(registration_token))
        self.assertRedirects(response, reverse("ventas:cliente_login"))
        self.assertTrue(get_user_model().objects.filter(email="ana.csrf@example.com", is_staff=False, is_superuser=False).exists())
        self.assertEqual(self.client.get(reverse("catalogo:lista")).status_code, 200)

        login_page = self.client.get(reverse("ventas:cliente_login"))
        login_token = self.token(login_page)
        csrf_cookie_before_login = self.client.cookies["csrftoken"].value
        response = self.client.post(reverse("ventas:cliente_login"), {"csrfmiddlewaretoken": login_token, "email": "ana.csrf@example.com", "password": "UnicaClave!2026"})
        self.assertRedirects(response, reverse("catalogo:lista"))
        csrf_cookie_after_login = self.client.cookies["csrftoken"].value
        self.assertNotEqual(csrf_cookie_before_login, csrf_cookie_after_login)
        stale_tab = self.client.post(reverse("ventas:cliente_login"), {"csrfmiddlewaretoken": login_token, "email": "ana.csrf@example.com", "password": "UnicaClave!2026"})
        self.assertEqual(stale_tab.status_code, 403)
        self.assertEqual(self.client.get(reverse("catalogo:lista")).status_code, 200)
        self.assertContains(self.client.get(reverse("catalogo:lista")), "Hola, Ana")

        catalog = self.client.get(reverse("catalogo:lista"))
        logout_token = self.token(catalog)
        self.assertEqual(self.client.post(reverse("ventas:cliente_logout"), {"csrfmiddlewaretoken": logout_token}).status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

        login_page = self.client.get(reverse("ventas:cliente_login"))
        response = self.client.post(reverse("ventas:cliente_login"), {"csrfmiddlewaretoken": self.token(login_page), "email": "ana.csrf@example.com", "password": "UnicaClave!2026"})
        self.assertRedirects(response, reverse("catalogo:lista"))

    def test_token_incorrecto_da_403_sin_desactivar_csrf(self):
        self.client.get(reverse("ventas:cliente_login"))
        response = self.client.post(reverse("ventas:cliente_login"), {"csrfmiddlewaretoken": "a" * 64, "email": "x@example.com", "password": "incorrecta"})
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Este formulario venció", status_code=403)

    def test_session_csrf_permite_origenes_locales_configurados_en_puertos_diferentes(self):
        with override_settings(CSRF_TRUSTED_ORIGINS=["http://localhost:8000", "http://localhost:8001"]):
            page = self.client.get(reverse("ventas:cliente_login"), HTTP_HOST="localhost:8000")
            token = self.token(page)
            response = self.client.post(
                reverse("ventas:cliente_login"),
                {"csrfmiddlewaretoken": token, "email": "ausente@example.com", "password": "incorrecta"},
                HTTP_HOST="localhost:8001",
                HTTP_ORIGIN="http://localhost:8000",
            )
            self.assertEqual(response.status_code, 200)
