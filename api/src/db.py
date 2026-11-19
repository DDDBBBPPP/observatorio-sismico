import os
from contextlib import contextmanager

import psycopg


@contextmanager
def connection():
    conn = psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "observatorio"),
        user=os.environ.get("POSTGRES_USER", "observatorio"),
        password=os.environ.get("POSTGRES_PASSWORD", "local-development-only"),
    )
    try:
        yield conn
    finally:
        conn.close()
