"""Lemma DB compatibility layer mapping Supabase DB queries to Lemma Pod records."""

from __future__ import annotations
from functools import lru_cache
from typing import Any
from datetime import datetime, timezone
import uuid

from backend.config import settings
from backend.lemma_client import get_pod


class SupabaseLikeResponse:
    """Mock response object mimicking Supabase Postgrest API response."""
    def __init__(self, data: Any = None):
        self.data = data

    @property
    def count(self) -> int:
        if isinstance(self.data, list):
            return len(self.data)
        return 1 if self.data else 0


class LemmaTableQuery:
    """Fluent query builder mapping Supabase-style calls to Lemma SDK methods."""
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.filters: list[tuple[str, Any]] = []
        self._order: tuple[str, bool] | None = None
        self._range: tuple[int, int] | None = None
        self._single: bool = False
        self._operation: str = "select"  # select | insert | upsert | update | delete
        self._data_payload: Any = None

    def select(self, columns: str = "*") -> LemmaTableQuery:
        self._operation = "select"
        return self

    def insert(self, data: dict | list[dict]) -> LemmaTableQuery:
        self._operation = "insert"
        self._data_payload = data
        return self

    def upsert(self, data: dict | list[dict], on_conflict: str = None) -> LemmaTableQuery:
        self._operation = "upsert"
        self._data_payload = data
        self._on_conflict = on_conflict
        return self

    def update(self, data: dict) -> LemmaTableQuery:
        self._operation = "update"
        self._data_payload = data
        return self

    def delete(self) -> LemmaTableQuery:
        self._operation = "delete"
        return self

    def eq(self, field: str, value: Any) -> LemmaTableQuery:
        self.filters.append((field, value))
        return self

    def order(self, field: str, desc: bool = False) -> LemmaTableQuery:
        self._order = (field, desc)
        return self

    def range(self, start: int, end: int) -> LemmaTableQuery:
        self._range = (start, end)
        return self

    def maybe_single(self) -> LemmaTableQuery:
        self._single = True
        return self

    def execute(self) -> SupabaseLikeResponse:
        pod = get_pod()

        if self._operation == "select":
            # List all records in the table (support up to 1000 items)
            resp = pod.records.list(self.table_name, limit=1000)
            items = resp.to_dict().get("items", [])

            # Filter records in-memory
            filtered = []
            for item in items:
                match = True
                for field, val in self.filters:
                    if item.get(field) != val:
                        match = False
                        break
                if match:
                    filtered.append(item)

            # Apply ordering
            if self._order:
                sort_field, desc = self._order
                # Graceful sorting fallback for missing/null keys
                filtered.sort(
                    key=lambda x: (
                        x.get(sort_field) is not None,
                        x.get(sort_field)
                    ),
                    reverse=desc
                )

            # Apply pagination slicing
            if self._range:
                start, end = self._range
                filtered = filtered[start : end + 1]

            # Handle maybe_single return shape
            if self._single:
                data_result = filtered[0] if filtered else None
            else:
                data_result = filtered

            return SupabaseLikeResponse(data=data_result)

        elif self._operation == "insert":
            inserted_items = []
            payloads = (
                self._data_payload
                if isinstance(self._data_payload, list)
                else [self._data_payload]
            )
            for p in payloads:
                record = {**p}
                if "id" not in record:
                    record["id"] = str(uuid.uuid4())
                if "created_at" not in record:
                    record["created_at"] = datetime.now(timezone.utc).isoformat()

                inserted = pod.records.create(self.table_name, record)
                inserted_items.append(inserted)

            data_result = inserted_items if isinstance(self._data_payload, list) else inserted_items[0]
            return SupabaseLikeResponse(data=data_result)

        elif self._operation == "upsert":
            # List all existing items to detect conflicts
            resp = pod.records.list(self.table_name, limit=1000)
            items = resp.to_dict().get("items", [])

            conflict_fields = []
            if hasattr(self, "_on_conflict") and self._on_conflict:
                conflict_fields = [f.strip() for f in self._on_conflict.split(",")]

            inserted_items = []
            payloads = (
                self._data_payload
                if isinstance(self._data_payload, list)
                else [self._data_payload]
            )
            for p in payloads:
                record = {**p}
                if "created_at" not in record:
                    record["created_at"] = datetime.now(timezone.utc).isoformat()

                # Search for an existing record matching either composite keys or ID
                existing_item = None
                if conflict_fields:
                    for item in items:
                        match = True
                        for field in conflict_fields:
                            if item.get(field) != record.get(field):
                                match = False
                                break
                        if match:
                            existing_item = item
                            break
                elif "id" in record:
                    for item in items:
                        if item.get("id") == record["id"]:
                            existing_item = item
                            break

                if existing_item:
                    # Update fields in the existing record
                    updated = pod.records.update(self.table_name, existing_item["id"], record)
                    inserted_items.append(updated)
                else:
                    # Create new record
                    if "id" not in record:
                        record["id"] = str(uuid.uuid4())
                    inserted = pod.records.create(self.table_name, record)
                    inserted_items.append(inserted)

            data_result = inserted_items if isinstance(self._data_payload, list) else inserted_items[0]
            return SupabaseLikeResponse(data=data_result)

        elif self._operation == "update":
            # Fetch all existing items to find matches
            resp = pod.records.list(self.table_name, limit=1000)
            items = resp.to_dict().get("items", [])

            updated_items = []
            for item in items:
                match = True
                for field, val in self.filters:
                    if item.get(field) != val:
                        match = False
                        break
                if match:
                    updated = pod.records.update(self.table_name, item["id"], self._data_payload)
                    updated_items.append(updated)

            return SupabaseLikeResponse(data=updated_items)

        elif self._operation == "delete":
            # Fetch all existing items to find matches
            resp = pod.records.list(self.table_name, limit=1000)
            items = resp.to_dict().get("items", [])

            deleted_items = []
            for item in items:
                match = True
                for field, val in self.filters:
                    if item.get(field) != val:
                        match = False
                        break
                if match:
                    pod.records.delete(self.table_name, item["id"])
                    deleted_items.append(item)

            return SupabaseLikeResponse(data=deleted_items)

        return SupabaseLikeResponse()


class LemmaDBCompat:
    """Supabase-compatible DB client wrapper using Lemma SDK."""
    def table(self, table_name: str) -> LemmaTableQuery:
        return LemmaTableQuery(table_name)


@lru_cache(maxsize=1)
def get_db() -> Any:
    """Return the cached Lemma DB compatibility wrapper client."""
    # Ensure Lemma configuration environment variables are present
    if not settings.LEMMA_TOKEN or not settings.LEMMA_POD_ID:
        raise RuntimeError("LEMMA_TOKEN and LEMMA_POD_ID must be set in .env")

    return LemmaDBCompat()
