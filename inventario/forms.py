from django import forms

from .models import (
    Categoria,
    Material,
    MedidaProducto,
    MovimientoInventario,
    Producto,
)
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "codigo",
            "nombre",
            "descripcion",
            "imagen",
            "categoria",
            "precio",
            "stock",
            "stock_minimo",
            "activo",
        ]
        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. CAM-001",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre del producto",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "categoria": forms.Select(
                attrs={"class": "form-control"}
            ),
            "precio": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
            "stock_minimo": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip().upper()
        return codigo

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()

        if len(nombre) < 3:
            raise forms.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )

        return nombre


class MedidaProductoForm(forms.ModelForm):
    class Meta:
        model = MedidaProducto
        fields = [
            "alto_cm",
            "ancho_cm",
            "profundidad_cm",
            "observaciones",
        ]
        widgets = {
            "alto_cm": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "ancho_cm": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "profundidad_cm": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "observaciones": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = [
            "nombre",
            "descripcion",
            "activo",
        ]
class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = [
            "codigo",
            "nombre",
            "unidad_medida",
            "stock_minimo",
            "costo_referencia",
            "activo",
        ]

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()


class MovimientoMaterialForm(forms.Form):
    material = forms.ModelChoiceField(
        queryset=Material.objects.filter(activo=True),
        label="Material",
    )

    tipo = forms.ChoiceField(
        choices=MovimientoInventario.TIPOS,
        label="Tipo de movimiento",
    )

    cantidad = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        max_digits=12,
    )

    motivo = forms.CharField(
        max_length=200,
    )

    referencia = forms.CharField(
        max_length=100,
        required=False,
    )
