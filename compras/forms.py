from django import forms
from django.forms import formset_factory

from inventario.models import Material

from .models import Proveedor


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "nombre",
            "nit",
            "telefono",
            "email",
            "direccion",
            "activo",
        ]


class CompraForm(forms.Form):
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.filter(
            activo=True
        )
    )

    numero_documento = forms.CharField(
        max_length=50,
        required=False,
    )

    observaciones = forms.CharField(
        widget=forms.Textarea(
            attrs={"rows": 3}
        ),
        required=False,
    )


class DetalleCompraForm(forms.Form):
    material = forms.ModelChoiceField(
        queryset=Material.objects.filter(
            activo=True
        )
    )

    cantidad = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
    )

    costo_unitario = forms.DecimalField(
        min_value=0,
        max_digits=12,
        decimal_places=2,
    )


DetalleCompraFormSet = formset_factory(
    DetalleCompraForm,
    extra=5,
    min_num=1,
    validate_min=True,
)