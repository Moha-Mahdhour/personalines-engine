"""Task lifecycle.

Every job is a row in the `tasks` table whose Status column moves through a
fixed set of states. The web app reads that column to show progress, so the
allowed transitions are defined once here and enforced by the workers.

    Init -> Searching -> Personalizing -> Completed
               |               |
               +---> Error <---+
"""
from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
    INIT = "Init"
    SEARCHING = "Searching"
    PERSONALIZING = "Personalizing"
    COMPLETED = "Completed"
    ERROR = "Error"

    @classmethod
    def parse(cls, value: str) -> "TaskStatus":
        """Accept the exact stored value, case-insensitively."""
        for status in cls:
            if status.value.lower() == str(value).strip().lower():
                return status
        raise ValueError(f"Unknown task status: {value!r}")

    @property
    def is_terminal(self) -> bool:
        return self in (TaskStatus.COMPLETED, TaskStatus.ERROR)


TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.INIT: frozenset({TaskStatus.SEARCHING, TaskStatus.ERROR}),
    TaskStatus.SEARCHING: frozenset({TaskStatus.PERSONALIZING, TaskStatus.ERROR}),
    TaskStatus.PERSONALIZING: frozenset({TaskStatus.COMPLETED, TaskStatus.ERROR}),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.ERROR: frozenset(),
}


class InvalidTransition(ValueError):
    pass


def can_transition(current: TaskStatus, target: TaskStatus) -> bool:
    return target in TRANSITIONS[current]


def check_transition(current: TaskStatus, target: TaskStatus) -> None:
    if not can_transition(current, target):
        raise InvalidTransition(f"{current.value} -> {target.value} is not allowed")
