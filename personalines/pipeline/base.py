from __future__ import annotations

import logging
from dataclasses import dataclass

from ..domain import Task
from ..status import TaskStatus, check_transition
from ..storage import TaskStore

log = logging.getLogger("personalines")


class StageError(RuntimeError):
    """An expected failure with a message fit to show the user."""


@dataclass(frozen=True)
class StageResult:
    task_id: int
    ok: bool
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    error: str | None = None


class StatusTracker:
    """Moves one task through the state machine, writing each step to the store."""

    def __init__(self, store: TaskStore, task: Task) -> None:
        self.store, self.task_id, self.current = store, task.id, task.status

    def move(self, target: TaskStatus, error: str | None = None) -> None:
        check_transition(self.current, target)
        self.store.set_status(self.task_id, target, error)
        log.info("task %s: %s -> %s", self.task_id, self.current.value, target.value)
        self.current = target

    def fail(self, error: str) -> None:
        if not self.current.is_terminal:
            self.move(TaskStatus.ERROR, error)
