from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from django.conf.urls.static import static
from django.views.generic import RedirectView

from .views import custom_404_view, custom_500_view, health_check


urlpatterns = [
    path(
        "",
        RedirectView.as_view(
            pattern_name="catalogo:lista",
            permanent=False,
        ),
    ),
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("", include("catalogo.urls")),
    path("", include("inventario.urls")),
    path("", include("compras.urls")),
    path("", include("ventas.urls")),
    path("", include("reportes.urls")),
    path("", include("anahibot.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = custom_404_view
handler500 = custom_500_view
