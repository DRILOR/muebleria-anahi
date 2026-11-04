# Sprint 3 — Plan de Integración, Estabilización y Despliegue

Sistema Inteligente de Gestión de Inventario para la Carpintería y Mueblería Anahí.

---

## 1. Estado y Rama de Origen

- **Rama base de origen:** `sprint2/helen` (contiene todo el código funcional del Sprint 1 y Sprint 2 con 138 pruebas aprobadas y 93 % de cobertura).
- **Rama objetivo para entrega:** `sprint3/helen`.
- **Regla de integridad:** No se modifica la rama `main` ni se descartan migraciones o modelos previos.

---

## 2. Objetivos del Sprint 3

1. **Integración transversal:** Consolidar la interoperabilidad fluida entre todos los módulos del sistema (Inventario, Compras, Ventas, Reportes y Asistente AnahíBot).
2. **Estabilización del sistema:**
   - Implementación del endpoint de monitoreo y estado de salud (`/health/`) con validación activa de conexión a MySQL.
   - Creación de páginas de error HTTP personalizadas y accesibles (`404.html` y `500.html`).
   - Configuración de logging estructurado (`LOGGING`) para entornos de depuración y producción.
3. **Seguridad y robustez:**
   - Soporte desacoplado para despliegue seguro con HTTPS y balanceadores/proxies inversos (`CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, cookies seguras vía `.env`).
   - Mantenimiento estricto de transacciones atómicas (`@transaction.atomic` y `select_for_update`) en operaciones que alteran inventario y finanzas.
4. **Preparación para despliegue:**
   - Creación de configuración de servidor WSGI de producción (`deploy/gunicorn.conf.py`).
   - Plantilla de servidor web inverso y servidor de estáticos (`deploy/nginx-muebleria.conf`).
   - Unidad de servicio del sistema operativo (`deploy/muebleria-anahi.service`).
   - Script automatizado de despliegue (`deploy/deploy.sh`).
   - Manifiesto para despliegue en contenedores (`Dockerfile` y `docker-compose.yml`).
5. **Aseguramiento de calidad y cobertura:**
   - Cobertura mínima obligatoria: 80 %.
   - Cobertura lograda: **95 %**.
   - Total de pruebas aprobadas: **150 pruebas** (138 del Sprint 1 y 2 + 12 pruebas de integración y estabilización).

---

## 3. Matriz de Integración Entre Módulos

| Módulo Origen | Módulo Destino | Mecanismo de Integración | Verificación Automatizada |
| :--- | :--- | :--- | :--- |
| **Compras** | **Inventario** | `compras.services.registrar_compra` delega en `inventario.services.registrar_movimiento` el ingreso de material. | `CompraServiceTests.test_registrar_compra_actualiza_total_y_stock` |
| **Ventas** | **Inventario** | `ventas.services.registrar_venta` bloquea stock con `select_for_update`, descuenta existencias y genera `MovimientoProducto` de salida. | `VentaServiceTests.test_registrar_venta_completa_operacion` |
| **Ventas** | **Inventario** | `ventas.services.anular_venta` revierte el stock del producto y genera `MovimientoProducto` de entrada con trazabilidad. | `VentaServiceTests.test_anular_venta_restaura_stock` |
| **Ventas** | **Reportes** | `reportes.services` agrega ventas no anuladas para cálculo de ingresos, productos más vendidos y totales financieros. | `ReportesServiceTests.test_resumen_ventas_excluye_anuladas` |
| **Inventario** | **Reportes** | `reportes.services.reporte_inventario` clasifica stock de productos y materiales en Disponible, Stock Bajo y Agotado. | `ReportesServiceTests.test_reporte_inventario_general` |
| **Todos** | **AnahíBot** | Motor determinista consulta ORM directamente sin inventar cifras, discriminando valores cero de registros inexistentes. | `AnahiBotServiceTests` (42 pruebas dedicadas) |
| **Infraestructura** | **MySQL** | `/health/` verifica activamente la conexión de la base de datos `muebleria_anahi`. | `SistemaIntegracionYDespliegueTests.test_health_check_endpoint` |

---

## 4. Criterios de Aceptación del Sprint 3

1. **CA-001 (Monitoreo de Salud):** El endpoint `GET /health/` debe responder código HTTP 200 con JSON `{"status": "healthy", "database": "ok"}` cuando la base de datos esté accesible, y código 503 en caso de falla de base de datos.
2. **CA-002 (Páginas de Error Branded):** Las solicitudes a rutas inexistentes deben responder HTTP 404 mostrando la plantilla personalizada `404.html` con la estética de Mueblería Anahí. Los errores internos deben renderizar `500.html`.
3. **CA-003 (Configuración de Producción Segura):** El sistema debe permitir activar o desactivar redirección HTTPS, cookies seguras y encabezados HSTS exclusivamente a través del archivo de entorno `.env`, sin modificar código fuente.
4. **CA-004 (Artefactos de Despliegue):** El repositorio debe incluir configuraciones estándar para Gunicorn, Nginx, Systemd y Docker.
5. **CA-005 (Cobertura y Pruebas):** La suite completa debe mantener las 138 pruebas previas y superar el 80 % de cobertura. Se alcanza un **95 % de cobertura con 150 pruebas aprobadas**.

---

## 5. Instrucciones de Despliegue

### Opción A: Despliegue en Servidor Linux (Systemd + Nginx + Gunicorn)

1. **Configurar el entorno:**
   ```bash
   cp .env.example .env
   # Configurar credenciales reales y DJANGO_DEBUG=False
   ```
2. **Ejecutar script de despliegue:**
   ```bash
   ./deploy/deploy.sh
   ```
3. **Instalar servicio Systemd:**
   ```bash
   sudo cp deploy/muebleria-anahi.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now muebleria-anahi
   ```
4. **Configurar Nginx:**
   ```bash
   sudo cp deploy/nginx-muebleria.conf /etc/nginx/sites-available/muebleria-anahi
   sudo ln -sf /etc/nginx/sites-available/muebleria-anahi /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl restart nginx
   ```

### Opción B: Despliegue en Contenedores (Docker Compose)

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
```

---

## 6. Evidencia de Pruebas y Cobertura

### Pruebas Automatizadas
```bash
python manage.py test --keepdb
```
Resultado: **150 pruebas ejecutadas, 150 aprobadas (OK).**

### Cobertura de Código
```bash
coverage run manage.py test --keepdb
coverage report -m
```
Resultado: **95 % de cobertura general.**

