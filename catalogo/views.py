from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from inventario.models import Categoria, Producto
from ventas.models import Cliente, PedidoCliente
from ventas.services import crear_pedido


def _cantidad_carrito(request):
    return sum(int(n) for n in request.session.get("carrito", {}).values() if str(n).isdigit())


def lista(request):
    productos = Producto.objects.filter(activo=True).select_related("categoria").prefetch_related("medidas")
    busqueda = request.GET.get("q", "").strip()
    categoria = request.GET.get("categoria", "").strip()
    disponibilidad = request.GET.get("disponibilidad", "").strip()
    if busqueda:
        productos = productos.filter(Q(nombre__icontains=busqueda) | Q(descripcion__icontains=busqueda) | Q(codigo__icontains=busqueda) | Q(categoria__nombre__icontains=busqueda))
    if categoria.isdigit():
        productos = productos.filter(categoria_id=int(categoria), categoria__activo=True)
    if disponibilidad == "disponible":
        productos = productos.filter(stock__gt=0)
    elif disponibilidad == "agotado":
        productos = productos.filter(stock=0)
    elif disponibilidad == "bajo":
        productos = productos.filter(stock__gt=0, stock__lte=F("stock_minimo"))
    page_obj = Paginator(productos.order_by("nombre"), 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "catalogo/lista.html", {
        "page_obj": page_obj, "categorias": Categoria.objects.filter(activo=True).order_by("nombre"),
        "busqueda": busqueda, "categoria_seleccionada": categoria, "disponibilidad": disponibilidad,
        "carrito_cantidad": _cantidad_carrito(request),
        "filtros_url": params.urlencode(),
        "hero_producto": Producto.objects.filter(activo=True).exclude(imagen="").order_by("pk").first(),
    })


def detalle(request, pk):
    producto = get_object_or_404(Producto.objects.filter(activo=True).select_related("categoria").prefetch_related("medidas"), pk=pk)
    return render(request, "catalogo/detalle.html", {"producto": producto, "carrito_cantidad": _cantidad_carrito(request)})


def _lineas_carrito(request):
    raw = request.session.get("carrito", {})
    ids = [int(pk) for pk in raw if str(pk).isdigit()]
    productos = {p.pk: p for p in Producto.objects.filter(pk__in=ids, activo=True)}
    lineas, total = [], Decimal("0.00")
    for pk, valor in raw.items():
        try:
            cantidad, producto = int(valor), productos.get(int(pk))
        except (TypeError, ValueError):
            continue
        if producto and cantidad > 0:
            subtotal = producto.precio * cantidad
            lineas.append({"producto": producto, "cantidad": cantidad, "subtotal": subtotal})
            total += subtotal
    return lineas, total


def carrito(request):
    lineas, total = _lineas_carrito(request)
    return render(request, "catalogo/carrito.html", {"lineas": lineas, "total": total, "carrito_cantidad": _cantidad_carrito(request)})


@require_POST
def carrito_agregar(request, pk):
    producto = get_object_or_404(Producto, pk=pk, activo=True)
    try:
        cantidad = int(request.POST.get("cantidad", "1"))
    except (TypeError, ValueError):
        cantidad = 0
    cart = request.session.get("carrito", {})
    nueva = int(cart.get(str(pk), 0)) + cantidad
    if cantidad < 1 or nueva > producto.stock:
        messages.error(request, "La cantidad solicitada no está disponible en el stock actual.")
    else:
        cart[str(pk)] = nueva
        request.session["carrito"] = cart
        messages.success(request, f"{producto.nombre} se agregó al carrito.")
    if not request.user.is_authenticated:
        return redirect(f"/clientes/login/?{urlencode({'next': '/carrito/'})}")
    return redirect("catalogo:carrito")


@require_POST
def carrito_actualizar(request, pk):
    cart = request.session.get("carrito", {})
    if str(pk) not in cart:
        return redirect("catalogo:carrito")
    try:
        cantidad = int(request.POST.get("cantidad", "0"))
        producto = Producto.objects.get(pk=pk, activo=True)
    except (TypeError, ValueError, Producto.DoesNotExist):
        cantidad, producto = 0, None
    if cantidad <= 0:
        cart.pop(str(pk), None)
    elif not producto or cantidad > producto.stock:
        messages.error(request, "La cantidad supera las existencias disponibles.")
    else:
        cart[str(pk)] = cantidad
    request.session["carrito"] = cart
    return redirect("catalogo:carrito")


@require_POST
def carrito_vaciar(request):
    request.session["carrito"] = {}
    return redirect("catalogo:carrito")


@login_required
def confirmar_carrito(request):
    lineas, total = _lineas_carrito(request)
    cliente = Cliente.objects.filter(usuario=request.user, activo=True).first()
    if request.method == "POST":
        if not cliente or not lineas:
            messages.error(request, "El carrito está vacío o tu perfil de cliente no está activo.")
            return redirect("catalogo:carrito")
        try:
            pedido = crear_pedido(cliente, [{"producto": row["producto"].pk, "cantidad": row["cantidad"]} for row in lineas],
                                  telefono=request.POST.get("telefono", cliente.telefono),
                                  direccion=request.POST.get("direccion", cliente.direccion))
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return redirect("catalogo:carrito")
        request.session["carrito"] = {}
        return redirect("catalogo:pedido_exito", pk=pedido.pk)
    return render(request, "catalogo/confirmar.html", {"lineas": lineas, "total": total, "cliente": cliente,
                  "carrito_cantidad": _cantidad_carrito(request)})


@login_required
def pedido_exito(request, pk):
    cliente = get_object_or_404(Cliente, usuario=request.user, activo=True)
    pedido = get_object_or_404(PedidoCliente.objects.prefetch_related("detalles__producto"), pk=pk, cliente=cliente)
    return render(request, "catalogo/pedido_exito.html", {"pedido": pedido})
