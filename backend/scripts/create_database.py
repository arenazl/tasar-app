"""Crea la base de datos `tasar` en Aiven si no existe (idempotente)."""
import asyncio
import pymysql
from core.config import settings


def main():
    conn = pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        ssl={"ca": None},  # Aiven requiere SSL pero acepta sin CA path en PyMySQL
        ssl_disabled=False,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"DB `{settings.DB_NAME}` lista.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
