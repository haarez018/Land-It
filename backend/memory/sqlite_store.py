"""SQLite structured data store — drop-in replacement for in-memory dicts."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional


class JSONSQLiteStore:
    """
    Persistent key-value store backed by SQLite.
    Values are serialized as JSON; Pydantic models are handled automatically.
    Implements __getitem__, __setitem__, __contains__, and .values() so it
    can replace a plain dict[str, Model] without changing call sites.
    """

    def __init__(
        self,
        table: str,
        model_class=None,
        db_path: str = "data/career_copilot.db",
    ) -> None:
        self._table = table
        self._model_class = model_class
        self._db_path = db_path
        self._init_db()

    # ── Private ──────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _serialize(self, value: Any) -> str:
        if hasattr(value, "model_dump"):
            return json.dumps(value.model_dump())
        return json.dumps(value)

    def _deserialize(self, raw: str) -> Any:
        data = json.loads(raw)
        if self._model_class is not None:
            return self._model_class.model_validate(data)
        return data

    # ── Public API ────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT value FROM {self._table} WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return default
        return self._deserialize(row["value"])

    def set(self, key: str, value: Any) -> None:
        serialized = self._serialize(value)
        with self._connect() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {self._table} (key, value) VALUES (?, ?)",
                (key, serialized),
            )

    def delete(self, key: str) -> None:
        with self._connect() as conn:
            conn.execute(f"DELETE FROM {self._table} WHERE key = ?", (key,))

    def values(self) -> list:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT value FROM {self._table}").fetchall()
        return [self._deserialize(row["value"]) for row in rows]

    def all_keys(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT key FROM {self._table}").fetchall()
        return [row["key"] for row in rows]

    # ── Dict-protocol methods ─────────────────────────────────────────────

    def __contains__(self, key: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT 1 FROM {self._table} WHERE key = ?", (key,)
            ).fetchone()
        return row is not None

    def __getitem__(self, key: str) -> Any:
        result = self.get(key)
        if result is None:
            raise KeyError(key)
        return result

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        if key not in self:
            raise KeyError(key)
        self.delete(key)
