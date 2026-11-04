from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST
from urllib.parse import urlencode

from .forms import AccesoClienteForm, RegistroClienteForm
from .models import Cliente


@ensure_csrf_cookie
@never_cache
@require_http_methods(["GET", "POST"])
def registro(request):
    form = RegistroClienteForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        User = get_user_model()
        with transaction.atomic():
            user = User.objects.create_user(
                username=data["email"], email=data["email"],
                first_name=data["nombre"].strip(), last_name=data["apellidos"].strip(),
                password=data["password1"], is_staff=False, is_superuser=False,
            )
            Cliente.objects.create(
                usuario=user,
                nombre=f'{user.first_name} {user.last_name}'.strip(),
                email=user.email,
            )
        messages.success(request, "Tu cuenta fue creada. Ya puedes iniciar sesión.")
        login_url = reverse("ventas:cliente_login")
        next_url = request.POST.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            login_url = f"{login_url}?{urlencode({'next': next_url})}"
        return redirect(login_url)
    next_url = request.POST.get("next", "") if request.method == "POST" else request.GET.get("next", "")
    return render(request, "clientes/registro.html", {"form": form, "next": next_url})


@ensure_csrf_cookie
@never_cache
@require_http_methods(["GET", "POST"])
def acceso(request):
    if request.method == "GET" and request.user.is_authenticated:
        return redirect("catalogo:lista")
    form = AccesoClienteForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        user = authenticate(request, username=email, password=form.cleaned_data["password"])
        if user is None or not user.is_active:
            form.add_error(None, "El correo o la contraseña no son correctos.")
        else:
            login(request, user)
            destino = request.POST.get("next", "")
            if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                destino = reverse("catalogo:lista")
            return redirect(destino)
    next_url = request.POST.get("next", "") if request.method == "POST" else request.GET.get("next", "")
    return render(request, "clientes/login.html", {"form": form, "next": next_url})


@require_POST
def salir(request):
    logout(request)
    return redirect("catalogo:lista")
