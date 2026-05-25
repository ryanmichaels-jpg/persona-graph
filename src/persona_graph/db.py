"""Thin SQLite wrapper used by every Python module (seed, analyze, icp).

The Next.js side reads SQLite directly via better-sqlite3 — this Python module
exists for the write path (scrape → analyze → score). The committed
data/intel.db file is the canonical data layer.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_PATH = Path(os.getenv("INTEL_DB_PATH", "data/intel.db"))


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "init_db.sql"


@contextmanager
def connect(path: Path | None = None, init_if_missing: bool = True):
    """Open a SQLite connection with foreign keys on. Initializes schema if the
    DB file doesn't exist yet."""
    path = path or DEFAULT_DB_PATH
    if init_if_missing and not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as init_conn:
            init_conn.executescript(_schema_path().read_text())

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reset_db(path: Path | None = None) -> None:
    """Wipe everything and re-apply schema. Used by tests + seed regeneration."""
    path = path or DEFAULT_DB_PATH
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(_schema_path().read_text())
