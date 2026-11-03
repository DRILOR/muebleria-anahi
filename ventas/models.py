from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Cliente(models.Model):
    """Cliente de la mueblería.

    La eliminación es lógica: el registro se conserva para mantener la
    trazabilidad de las ventas y simplemente se marca como inactivo.
    """

    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre completo",
    )
    nit = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="NIT / Documento",
    )
    telefono = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Teléfono",
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Correo electrónico",
    )
    direccion = models.CharField(
        max_length=250,
        blank=True,
        verbose_name="Dirección",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización",
    )

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        indexes = [
            models.Index(fields=["nombre"]),
        ]

    def __str__(self):
        return self.nombre

    @property
    def cantidad_ventas(self):
        return self.ventas.count()

    @property
    def total_comprado(self):
        from django.db.models import Sum

        total = self.ventas.filter(
            estado=Venta.ESTADO_COMPLETADA,
        ).aggregate(total=Sum("total"))["total"]
        return total or Decimal("0.00")


class Venta(models.Model):
    ESTADO_COMPLETADA = "COMPLETADA"
    ESTADO_ANULADA = "ANULADA"

    ESTADOS = [
        (ESTADO_COMPLETADA, "Completada"),
        (ESTADO_ANULADA, "Anulada"),
    ]

    numero = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Número de venta",
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="ventas",
        verbose_name="Cliente",
    )
    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Total",
    )
    estado = models.CharField(
        max_length=12,
        choices=ESTADOS,
        default=ESTADO_COMPLETADA,
        verbose_name="Estado",
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas_registradas",
        verbose_name="Registrada por",
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de venta",
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización",
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["estado", "fecha"]),
        ]

    def __str__(self):
        return f"{self.numero or 'Venta'} - {self.cliente}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.numero or not self.pk:
            return

        numero = f"VEN-{self.pk:06d}"
        type(self).objects.filter(pk=self.pk).update(numero=numero)
        self.numero = numero

    @property
    def esta_anulada(self):
        return self.estado == self.ESTADO_ANULADA


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Venta",
    )
    producto = models.ForeignKey(
        "inventario.Producto",
        on_delete=models.PROTECT,
        related_name="detalles_venta",
        verbose_name="Producto",
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad",
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Precio unitario",
    )
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Subtotal",
    )

    class Meta:
        ordering = ["pk"]
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"


class Ingreso(models.Model):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    TARJETA = "TARJETA"
    QR = "QR"

    METODOS_PAGO = [
        (EFECTIVO, "Efectivo"),
        (TRANSFERENCIA, "Transferencia"),
        (TARJETA, "Tarjeta"),
        (QR, "Código QR"),
    ]

    venta = models.OneToOneField(
        Venta,
        on_delete=models.CASCADE,
        related_name="ingreso",
        verbose_name="Venta",
    )
    monto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Monto",
    )
    metodo_pago = models.CharField(
        max_length=15,
        choices=METODOS_PAGO,
        default=EFECTIVO,
        verbose_name="Método de pago",
    )
    referencia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Referencia del pago",
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ingresos_registrados",
        verbose_name="Registrado por",
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha del ingreso",
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Ingreso"
        verbose_name_plural = "Ingresos"
        indexes = [
            models.Index(fields=["fecha"]),
        ]

    def __str__(self):
        return f"Ingreso {self.venta.numero} - {self.monto}"


class MovimientoProducto(models.Model):
    """Trazabilidad de las entradas y salidas de productos terminados."""

    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"

    TIPOS = [
        (ENTRADA, "Entrada"),
        (SALIDA, "Salida"),
    ]

    producto = models.ForeignKey(
        "inventario.Producto",
        on_delete=models.PROTECT,
        related_name="movimientos_venta",
        verbose_name="Producto",
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPOS,
        verbose_name="Tipo",
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad",
    )
    stock_anterior = models.PositiveIntegerField(
        verbose_name="Stock anterior",
    )
    stock_resultante = models.PositiveIntegerField(
        verbose_name="Stock resultante",
    )
    motivo = models.CharField(
        max_length=200,
        verbose_name="Motivo",
    )
    referencia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Referencia",
    )
    venta = models.ForeignKey(
        Venta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos",
        verbose_name="Venta",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_producto",
        verbose_name="Registrado por",
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha",
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Movimiento de producto"
        verbose_name_plural = "Movimientos de productos"
        indexes = [
            models.Index(fields=["producto", "fecha"]),
        ]

    def __str__(self):
        return f"{self.tipo} - {self.producto} - {self.cantidad}"
