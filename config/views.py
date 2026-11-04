from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


def health_check(request):
    """Endpoint de salud del sistema para balanceadores de carga y monitoreo."""
    db_status = "ok"
    status_code = 200

    try:
        connection.ensure_connection()
    except Exception as exc:
        db_status = f"error: {str(exc)}"
        status_code = 503

    payload = {
        "status": "healthy" if status_code == 200 else "unhealthy",
        "database": db_status,
        "debug": settings.DEBUG,
    }

    return JsonResponse(payload, status=status_code)


def custom_404_view(request, exception=None):
    """Vista personalizada para páginas no encontradas (HTTP 404)."""
    return render(request, "404.html", status=404)


def custom_500_view(request):
    """Vista personalizada para errores internos del servidor (HTTP 500)."""
    return render(request, "500.html", status=500)


def csrf_failure(request, reason=""):
    """Keep CSRF rejection at 403 and explain how to refresh an expired form."""
    return render(request, "403_csrf.html", {"form_url": request.path}, status=403)

