from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Optional

# Prefer psycopg (v3), fall back to psycopg2.
_driver = None
try:
    import psycopg  # type: ignore
    _driver = "psycopg"
except Exception:
    try:
        import psycopg2  # type: ignore
        _driver = "psycopg2"
    except Exception:
        _driver = None

if _driver is None:
    raise ImportError("Install psycopg[binary] or psycopg2-binary.")


@contextmanager
def connect(dsn: str) -> Iterator[Any]:
    if _driver == "psycopg":
        import psycopg  # type: ignore
        conn = psycopg.connect(dsn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        import psycopg2  # type: ignore
        conn = psycopg2.connect(dsn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def execute(conn: Any, sql: str, params: tuple = ()) -> None:
    with conn.cursor() as cur:
        cur.execute(sql, params)


def fetchone(conn: Any, sql: str, params: tuple = ()) -> Optional[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fetchall(conn: Any, sql: str, params: tuple = ()) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()
