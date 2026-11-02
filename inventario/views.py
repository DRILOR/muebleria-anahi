from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MedidaProductoForm, ProductoForm
from .models import Producto


@login_required
def producto_lista(request):
    productos = Producto.objects.select_related(
        "categoria"
    ).all()

    busqueda = request.GET.get("q", "").strip()

    if busqueda:
        productos = productos.filter(
            Q(codigo__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
            | Q(categoria__nombre__icontains=busqueda)
        )

    contexto = {
        "productos": productos,
        "busqueda": busqueda,
    }

    return render(
        request,
        "inventario/producto_lista.html",
        contexto,
    )


@login_required
def producto_crear(request):
    if request.method == "POST":
        producto_form = ProductoForm(request.POST)
        medida_form = MedidaProductoForm(request.POST)

        if producto_form.is_valid() and medida_form.is_valid():
            producto = producto_form.save()

            medida = medida_form.save(commit=False)
            medida.producto = producto
            medida.save()

            messages.success(
                request,
                "Producto registrado correctamente.",
            )

            return redirect("inventario:producto_lista")

    else:
        producto_form = ProductoForm()
        medida_form = MedidaProductoForm()

    return render(
        request,
        "inventario/producto_form.html",
        {
            "producto_form": producto_form,
            "medida_form": medida_form,
            "titulo": "Registrar producto",
        },
    )


@login_required
def producto_editar(request, pk):
    producto = get_object_or_404(
        Producto,
        pk=pk,
    )

    medida = getattr(
        producto,
        "medidas",
        None,
    )

    if request.method == "POST":
        producto_form = ProductoForm(
            request.POST,
            instance=producto,
        )

        medida_form = MedidaProductoForm(
            request.POST,
            instance=medida,
        )

        if producto_form.is_valid() and medida_form.is_valid():
            producto = producto_form.save()

            nueva_medida = medida_form.save(commit=False)
            nueva_medida.producto = producto
            nueva_medida.save()

            messages.success(
                request,
                "Producto actualizado correctamente.",
            )

            return redirect("inventario:producto_lista")

    else:
        producto_form = ProductoForm(
            instance=producto,
        )

        medida_form = MedidaProductoForm(
            instance=medida,
        )

    return render(
        request,
        "inventario/producto_form.html",
        {
            "producto_form": producto_form,
            "medida_form": medida_form,
            "titulo": "Editar producto",
            "producto": producto,
        },
    )


@login_required
def producto_eliminar(request, pk):
    producto = get_object_or_404(
        Producto,
        pk=pk,
    )

    if request.method == "POST":
        producto.activo = False
        producto.save(
            update_fields=["activo"]
        )

        messages.success(
            request,
            "Producto desactivado correctamente.",
        )

        return redirect("inventario:producto_lista")

    return render(
        request,
        "inventario/producto_confirmar_eliminar.html",
        {
            "producto": producto,
        },
    )