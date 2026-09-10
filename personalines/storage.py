"""Task storage: files in a bucket plus a Status column per task.

Workers talk to the TaskStore protocol only. SupabaseTaskStore is the
production adapter; InMemoryTaskStore backs the tests and local dry runs.
"""
from __future__ import annotations

import threading
from typing import Protocol

from .status import TaskStatus


class StorageError(RuntimeError):
    pass


class TaskStore(Protocol):
    def download(self, key: str) -> bytes: ...
    def upload(self, key: str, data: bytes, content_type: str = "text/csv") -> None: ...
    def set_status(self, task_id: int, status: TaskStatus, error: str | None = None) -> None: ...


class SupabaseTaskStore:
    """Supabase Storage + Postgres. The client is created on first use."""

    def __init__(self, url: str, key: str, bucket: str = "Users", table: str = "tasks") -> None:
        self._url, self._key = url, key
        self.bucket, self.table = bucket, table
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        with self._lock:
            if self._client is None:
                try:
                    from supabase import create_client
                except ImportError as exc:
                    raise StorageError("Install the 'supabase' extra: pip install '.[supabase]'") from exc
                self._client = create_client(self._url, self._key)
            return self._client

    def download(self, key: str) -> bytes:
        try:
            return self.client.storage.from_(self.bucket).download(key)
        except Exception as exc:  # the SDK raises several unrelated types
            raise StorageError(f"download failed for {key}: {exc}") from exc

    def upload(self, key: str, data: bytes, content_type: str = "text/csv") -> None:
        try:
            self.client.storage.from_(self.bucket).upload(
                path=key, file=data, file_options={"content-type": content_type, "upsert": "true"})
        except Exception as exc:
            raise StorageError(f"upload failed for {key}: {exc}") from exc

    def set_status(self, task_id: int, status: TaskStatus, error: str | None = None) -> None:
        row: dict[str, str] = {"Status": status.value}
        if error is not None:
            row["error_message"] = error[:1000]
        self.client.table(self.table).update(row).eq("id", task_id).execute()


class InMemoryTaskStore:
    """Thread-safe fake with the same interface; records every status change."""

    def __init__(self, files: dict[str, bytes] | None = None) -> None:
        self.files: dict[str, bytes] = dict(files or {})
        self.history: dict[int, list[tuple[TaskStatus, str | None]]] = {}
        self._lock = threading.Lock()

    def download(self, key: str) -> bytes:
        with self._lock:
            if key not in self.files:
                raise StorageError(f"not found: {key}")
            return self.files[key]

    def upload(self, key: str, data: bytes, content_type: str = "text/csv") -> None:
        with self._lock:
            self.files[key] = data

    def set_status(self, task_id: int, status: TaskStatus, error: str | None = None) -> None:
        with self._lock:
            self.history.setdefault(task_id, []).append((status, error))

    def status_of(self, task_id: int) -> TaskStatus | None:
        h = self.history.get(task_id)
        return h[-1][0] if h else None
