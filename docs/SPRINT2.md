# Sprint 2 — Documentación de entrega

Rama: `sprint2/helen`

## Objetivo

Implementar las historias de usuario US-005, US-006 y US-007 sobre la base del
Sprint 1, manteniendo las 19 pruebas originales y alcanzando una cobertura
automática mínima del 80 %.

## Historias de usuario

### US-005 — Clientes y ventas

**Alcance implementado**

- Listado, búsqueda, registro, edición y eliminación lógica de clientes.
- Registro de ventas con múltiples productos.
- Selección de productos y validación de stock en servidor.
- Precios obtenidos de la base de datos, sin confiar en el navegador.
- Descuento automático de inventario y registro del movimiento de salida.
- Cálculo de subtotales, total y registro del ingreso.
- Comprobante de venta en pantalla y PDF.
- Historial de ventas, detalle y anulación con devolución de stock.
- Trazabilidad mediante `MovimientoProducto` e `Ingreso`.

**Criterios de aceptación**

- No se puede vender un producto inactivo.
- No se puede vender una cantidad superior al stock disponible.
- Una venta completada descuenta stock de forma atómica.
- Una venta anulada devuelve el stock y queda registrada para auditoría.
- El total y los subtotales coinciden con los precios de la base de datos.

**Pruebas**

- `ventas/tests.py`: 44 pruebas.

### US-006 — Reportes administrativos

**Alcance implementado**

- Reporte general de ventas con filtros `desde`/`hasta`, paginación y totales.
- Reporte de productos más vendidos con límite configurable.
- Reporte de inventario de productos y materiales con estados de stock.
- Reporte de ingresos y distribución por método de pago.
- Exportaciones PDF y Excel con tablas, resúmenes y totales.
- Enlaces de exportación que conservan los filtros aplicados.
- Acceso restringido a usuarios `is_staff`.

**Criterios de aceptación**

- Las ventas anuladas no suman a los ingresos, pero se informan para auditoría.
- Los filtros de fecha usan un rango `[inicio, fin)`.
- El inventario distingue agotado, stock bajo y disponible.
- Las exportaciones respetan los filtros de la pantalla.
- El PDF y el Excel se descargan como archivos adjuntos.
- Un usuario sin permisos no puede acceder a los reportes.

**Pruebas**

- `reportes/tests.py`: 33 pruebas.

### US-007 — AnahíBot

**Alcance implementado**

- Página de chat en `/asistente/` con interfaz responsive.
- Endpoint AJAX `POST /asistente/responder/` con JSON.
- Motor determinista que consulta la base de datos.
- Intenciones:
  - Saludo, ayuda y opciones.
  - Consulta de productos por nombre o código.
  - Consulta de materiales por nombre o código.
  - Productos agotados y con stock bajo.
  - Resumen general del inventario.
  - Catálogo de productos activos.
  - Proveedores registrados.
  - Proveedores asociados a un material según sus compras.
  - Ventas, ingresos y ticket promedio por periodo.
  - Productos más vendidos.
  - Recomendaciones de reposición y priorización de ventas.
- Distinción explícita entre:
  - Registro inexistente: no se encontró información.
  - Registro existente con valor cero: se informa el cero sin inventar datos.
- Restricción de ventas, ingresos y proveedores a usuarios `is_staff`.
- Protección CSRF, validación de JSON, longitud máxima de 500 caracteres y
  renderizado seguro de respuestas en el navegador.

**Criterios de aceptación**

- El asistente no muestra datos de ventas o proveedores a usuarios sin permisos.
- El asistente no inventa productos, precios, ventas ni proveedores.
- Las respuestas de inventario y ventas coinciden con la base de datos.
- Un producto agotado se informa como agotado, no como inexistente.
- Un mensaje inválido devuelve un error controlado.
- El chat exige autenticación y token CSRF.

**Pruebas**

- `anahibot/tests.py`: 42 pruebas.

## Decisiones técnicas

### Configuración de pruebas

`config/settings_test.py` usa SQLite en memoria para permitir la ejecución de la
suite en entornos sin servidor MySQL. La configuración de producción
(`config/settings.py`) mantiene MySQL 8.4 mediante `mysqlclient`.

### Servicios y transacciones

- `ventas/services.py` centraliza el registro y la anulación de ventas.
- Se usa `transaction.atomic()` y `select_for_update()` para evitar sobreventa
  y precios manipulados.
- `reportes/services.py` centraliza consultas y agregaciones.
- `reportes/builders.py` transforma datos en una estructura común de reporte.
- `reportes/exporters.py` genera PDF y Excel a partir de esa estructura.
- `anahibot/services.py` separa la detección de intenciones, la consulta de
  datos y la redacción de respuestas.

### Seguridad

- Vistas de clientes, ventas y AnahíBot con `login_required`.
- Reportes y consultas financieras con `staff_member_required` o validación
  equivalente en el servicio del bot.
- CSRF activo en formularios y en el endpoint AJAX.
- Los precios se recalculan desde la base de datos.
- No se almacenan credenciales de IA ni secretos en el repositorio.

### AnahíBot sin dependencia de IA externa

El bot usa reglas deterministas y consultas ORM. No requiere una API key ni
envía datos a terceros. Esto garantiza que las respuestas sean verificables y
que no se generen datos ficticios. Si se incorpora un modelo externo en el
futuro, las credenciales deben gestionarse con variables de entorno.

## Evidencia de pruebas

Comando:

```bash
DJANGO_SETTINGS_MODULE=config.settings_test python manage.py test
```

Resultado:

```text
Ran 138 tests in 7.05s
OK
```

Composición:

- 19 pruebas del Sprint 1.
- 44 pruebas de US-005.
- 33 pruebas de US-006.
- 42 pruebas de US-007.

Cobertura:

```bash
DJANGO_SETTINGS_MODULE=config.settings_test coverage run manage.py test
coverage report -m
```

Resultado de referencia: **93 %** de cobertura total, por encima del mínimo de
80 %. La configuración de cobertura incluye `inventario`, `compras`, `ventas`,
`reportes` y `anahibot`.

## Commits principales

- `feat(ventas): implement US-005 clients, sales and receipts`
- `feat(reportes): implement US-006 sales, inventory and income reports`
- `feat(anahibot): implement US-007 database-backed assistant`

## Entrega

- Rama: `sprint2/helen`
- No se modifica `main`.
- Se conservan las migraciones y funcionalidades del Sprint 1.
- Las migraciones nuevas corresponden a clientes, ventas, ingresos y
  movimientos de productos.
