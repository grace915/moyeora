"""SQLite 데이터 액세스 — 슬러그 단위로 응답만 저장."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

DB_PATH = Path(os.environ.get("DB_PATH") or (Path(__file__).parent / "moyeora.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS responses (
    slug            TEXT NOT NULL,
    name            TEXT NOT NULL,
    available_date  TEXT NOT NULL,
    PRIMARY KEY (slug, name, available_date)
);
CREATE INDEX IF NOT EXISTS idx_responses_slug ON responses(slug);

CREATE TABLE IF NOT EXISTS finalized (
    slug        TEXT PRIMARY KEY,
    final_date  TEXT NOT NULL
);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


def save_response(slug: str, name: str, available_dates: list[str]) -> None:
    """이름 기준으로 가용일을 통째로 교체."""
    name = name.strip()
    if not name:
        raise ValueError("이름이 필요합니다.")

    valid: list[str] = []
    for d in available_dates:
        try:
            date.fromisoformat(d)
            valid.append(d)
        except ValueError:
            continue

    with connect() as c:
        c.execute(
            "DELETE FROM responses WHERE slug = ? AND name = ?",
            (slug, name),
        )
        c.executemany(
            "INSERT OR IGNORE INTO responses(slug, name, available_date) VALUES (?, ?, ?)",
            [(slug, name, d) for d in valid],
        )


def get_responses(slug: str) -> dict[str, set[str]]:
    """이름 → 가능 날짜 집합."""
    with connect() as c:
        rows = c.execute(
            "SELECT name, available_date FROM responses WHERE slug = ?",
            (slug,),
        ).fetchall()
    out: dict[str, set[str]] = {}
    for r in rows:
        out.setdefault(r["name"], set()).add(r["available_date"])
    return out


def get_finalized(slug: str) -> str | None:
    with connect() as c:
        row = c.execute(
            "SELECT final_date FROM finalized WHERE slug = ?", (slug,)
        ).fetchone()
    return row["final_date"] if row else None


def set_finalized(slug: str, final_date: str) -> None:
    date.fromisoformat(final_date)  # 형식 검증
    with connect() as c:
        c.execute(
            "INSERT INTO finalized(slug, final_date) VALUES (?, ?) "
            "ON CONFLICT(slug) DO UPDATE SET final_date = excluded.final_date",
            (slug, final_date),
        )


def clear_finalized(slug: str) -> None:
    with connect() as c:
        c.execute("DELETE FROM finalized WHERE slug = ?", (slug,))
