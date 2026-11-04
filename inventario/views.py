from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MedidaProductoForm, ProductoForm
from .models import Producto
from django.core.exceptions import ValidationError

from .forms import MaterialForm, MovimientoMaterialForm
from .models import Material, MovimientoInventario
from .services import registrar_movimiento

@staff_member_required
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


@staff_member_required
def producto_crear(request):
    if request.method == "POST":
        producto_form = ProductoForm(request.POST, request.FILES)
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


@staff_member_required
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
            request.FILES,
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


@staff_member_required
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
@staff_member_required
def material_lista(request):
    materiales = Material.objects.all()

    q = request.GET.get("q", "").strip()

    if q:
        materiales = materiales.filter(
            Q(codigo__icontains=q)
            | Q(nombre__icontains=q)
        )

    return render(
        request,
        "inventario/material_lista.html",
        {
            "materiales": materiales,
            "busqueda": q,
        },
    )


@staff_member_required
def material_crear(request):
    if request.method == "POST":
        form = MaterialForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Material registrado correctamente.",
            )

            return redirect(
                "inventario:material_lista"
            )
    else:
        form = MaterialForm()

    return render(
        request,
        "inventario/material_form.html",
        {
            "form": form,
            "titulo": "Registrar material",
        },
    )


@staff_member_required
def material_editar(request, pk):
    material = get_object_or_404(
        Material,
        pk=pk,
    )

    if request.method == "POST":
        form = MaterialForm(
            request.POST,
            instance=material,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Material actualizado correctamente.",
            )

            return redirect(
                "inventario:material_lista"
            )

    else:
        form = MaterialForm(
            instance=material,
        )

    return render(
        request,
        "inventario/material_form.html",
        {
            "form": form,
            "titulo": "Editar material",
        },
    )


@staff_member_required
def movimiento_crear(request):
    if request.method == "POST":
        form = MovimientoMaterialForm(request.POST)

        if form.is_valid():
            try:
                registrar_movimiento(
                    material_id=form.cleaned_data[
                        "material"
                    ].pk,
                    tipo=form.cleaned_data["tipo"],
                    cantidad=form.cleaned_data[
                        "cantidad"
                    ],
                    motivo=form.cleaned_data[
                        "motivo"
                    ],
                    referencia=form.cleaned_data[
                        "referencia"
                    ],
                    usuario=request.user,
                )

                messages.success(
                    request,
                    "Movimiento registrado correctamente.",
                )

                return redirect(
                    "inventario:material_lista"
                )

            except ValidationError as error:
                form.add_error(
                    None,
                    error.message,
                )
    else:
        form = MovimientoMaterialForm()

    return render(
        request,
        "inventario/movimiento_form.html",
        {"form": form},
    )


@staff_member_required
def movimiento_historial(request):
    movimientos = (
        MovimientoInventario.objects
        .select_related(
            "material",
            "creado_por",
        )
        .all()
    )

    return render(
        request,
        "inventario/movimiento_historial.html",
        {
            "movimientos": movimientos,
        },
    )
