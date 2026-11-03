# Mueblería Anahí

Sistema de gestión de inventario, compras, ventas, reportes y asistencia
conversacional para una mueblería. El proyecto está construido con Django 5.2,
Python 3.11 y MySQL 8.4 para producción.

## Funcionalidades

### Sprint 1

- Gestión de categorías, productos, medidas de productos y materiales.
- Control de stock de productos y materiales con stock mínimo.
- Registro de movimientos de inventario y trazabilidad de entradas y salidas.
- Gestión de proveedores y compras de materiales.
- Interfaz responsive y validaciones de formularios.

### Sprint 2 — US-005: clientes y ventas

- CRUD de clientes con búsqueda, filtros y eliminación lógica.
- Registro de ventas con selección de productos desde la base de datos.
- Validación de stock antes de confirmar la venta.
- Descuento automático de inventario dentro de una transacción atómica.
- Cálculo de subtotales, total y registro automático del ingreso.
- Comprobante de venta en pantalla y PDF.
- Historial de ventas, detalle y anulación con devolución de stock.
- Los precios siempre se toman de la base de datos para evitar alteraciones
  desde el navegador.

### Sprint 2 — US-006: reportes administrativos

- Reporte general de ventas con filtros por fecha y paginación.
- Reporte de productos más vendidos.
- Reporte de inventario de productos y materiales.
- Reporte de ingresos y distribución por método de pago.
- Totales, promedios y resúmenes ejecutivos.
- Exportación profesional a PDF con ReportLab.
- Exportación a Excel con OpenPyXL.
- Acceso restringido a usuarios con permisos de administración (`is_staff`).

### Sprint 2 — US-007: AnahíBot

- Asistente conversacional disponible en `/asistente/`.
- Responde con datos reales de la base de datos:
  - Precio, stock y estado de productos.
  - Stock y costo de referencia de materiales.
  - Productos agotados y con stock bajo.
  - Resumen del inventario.
  - Ventas, ingresos y ticket promedio por periodo.
  - Productos más vendidos.
  - Proveedores registrados y proveedores asociados a un material por sus
    compras.
  - Recomendaciones de reposición y priorización de productos.
- Distingue entre un dato inexistente y un valor registrado en cero.
- No inventa productos, precios, ventas ni proveedores.
- Las consultas de ventas, ingresos y proveedores requieren permisos de
  administración.
- Interfaz de chat responsive con AJAX, protección CSRF y validación de entrada.
- No requiere credenciales de IA ni servicios externos: el motor es determinista
  y consulta directamente la base de datos. Si en el futuro se integra un
  proveedor externo, sus credenciales deben ir en variables de entorno y nunca
  en el repositorio.

## Arquitectura

| App | Responsabilidad |
| --- | --- |
| `inventario` | Productos, materiales, categorías, medidas y movimientos |
| `compras` | Proveedores y compras de materiales |
| `ventas` | Clientes, ventas, ingresos y comprobantes |
| `reportes` | Consultas, reportes, exportaciones PDF/Excel |
| `anahibot` | Motor conversacional e interfaz de chat |
| `config` | Configuración, rutas y settings de pruebas |

Las reglas de negocio críticas están en capas de servicio
(`ventas/services.py`, `reportes/services.py`, `anahibot/services.py`) y las
operaciones de venta usan transacciones atómicas y `select_for_update` para
evitar sobreventa.

## Requisitos

- Python 3.11
- MySQL 8.4 en producción
- Dependencias de `requirements.txt`

## Instalación

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Crear el archivo `.env` a partir de `.env.example` y completar los datos de
conexión:

```bash
cp .env.example .env
```

Variables principales:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DB_NAME=muebleria_anahi
DB_USER=anahi_app
DB_PASSWORD=change-me
DB_HOST=127.0.0.1
DB_PORT=3306
DB_TEST_NAME=muebleria_anahi_test
```

Aplicar migraciones y crear un administrador:

```bash
python manage.py migrate
python manage.py createsuperuser
```

Ejecutar el servidor:

```bash
python manage.py runserver
```

Rutas principales:

- `/productos/`, `/materiales/`, `/compras/`, `/proveedores/`
- `/clientes/`, `/ventas/`
- `/reportes/ventas/`, `/reportes/productos/`, `/reportes/inventario/`,
  `/reportes/ingresos/`
- `/asistente/`

## Pruebas

La suite usa `config.settings_test`, que emplea SQLite en memoria para poder
ejecutarse en entornos sin servidor MySQL. La configuración de producción sigue
usando MySQL 8.4.

```bash
DJANGO_SETTINGS_MODULE=config.settings_test python manage.py test
```

Cobertura:

```bash
DJANGO_SETTINGS_MODULE=config.settings_test coverage run manage.py test
coverage report -m
```

La suite incluye las 19 pruebas originales del Sprint 1 y pruebas nuevas para
clientes, ventas, reportes, exportaciones y AnahíBot. La cobertura configurada
exige un mínimo de 80 %.

## Seguridad

- Autenticación obligatoria para clientes, ventas, reportes y AnahíBot.
- Reportes, ventas financieras y proveedores restringidos a usuarios `is_staff`.
- Protección CSRF en el chat y en los formularios.
- Validación y límite de longitud de los mensajes del asistente.
- Precios y stock recalculados en el servidor, nunca confiados al navegador.
- Credenciales y secretos fuera del repositorio mediante variables de entorno.

## Documentación adicional

- [Sprint 2](docs/SPRINT2.md): alcance, historias de usuario, decisiones
  técnicas y criterios de aceptación.

## Rama de entrega

El desarrollo del Sprint 2 se encuentra en la rama `sprint2/helen`.
