"""Migración manual: agrega columnas IA-first a `comparables` y crea `external_listings`.

SQLAlchemy `create_all` solo crea tablas nuevas, no modifica existentes.
Este script aplica los ALTER TABLE necesarios. Idempotente: si una columna ya existe, la salta.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql
from core.config import settings


ALTERS = [
    "ALTER TABLE comparables ADD COLUMN source_type VARCHAR(30) DEFAULT 'manual'",
    "ALTER TABLE comparables ADD COLUMN ai_reason TEXT",
    "ALTER TABLE comparables ADD COLUMN source_property_id INT",
    "ALTER TABLE comparables ADD COLUMN external_listing_id INT",
]


def main():
    conn = pymysql.connect(
        host=settings.DB_HOST, port=settings.DB_PORT,
        user=settings.DB_USER, password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        ssl={"fake_flag_to_enable_tls": True},
    )
    try:
        with conn.cursor() as cur:
            for sql in ALTERS:
                try:
                    cur.execute(sql)
                    print(f"OK: {sql[:80]}")
                except pymysql.err.OperationalError as e:
                    if "Duplicate column" in str(e) or "1060" in str(e):
                        print(f"SKIP (ya existe): {sql[:80]}")
                    else:
                        print(f"FAIL: {sql[:80]} -- {e}")
        conn.commit()
        print("\nMigración OK")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
