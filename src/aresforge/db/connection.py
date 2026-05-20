from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from aresforge.config import AppConfig


@contextmanager
def connect(config: AppConfig) -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(config.database_dsn(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
