from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import (
    Count,
    DecimalField,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from inventario.models import Producto

from .comprobante import generar_comprobante_pdf
from .forms import (
    ClienteForm,
    DetalleVentaFormSet,
    VentaForm,
)
from .models import Cliente, Ingreso, Venta
from .services import anular_venta, registrar_venta
from .utils import rango_fechas


TOTAL_CERO = Value(
    Decimal("0.00"),
    output_field=DecimalField(max_digits=14, decimal_places=2),
)


def _paginar(request, queryset, por_pagina=15):
    paginator = Paginator(queryset, por_pagina)
    return paginator.get_page(request.GET.get("page"))


@login_required
def cliente_lista(request):
    busqueda = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "activos")

    clientes = (
        Cliente.objects
        .annotate(
            ventas_realizadas=Count(
                "ventas",
                filter=Q(
                    ventas__estado=Venta.ESTADO_COMPLETADA,
                ),
            ),
            monto_comprado=Coalesce(
                Sum(
                    "ventas__total",
                    filter=Q(
                        ventas__estado=Venta.ESTADO_COMPLETADA,
                    ),
                ),
                TOTAL_CERO,
            ),
        )
        .order_by("nombre")
    )

    if busqueda:
        clientes = clientes.filter(
            Q(nombre__icontains=busqueda)
            | Q(nit__icontains=busqueda)
            | Q(telefono__icontains=busqueda)
            | Q(email__icontains=busqueda)
        )

    if estado == "activos":
        clientes = clientes.filter(activo=True)
    elif estado == "inactivos":
        clientes = clientes.filter(activo=False)

    return render(
        request,
        "ventas/cliente_lista.html",
        {
            "page_obj": _paginar(request, clientes),
            "busqueda": busqueda,
            "estado": estado,
        },
    )


@login_required
def cliente_crear(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)

        if form.is_valid():
            cliente = form.save()

            messages.success(
                request,
                f"Cliente {cliente.nombre} registrado correctamente.",
            )

            return redirect("ventas:cliente_lista")
    else:
        form = ClienteForm()

    return render(
        request,
        "ventas/cliente_form.html",
        {
            "form": form,
            "titulo": "Registrar cliente",
            "subtitulo": "Agrega los datos de contacto del cliente.",
        },
    )


@login_required
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == "POST":
        form = ClienteForm(
            request.POST,
            instance=cliente,
        )

        if form.is_valid():
            cliente = form.save()

            messages.success(
                request,
                f"Cliente {cliente.nombre} actualizado correctamente.",
            )

            return redirect("ventas:cliente_lista")
    else:
        form = ClienteForm(instance=cliente)

    return render(
        request,
        "ventas/cliente_form.html",
        {
            "form": form,
            "cliente": cliente,
            "titulo": "Editar cliente",
            "subtitulo": "Actualiza la información del cliente.",
        },
    )


@login_required
def cliente_eliminar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == "POST":
        if cliente.activo:
            cliente.activo = False
            cliente.save(update_fields=["activo", "actualizado_en"])

            messages.success(
                request,
                f"Cliente {cliente.nombre} desactivado correctamente. "
                "Sus ventas se conservan en el historial.",
            )
        else:
            messages.info(
                request,
                "El cliente ya se encontraba desactivado.",
            )

        return redirect("ventas:cliente_lista")

    return render(
        request,
        "ventas/cliente_confirmar_eliminar.html",
        {"cliente": cliente},
    )


@login_required
def cliente_detalle(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    ventas = (
        cliente.ventas
        .select_related("creado_por", "ingreso")
        .prefetch_related("detalles__producto")
        .order_by("-fecha")
    )

    resumen = ventas.filter(
        estado=Venta.ESTADO_COMPLETADA,
    ).aggregate(
        cantidad=Count("pk"),
        total=Coalesce(Sum("total"), TOTAL_CERO),
    )

    return render(
        request,
        "ventas/cliente_detalle.html",
        {
            "cliente": cliente,
            "ventas": ventas[:10],
            "resumen": resumen,
        },
    )


@login_required
def venta_lista(request):
    busqueda = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    desde = request.GET.get("desde", "").strip()
    hasta = request.GET.get("hasta", "").strip()
    error_fechas = ""

    ventas = (
        Venta.objects
        .select_related("cliente", "creado_por", "ingreso")
        .prefetch_related("detalles")
        .all()
    )

    if busqueda:
        ventas = ventas.filter(
            Q(numero__icontains=busqueda)
            | Q(cliente__nombre__icontains=busqueda)
            | Q(cliente__nit__icontains=busqueda)
        )

    if estado in dict(Venta.ESTADOS):
        ventas = ventas.filter(estado=estado)

    try:
        inicio, fin = rango_fechas(desde, hasta)
    except ValueError as error:
        inicio = fin = None
        error_fechas = str(error)

    if inicio:
        ventas = ventas.filter(fecha__gte=inicio)

    if fin:
        ventas = ventas.filter(fecha__lt=fin)

    resumen = ventas.filter(
        estado=Venta.ESTADO_COMPLETADA,
    ).aggregate(
        cantidad=Count("pk"),
        total=Coalesce(Sum("total"), TOTAL_CERO),
    )

    return render(
        request,
        "ventas/venta_lista.html",
        {
            "page_obj": _paginar(request, ventas),
            "busqueda": busqueda,
            "estado": estado,
            "desde": desde,
            "hasta": hasta,
            "error_fechas": error_fechas,
            "resumen": resumen,
        },
    )


@login_required
def venta_crear(request):
    if request.method == "POST":
        form = VentaForm(request.POST)
        formset = DetalleVentaFormSet(
            request.POST,
            prefix="detalle",
        )

        if form.is_valid() and formset.is_valid():
            detalles = []

            for detalle_form in formset:
                datos = getattr(
                    detalle_form,
                    "cleaned_data",
                    None,
                )

                if not datos or datos.get("DELETE"):
                    continue

                producto = datos.get("producto")
                cantidad = datos.get("cantidad")

                if producto and cantidad:
                    detalles.append(
                        {
                            "producto": producto,
                            "cantidad": cantidad,
                        }
                    )

            if not detalles:
                form.add_error(
                    None,
                    "Debe agregar al menos un producto a la venta.",
                )
            else:
                try:
                    venta = registrar_venta(
                        cliente=form.cleaned_data["cliente"],
                        items=detalles,
                        usuario=request.user,
                        observaciones=(
                            form.cleaned_data["observaciones"]
                        ),
                        metodo_pago=(
                            form.cleaned_data["metodo_pago"]
                        ),
                        referencia_pago=(
                            form.cleaned_data["referencia_pago"]
                        ),
                    )

                    messages.success(
                        request,
                        f"Venta {venta.numero} registrada por "
                        f"Bs {venta.total:.2f}.",
                    )

                    return redirect(
                        "ventas:venta_detalle",
                        pk=venta.pk,
                    )

                except ValidationError as error:
                    form.add_error(None, error)
    else:
        form = VentaForm()
        formset = DetalleVentaFormSet(prefix="detalle")

    productos_datos = {
        str(producto.pk): {
            "precio": str(producto.precio),
            "stock": producto.stock,
        }
        for producto in Producto.objects.filter(activo=True)
    }

    return render(
        request,
        "ventas/venta_form.html",
        {
            "form": form,
            "formset": formset,
            "productos_datos": productos_datos,
        },
    )


def _obtener_venta(pk):
    return get_object_or_404(
        Venta.objects
        .select_related("cliente", "creado_por", "ingreso")
        .prefetch_related("detalles__producto"),
        pk=pk,
    )


@login_required
def venta_detalle(request, pk):
    return render(
        request,
        "ventas/venta_detalle.html",
        {"venta": _obtener_venta(pk)},
    )


@login_required
def venta_comprobante(request, pk):
    return render(
        request,
        "ventas/venta_comprobante.html",
        {"venta": _obtener_venta(pk)},
    )


@login_required
def venta_comprobante_pdf(request, pk):
    venta = _obtener_venta(pk)
    contenido = generar_comprobante_pdf(venta)

    response = HttpResponse(
        contenido,
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{venta.numero or venta.pk}.pdf"'
    )

    return response


@staff_member_required
def venta_anular(request, pk):
    venta = _obtener_venta(pk)

    if request.method == "POST":
        try:
            anular_venta(
                venta=venta,
                usuario=request.user,
                motivo=request.POST.get(
                    "motivo",
                    "",
                ).strip(),
            )

            messages.success(
                request,
                f"Venta {venta.numero} anulada. "
                "El stock fue devuelto al inventario.",
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])

        return redirect(
            "ventas:venta_detalle",
            pk=venta.pk,
        )

    return render(
        request,
        "ventas/venta_confirmar_anular.html",
        {"venta": venta},
    )
