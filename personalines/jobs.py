"""Where a job's files live, locally and in storage, plus CSV helpers.

Remote keys must match what the web app uploads and downloads, so they keep
the historical naming:

    <user>/<task>/<file>                          uploaded lead list
    <user>/<task>/<file minus .csv>-formatted.csv  enriched leads
    <user>/<task>/<file up to first dot>-formatted-Final.csv   finished output

Local paths use one consistent stem. The old workers derived it two
different ways, so a file such as ``leads.v2.csv`` was written under one
name by the collector and looked for under another by the personalizer.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .domain import Task


def _strip_csv(name: str) -> str:
    return name[:-4] if name.lower().endswith(".csv") else name


@dataclass(frozen=True)
class JobFiles:
    user_id: str
    task_id: int
    file_name: str
    work_dir: Path = Path("Filing")

    @classmethod
    def for_task(cls, task: Task, work_dir: Path = Path("Filing")) -> "JobFiles":
        return cls(task.user_id, task.id, task.file_name, Path(work_dir))

    # remote storage keys (compatible with the web app)
    @property
    def _prefix(self) -> str:
        return f"{self.user_id}/{self.task_id}"

    @property
    def remote_input(self) -> str:
        return f"{self._prefix}/{self.file_name}"

    @property
    def remote_formatted(self) -> str:
        return f"{self._prefix}/{_strip_csv(self.file_name)}-formatted.csv"

    @property
    def remote_final(self) -> str:
        return f"{self._prefix}/{self.file_name.split('.')[0]}-formatted-Final.csv"

    # local working files
    @property
    def local_dir(self) -> Path:
        return self.work_dir / self.user_id / str(self.task_id)

    @property
    def local_input(self) -> Path:
        return self.local_dir / self.file_name

    @property
    def local_formatted(self) -> Path:
        return self.local_dir / f"{_strip_csv(self.file_name)}-formatted.csv"

    @property
    def local_final(self) -> Path:
        return self.local_dir / f"{_strip_csv(self.file_name)}-final.csv"


def parse_csv(data: bytes | str) -> list[dict[str, str]]:
    """Rows from CSV content. Tolerates the BOM that Excel adds."""
    text = data.decode("utf-8-sig") if isinstance(data, bytes) else data.lstrip("﻿")
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def render_csv(rows: Sequence[dict[str, str]], fieldnames: Iterable[str] | None = None) -> bytes:
    """CSV bytes for rows; columns follow first appearance across all rows."""
    if fieldnames is None:
        cols: dict[str, None] = {}
        for row in rows:
            for key in row:
                cols.setdefault(key)
        fieldnames = list(cols)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(fieldnames), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def write_local(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path
