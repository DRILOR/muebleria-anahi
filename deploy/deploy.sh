#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

echo "=== Despliegue de Mueblería Anahí ==="
echo "Directorio base: $BASE_DIR"

# 1. Validar entorno virtual
if [ ! -d ".venv" ]; then
    echo "ERROR: Entorno virtual .venv no encontrado."
    exit 1
fi

source .venv/bin/activate

# 2. Validar archivo .env
if [ ! -f ".env" ]; then
    echo "ERROR: Archivo .env no encontrado."
    exit 1
fi

# 3. Comprobar conectividad y estado del sistema Django
echo "-> Comprobando estado del sistema Django..."
python manage.py check --database default

# 4. Aplicar migraciones pendientes
echo "-> Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

# 5. Recopilar archivos estáticos
echo "-> Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

# 6. Ejecutar verificación de despliegue
echo "-> Ejecutando verificación de despliegue..."
python manage.py check --deploy || true

echo "=== Despliegue preparado correctamente ==="
echo "Para reiniciar el servicio del servidor de aplicaciones:"
echo "sudo systemctl restart muebleria-anahi"

