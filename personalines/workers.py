"""Background worker threads, one per stage."""
from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Protocol

from .domain import Task

log = logging.getLogger("personalines")


class Stage(Protocol):
    def run(self, task: Task): ...


class StageWorker:
    """Runs a stage on queued tasks, one at a time, until stopped."""

    def __init__(self, name: str, stage: Stage, poll_interval: float = 0.5) -> None:
        self.name, self.stage, self.poll_interval = name, stage, poll_interval
        self._queue: queue.Queue[Task] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name=f"worker-{name}", daemon=True)

    def start(self) -> "StageWorker":
        self._thread.start()
        return self

    def submit(self, task: Task) -> None:
        self._queue.put(task)

    def wait_idle(self, timeout: float | None = None) -> bool:
        """Wait until every submitted task is processed. Returns False on timeout."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while self._queue.unfinished_tasks:
            if deadline is not None and time.monotonic() > deadline:
                return False
            time.sleep(0.01)
        return True

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._thread.join(timeout)

    @property
    def alive(self) -> bool:
        return self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                task = self._queue.get(timeout=self.poll_interval)   # no busy-waiting
            except queue.Empty:
                continue
            task_id = getattr(task, "id", task)
            try:
                result = self.stage.run(task)
                log.info("%s finished task %s: %s", self.name, task_id, result)
            except Exception:
                # Stages report their own failures; this only catches bugs.
                # Nothing in here may raise, or the thread would die.
                log.exception("%s crashed on task %s", self.name, task_id)
            finally:
                self._queue.task_done()
