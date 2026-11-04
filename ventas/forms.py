from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.forms import formset_factory
from django.forms.formsets import BaseFormSet

from inventario.models import Producto

from .models import Cliente, Ingreso


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nombre",
            "nit",
            "telefono",
            "email",
            "direccion",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. María Fernanda López",
                    "autocomplete": "name",
                }
            ),
            "nit": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. 12345678",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. 70000000",
                    "autocomplete": "tel",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "cliente@correo.com",
                    "autocomplete": "email",
                }
            ),
            "direccion": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Barrio, calle y número",
                    "autocomplete": "street-address",
                }
            ),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()

        if len(nombre) < 3:
            raise forms.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )

        return nombre

    def clean_nit(self):
        return self.cleaned_data.get("nit", "").strip().upper()

    def clean_telefono(self):
        return self.cleaned_data.get("telefono", "").strip()


class VentaForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(activo=True),
        label="Cliente",
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
    )
    metodo_pago = forms.ChoiceField(
        choices=Ingreso.METODOS_PAGO,
        label="Método de pago",
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
    )
    referencia_pago = forms.CharField(
        required=False,
        max_length=100,
        label="Referencia del pago",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Nro. de transferencia, voucher, etc.",
            }
        ),
    )
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Detalles adicionales de la venta",
            }
        ),
    )

    def clean_referencia_pago(self):
        return self.cleaned_data.get(
            "referencia_pago",
            "",
        ).strip()


class DetalleVentaForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(
            activo=True,
            stock__gt=0,
        ).order_by("nombre"),
        label="Producto",
        widget=forms.Select(
            attrs={"class": "form-control producto-select"}
        ),
    )
    cantidad = forms.IntegerField(
        min_value=1,
        max_value=100000,
        label="Cantidad",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control cantidad-input",
                "min": "1",
                "step": "1",
            }
        ),
    )


class DetalleVentaBaseFormSet(BaseFormSet):
    default_error_messages = {
        **BaseFormSet.default_error_messages,
        "too_few_forms": (
            "Debe agregar al menos un producto a la venta."
        ),
        "too_many_forms": (
            "La venta contiene demasiados productos."
        ),
    }


DetalleVentaFormSet = formset_factory(
    DetalleVentaForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
    formset=DetalleVentaBaseFormSet,
)


class RegistroClienteForm(forms.Form):
    nombre = forms.CharField(max_length=150, label="Nombre", widget=forms.TextInput(attrs={"autocomplete": "given-name"}))
    apellidos = forms.CharField(max_length=150, label="Apellidos", widget=forms.TextInput(attrs={"autocomplete": "family-name"}))
    email = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if len(email) > 150:
            raise forms.ValidationError("El correo no puede superar 150 caracteres.")
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("Este correo ya está asociado a una cuenta.")
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password1")
        if password:
            try:
                password_validation.validate_password(password)
            except ValidationError as error:
                self.add_error("password1", error)
        if cleaned.get("password1") and cleaned.get("password2") and cleaned["password1"] != cleaned["password2"]:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned


class AccesoClienteForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(attrs={"autocomplete": "username", "autofocus": True}))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
