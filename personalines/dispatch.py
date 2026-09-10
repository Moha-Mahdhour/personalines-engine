"""Route incoming task events to the worker for their current status."""
from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any, Mapping, Protocol

from .domain import Task
from .status import TaskStatus

log = logging.getLogger("personalines")


class Submitter(Protocol):
    name: str
    def submit(self, task: Task) -> None: ...


class Dispatcher:
    """Maps a task's status to a worker and drops duplicate deliveries.

    Supabase can deliver the same row change more than once (webhook retries,
    overlapping INSERT/UPDATE subscriptions), so each (task, status) pair is
    only dispatched once within a bounded memory window.
    """

    def __init__(self, routes: Mapping[TaskStatus, Submitter], memory: int = 10_000) -> None:
        self.routes, self.memory = dict(routes), memory
        self._seen: OrderedDict[tuple[int, TaskStatus], None] = OrderedDict()

    def dispatch(self, payload: Mapping[str, Any]) -> str | None:
        try:
            task = Task.from_payload(payload)
        except ValueError as exc:
            log.warning("ignoring malformed task event: %s", exc)
            return None
        worker = self.routes.get(task.status)
        if worker is None:
            return None                              # e.g. Completed/Error updates
        key = (task.id, task.status)
        if key in self._seen:
            log.info("duplicate event for task %s (%s) ignored", task.id, task.status.value)
            return None
        self._seen[key] = None
        if len(self._seen) > self.memory:
            self._seen.popitem(last=False)
        worker.submit(task)
        return worker.name
