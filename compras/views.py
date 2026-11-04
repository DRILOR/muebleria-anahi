from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .forms import (
    CompraForm,
    DetalleCompraFormSet,
    ProveedorForm,
)
from .models import Compra, Proveedor
from .services import registrar_compra


@staff_member_required
def proveedor_lista(request):
    proveedores = Proveedor.objects.all()

    return render(
        request,
        "compras/proveedor_lista.html",
        {"proveedores": proveedores},
    )


@staff_member_required
def proveedor_crear(request):
    if request.method == "POST":
        form = ProveedorForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Proveedor registrado correctamente.",
            )

            return redirect(
                "compras:proveedor_lista"
            )
    else:
        form = ProveedorForm()

    return render(
        request,
        "compras/proveedor_form.html",
        {
            "form": form,
            "titulo": "Registrar proveedor",
        },
    )


@staff_member_required
def proveedor_editar(request, pk):
    proveedor = get_object_or_404(
        Proveedor,
        pk=pk,
    )

    if request.method == "POST":
        form = ProveedorForm(
            request.POST,
            instance=proveedor,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Proveedor actualizado correctamente.",
            )

            return redirect(
                "compras:proveedor_lista"
            )
    else:
        form = ProveedorForm(
            instance=proveedor,
        )

    return render(
        request,
        "compras/proveedor_form.html",
        {
            "form": form,
            "titulo": "Editar proveedor",
        },
    )


@staff_member_required
def compra_lista(request):
    compras = (
        Compra.objects
        .select_related("proveedor")
        .all()
    )

    return render(
        request,
        "compras/compra_lista.html",
        {"compras": compras},
    )


@staff_member_required
def compra_crear(request):
    if request.method == "POST":
        form = CompraForm(request.POST)
        formset = DetalleCompraFormSet(
            request.POST,
        )

        if form.is_valid() and formset.is_valid():
            detalles = []

            for detalle_form in formset:
                if (
                    detalle_form.cleaned_data
                    and detalle_form.cleaned_data.get(
                        "material"
                    )
                ):
                    detalles.append(
                        detalle_form.cleaned_data
                    )

            if detalles:
                compra = registrar_compra(
                    proveedor=form.cleaned_data[
                        "proveedor"
                    ],
                    detalles=detalles,
                    usuario=request.user,
                    numero_documento=(
                        form.cleaned_data[
                            "numero_documento"
                        ]
                    ),
                    observaciones=(
                        form.cleaned_data[
                            "observaciones"
                        ]
                    ),
                )

                messages.success(
                    request,
                    f"Compra #{compra.pk} "
                    "registrada correctamente.",
                )

                return redirect(
                    "compras:compra_lista"
                )

            form.add_error(
                None,
                "Debe registrar al menos un material.",
            )

    else:
        form = CompraForm()
        formset = DetalleCompraFormSet()

    return render(
        request,
        "compras/compra_form.html",
        {
            "form": form,
            "formset": formset,
        },
    )
