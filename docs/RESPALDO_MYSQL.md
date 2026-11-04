# Respaldo local de MySQL

Ejecuta `.venv/bin/python tools/backup_mysql.py` desde el directorio del proyecto. El script toma host, puerto, base, usuario y contraseña de la configuración Django que carga `.env`; conecta por el mismo host TCP que usa Django y ejecuta `mysqldump --no-tablespaces`.

La contraseña se escribe solo en un archivo temporal con permisos `0600`, nunca en argumentos del proceso ni en la salida. El dump se crea en `~/Respaldos/muebleria-anahi/mysql-private/` con permisos privados, un nombre UTC único y no reemplaza archivos existentes. Un resultado vacío o un error de `mysqldump` no se publica como respaldo.

El usuario MySQL necesita permisos sobre las tablas y objetos incluidos; el comando evita el privilegio global `PROCESS` mediante `--no-tablespaces`. El script no cambia credenciales ni permisos. Revisa el tamaño del archivo generado y conserva copias fuera de esta máquina para tener un respaldo durable.
