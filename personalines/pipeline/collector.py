"""Stage 1: download the lead list, enrich every lead, upload the result."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from ..domain import Profile, Task
from ..enrichment import Enricher
from ..jobs import JobFiles, parse_csv, render_csv, write_local
from ..status import TaskStatus
from ..storage import StorageError, TaskStore
from .base import StageError, StageResult, StatusTracker, log

DESCRIPTION = "Description"


class CollectorStage:
    def __init__(self, store: TaskStore, enricher: Enricher, work_dir: Path = Path("Filing"), *,
                 download_attempts: int = 3, retry_delay: float = 5.0,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.store, self.enricher, self.work_dir = store, enricher, Path(work_dir)
        self.download_attempts, self.retry_delay, self._sleep = download_attempts, retry_delay, sleep

    def _download(self, key: str) -> bytes:
        # The web app inserts the task row and uploads the file in parallel,
        # so the file can arrive a moment after the task.
        for attempt in range(1, self.download_attempts + 1):
            try:
                return self.store.download(key)
            except StorageError:
                if attempt == self.download_attempts:
                    raise StageError(f"Uploaded file not found after {attempt} attempts: {key}")
                self._sleep(self.retry_delay)
        raise AssertionError("unreachable")

    def run(self, task: Task) -> StageResult:
        tracker = StatusTracker(self.store, task)
        files = JobFiles.for_task(task, self.work_dir)
        try:
            tracker.move(TaskStatus.SEARCHING)
            data = self._download(files.remote_input)
            write_local(files.local_input, data)
            rows = parse_csv(data)
            if not rows:
                raise StageError("The uploaded file has no rows")
            if task.linkedin_field not in rows[0]:
                raise StageError(f"Column {task.linkedin_field!r} not found; columns are: {', '.join(rows[0])}")

            profiles = self.enricher.enrich([r.get(task.linkedin_field) for r in rows])
            enriched = []
            for row, data_ in zip(rows, profiles):
                text = Profile.from_proxycurl(data_).to_prompt_text() if data_ else ""
                if text:
                    enriched.append({**row, DESCRIPTION: text})
            skipped = len(rows) - len(enriched)
            if not enriched:
                raise StageError(f"None of the {len(rows)} leads could be enriched")

            payload = render_csv(enriched)
            write_local(files.local_formatted, payload)
            self.store.upload(files.remote_formatted, payload)
            tracker.move(TaskStatus.PERSONALIZING)
            log.info("task %s: enriched %d leads, skipped %d", task.id, len(enriched), skipped)
            return StageResult(task.id, ok=True, processed=len(enriched), skipped=skipped)
        except (StageError, StorageError) as exc:
            tracker.fail(str(exc))
            return StageResult(task.id, ok=False, error=str(exc))
        except Exception as exc:  # never leave a task stuck in Searching
            log.exception("task %s: collector crashed", task.id)
            tracker.fail(f"Internal error: {exc}")
            return StageResult(task.id, ok=False, error=str(exc))
