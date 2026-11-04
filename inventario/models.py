import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from PIL import Image, UnidentifiedImageError

from django.core.validators import FileExtensionValidator


def validar_imagen_producto(archivo):
    """Valida tamaño máximo (5 MB) y formato de la fotografía."""
    tamano_maximo = 5 * 1024 * 1024
    if archivo.size > tamano_maximo:
        raise ValidationError(
            f"La imagen supera el límite permitido de 5 MB "
            f"({archivo.size / (1024 * 1024):.1f} MB)."
        )

    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise ValidationError(
            f"Formato no válido ({ext}). Use JPG, JPEG, PNG o WEBP."
        )
    try:
        archivo.seek(0)
        imagen = Image.open(archivo)
        imagen.verify()
        archivo.seek(0)
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationError("El archivo no contiene una imagen válida.")


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
    imagen = models.ImageField(
        upload_to="productos/",
        blank=True,
        validators=[validar_imagen_producto, FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
        verbose_name="Fotografía",
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
class Material(models.Model):
    UNIDAD = "UNIDAD"
    TABLON = "TABLON"
    METRO = "METRO"
    METRO_CUADRADO = "M2"
    KILOGRAMO = "KG"
    LITRO = "LITRO"

    UNIDADES = [
        (UNIDAD, "Unidad"),
        (TABLON, "Tablón"),
        (METRO, "Metro"),
        (METRO_CUADRADO, "Metro cuadrado"),
        (KILOGRAMO, "Kilogramo"),
        (LITRO, "Litro"),
    ]

    codigo = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Código",
    )

    nombre = models.CharField(
        max_length=150,
        verbose_name="Material",
    )

    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDADES,
        default=UNIDAD,
        verbose_name="Unidad de medida",
    )

    stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Stock actual",
    )

    stock_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Stock mínimo",
    )

    costo_referencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Costo de referencia",
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Material"
        verbose_name_plural = "Materiales"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def stock_bajo(self):
        return self.stock <= self.stock_minimo


class MovimientoInventario(models.Model):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"

    TIPOS = [
        (ENTRADA, "Entrada"),
        (SALIDA, "Salida"),
    ]

    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )

    tipo = models.CharField(
        max_length=10,
        choices=TIPOS,
    )

    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )

    stock_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    stock_resultante = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    motivo = models.CharField(
        max_length=200,
    )

    referencia = models.CharField(
        max_length=100,
        blank=True,
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    fecha = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"

    def __str__(self):
        return f"{self.tipo} - {self.material} - {self.cantidad}"
