"""Configuración usada exclusivamente por la suite de pruebas.

La configuración de producción sigue apuntando a MySQL 8.4. En entornos
de integración continua sin servidor MySQL se utiliza SQLite en memoria
para poder ejecutar la misma suite de pruebas de forma reproducible.
"""

import os

from .settings import *  # noqa: F401,F403


SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-test-key-sprint2",
)

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Los archivos generados por los reportes se prueban en memoria.
MEDIA_ROOT = "/tmp/opencode/muebleria-anahi-media"
