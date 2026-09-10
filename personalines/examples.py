"""Few-shot style examples.

A random handful is placed in every prompt so the model matches the tone
without producing the same line for every lead.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from importlib import resources
from pathlib import Path


@dataclass(frozen=True)
class ExampleBank:
    lines: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.lines:
            raise ValueError("ExampleBank needs at least one example line")

    @classmethod
    def from_text(cls, text: str) -> "ExampleBank":
        seen: dict[str, None] = {}
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                seen.setdefault(line)          # de-duplicate, keep order
        return cls(tuple(seen))

    @classmethod
    def from_file(cls, path: str | Path) -> "ExampleBank":
        return cls.from_text(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def default(cls) -> "ExampleBank":
        """The examples bundled with the package (personalines/data/examples.txt)."""
        text = resources.files("personalines").joinpath("data/examples.txt").read_text(encoding="utf-8")
        return cls.from_text(text)

    def sample(self, k: int, rng: random.Random | None = None) -> list[str]:
        rng = rng or random
        return rng.sample(self.lines, min(k, len(self.lines)))

    def block(self, k: int, rng: random.Random | None = None) -> str:
        return "\n".join(f"Example: {line}" for line in self.sample(k, rng))
