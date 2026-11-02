from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from inventario.models import Material


class Proveedor(models.Model):
    nombre = models.CharField(
        max_length=150,
    )

    nit = models.CharField(
        max_length=30,
        blank=True,
    )

    telefono = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    direccion = models.CharField(
        max_length=250,
        blank=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    creado_en = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Compra(models.Model):
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="compras",
    )

    numero_documento = models.CharField(
        max_length=50,
        blank=True,
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    observaciones = models.TextField(
        blank=True,
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )

    fecha = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Compra #{self.pk} - {self.proveedor}"


class DetalleCompra(models.Model):
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name="detalles",
    )

    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
    )

    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(0.01)
        ],
    )

    costo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ],
    )

    @property
    def subtotal(self):
        return (
            self.cantidad
            * self.costo_unitario
        )

    def __str__(self):
        return (
            f"{self.material} x "
            f"{self.cantidad}"
        )