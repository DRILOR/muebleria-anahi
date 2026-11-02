from django import forms

from .models import Categoria, MedidaProducto, Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "codigo",
            "nombre",
            "descripcion",
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