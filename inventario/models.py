from django.core.validators import MinValueValidator
from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre",
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    codigo = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Código",
    )
    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre",
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name="Categoría",
    )
    precio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Precio de venta",
    )
    stock = models.PositiveIntegerField(
        default=0,
        verbose_name="Stock actual",
    )
    stock_minimo = models.PositiveIntegerField(
        default=0,
        verbose_name="Stock mínimo",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización",
    )

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def stock_bajo(self):
        return self.stock <= self.stock_minimo


class MedidaProducto(models.Model):
    producto = models.OneToOneField(
        Producto,
        on_delete=models.CASCADE,
        related_name="medidas",
        verbose_name="Producto",
    )
    alto_cm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Alto (cm)",
    )
    ancho_cm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Ancho (cm)",
    )
    profundidad_cm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Profundidad (cm)",
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )

    class Meta:
        verbose_name = "Medida de producto"
        verbose_name_plural = "Medidas de productos"

    def __str__(self):
        return f"Medidas de {self.producto.nombre}"