import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services import MAX_MENSAJE, responder_mensaje, sugerencias_iniciales


@login_required
def index(request):
    return render(
        request,
        "anahibot/index.html",
        {
            "sugerencias": sugerencias_iniciales(request.user),
        },
    )


@login_required
@require_POST
def responder(request):
    try:
        datos = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "La solicitud no contiene un JSON válido."},
            status=400,
        )

    if not isinstance(datos, dict):
        return JsonResponse(
            {"error": "La solicitud debe enviar un objeto JSON."},
            status=400,
        )

    mensaje = datos.get("mensaje")

    if not isinstance(mensaje, str):
        return JsonResponse(
            {"error": "Debes enviar el campo «mensaje» como texto."},
            status=400,
        )

    mensaje = mensaje.strip()

    if not mensaje:
        return JsonResponse(
            {"error": "Escribe una consulta antes de enviar."},
            status=400,
        )

    if len(mensaje) > MAX_MENSAJE:
        return JsonResponse(
            {
                "error": (
                    f"La consulta no puede superar los "
                    f"{MAX_MENSAJE} caracteres."
                )
            },
            status=400,
        )

    return JsonResponse(
        responder_mensaje(mensaje, request.user)
    )
