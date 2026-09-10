"""Stage 2: write one personalized line per enriched lead, upload the result."""
from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..domain import Task
from ..examples import ExampleBank
from ..jobs import JobFiles, parse_csv, render_csv, write_local
from ..llm import ChatClient
from ..prompts import build_messages, clean_completion
from ..status import TaskStatus
from ..storage import StorageError, TaskStore
from .base import StageError, StageResult, StatusTracker, log
from .collector import DESCRIPTION

PERSONALIZATION = "Personalization"


class PersonalizerStage:
    def __init__(self, store: TaskStore, chat: ChatClient, examples: ExampleBank, work_dir: Path = Path("Filing"), *,
                 max_workers: int = 8, examples_per_prompt: int = 7, rng: random.Random | None = None) -> None:
        self.store, self.chat, self.examples, self.work_dir = store, chat, examples, Path(work_dir)
        self.max_workers, self.examples_per_prompt = max_workers, examples_per_prompt
        self.rng = rng or random.Random()

    def _generate(self, job: tuple[str, str]) -> tuple[str, str | None]:
        description, examples_block = job
        try:
            return clean_completion(self.chat.complete(build_messages(description, examples_block))), None
        except Exception as exc:          # isolate per-lead failures
            return "", str(exc)

    def run(self, task: Task) -> StageResult:
        tracker = StatusTracker(self.store, task)
        files = JobFiles.for_task(task, self.work_dir)
        try:
            rows = parse_csv(self.store.download(files.remote_formatted))
            rows = [r for r in rows if r.get(DESCRIPTION)]
            if not rows:
                raise StageError("No enriched leads to personalize")

            # Sample examples up front on one thread: reproducible with a seeded RNG.
            jobs = [(r[DESCRIPTION], self.examples.block(self.examples_per_prompt, self.rng)) for r in rows]
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                results = list(pool.map(self._generate, jobs))       # map() preserves input order

            out, errors = [], []
            for row, (line, err) in zip(rows, results):
                clean = {k: v for k, v in row.items() if k != DESCRIPTION}
                clean[PERSONALIZATION] = line
                out.append(clean)
                if err:
                    errors.append(err)
            if len(errors) == len(rows):
                raise StageError(f"All {len(rows)} generations failed; first error: {errors[0]}")

            payload = render_csv(out)
            write_local(files.local_final, payload)
            self.store.upload(files.remote_final, payload)
            tracker.move(TaskStatus.COMPLETED)
            log.info("task %s: personalized %d leads, %d failed", task.id, len(rows) - len(errors), len(errors))
            return StageResult(task.id, ok=True, processed=len(rows) - len(errors), failed=len(errors))
        except (StageError, StorageError) as exc:
            tracker.fail(str(exc))
            return StageResult(task.id, ok=False, error=str(exc))
        except Exception as exc:
            log.exception("task %s: personalizer crashed", task.id)
            tracker.fail(f"Internal error: {exc}")
            return StageResult(task.id, ok=False, error=str(exc))
