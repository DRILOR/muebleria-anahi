"""Create a private, non-overwriting MySQL dump using Django's DB settings."""

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


PROJECT_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, str(PROJECT_DIR))

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402


def option_value(value):
    value = str(value or "")
    if "\n" in value or "\r" in value:
        raise ValueError("MySQL connection settings cannot contain line breaks.")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    database = settings.DATABASES["default"]
    if database.get("ENGINE") != "django.db.backends.mysql":
        raise SystemExit("The configured Django database is not MySQL; no backup was created.")
    mysqldump = shutil.which("mysqldump")
    if not mysqldump:
        raise SystemExit("mysqldump is not installed or not available in PATH.")

    db_name = database["NAME"]
    if not db_name:
        raise SystemExit("Django has no database name configured; no backup was created.")
    if not re.fullmatch(r"[A-Za-z0-9_$-]+", str(db_name)):
        raise SystemExit("The configured database name contains unsupported path characters.")
    backup_dir = Path.home() / "Respaldos" / "muebleria-anahi" / "mysql-private"
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if backup_dir.stat().st_mode & 0o077:
        raise SystemExit(f"Protect the backup directory first: chmod 700 {backup_dir}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    final_path = backup_dir / f"{db_name}-{timestamp}.sql"
    partial_path = backup_dir / f".{db_name}-{timestamp}-{os.getpid()}.partial"
    config_values = {
        "host": database.get("HOST") or "localhost",
        "user": database.get("USER") or "",
        "password": database.get("PASSWORD") or "",
        "port": database.get("PORT") or 3306,
    }

    option_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="anahi-mysql-", suffix=".cnf", delete=False) as option_file:
            option_file_path = option_file.name
            os.chmod(option_file_path, 0o600)
            option_file.write("[client]\n")
            for key, value in config_values.items():
                option_file.write(f"{key}={option_value(value)}\n")

        descriptor = os.open(partial_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        result = subprocess.run(
            [
                mysqldump,
                f"--defaults-extra-file={option_file.name}",
                "--no-tablespaces",
                "--single-transaction",
                "--quick",
                "--skip-lock-tables",
                f"--result-file={partial_path}",
                db_name,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0 or not partial_path.is_file() or partial_path.stat().st_size == 0:
            error = result.stderr.decode("utf-8", errors="replace").lower()
            if "1045" in error or "access denied" in error:
                detail = "MySQL rejected the configured account; verify Django's host, user and database access."
            elif "process" in error:
                detail = "MySQL reported a PROCESS privilege error despite --no-tablespaces; review server/client versions and grants."
            else:
                detail = "Check that MySQL is running and that the account can read the configured database."
            raise SystemExit(f"mysqldump failed. {detail} No backup was published.")
        with partial_path.open("rb") as dump_file:
            if not dump_file.read(128).strip():
                raise SystemExit("The dump file is empty. No backup was published.")
        os.link(partial_path, final_path)
        print(f"Backup created: {final_path} ({final_path.stat().st_size} bytes)")
    finally:
        try:
            os.unlink(partial_path)
        except FileNotFoundError:
            pass
        if option_file_path:
            try:
                os.unlink(option_file_path)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    main()
