"""Domain models: the task that drives a job, and the enriched lead profile.

Plain dataclasses, so they are importable and testable without pydantic.
Parsing is deliberately forgiving about missing optional fields, because
enrichment APIs return partial profiles all the time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .status import TaskStatus


@dataclass(frozen=True)
class Task:
    id: int
    user_id: str
    file_name: str
    status: TaskStatus
    linkedin_field: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Task":
        try:
            return cls(
                id=int(record["id"]),
                user_id=str(record["UserID"]),
                file_name=str(record["FileName"]),
                status=TaskStatus.parse(record["Status"]),
                linkedin_field=str(record.get("LinkedinField") or "LinkedIn"),
            )
        except KeyError as exc:
            raise ValueError(f"Task record is missing field {exc.args[0]!r}") from exc

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Task":
        """Accept a Supabase webhook/realtime payload ({"record": {...}}) or a bare record."""
        record = payload.get("record", payload)
        if not isinstance(record, Mapping):
            raise ValueError("Payload has no task record")
        return cls.from_record(record)


@dataclass(frozen=True)
class Date:
    year: int
    month: int | None = None

    @classmethod
    def parse(cls, raw: Mapping[str, Any] | None) -> "Date | None":
        if not raw or not raw.get("year"):
            return None
        return cls(year=int(raw["year"]), month=int(raw["month"]) if raw.get("month") else None)

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d}" if self.month else str(self.year)


def _span(start: Date | None, end: Date | None) -> str:
    if not start:
        return ""
    return f"{start} to {end or 'present'}"


@dataclass(frozen=True)
class Experience:
    title: str
    company: str
    start: Date | None = None
    end: Date | None = None
    location: str = ""
    description: str = ""


@dataclass(frozen=True)
class Education:
    school: str
    degree: str = ""
    field_of_study: str = ""
    start: Date | None = None
    end: Date | None = None


@dataclass(frozen=True)
class Certification:
    name: str
    start: Date | None = None


@dataclass(frozen=True)
class Profile:
    full_name: str = ""
    headline: str = ""
    occupation: str = ""
    summary: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    experiences: tuple[Experience, ...] = field(default_factory=tuple)
    education: tuple[Education, ...] = field(default_factory=tuple)
    certifications: tuple[Certification, ...] = field(default_factory=tuple)

    @classmethod
    def from_proxycurl(cls, data: Mapping[str, Any]) -> "Profile":
        s = lambda v: (v or "").strip() if isinstance(v, str) else ""
        return cls(
            full_name=s(data.get("full_name")),
            headline=s(data.get("headline")),
            occupation=s(data.get("occupation")),
            summary=s(data.get("summary")),
            city=s(data.get("city")),
            state=s(data.get("state")),
            country=s(data.get("country_full_name") or data.get("country")),
            experiences=tuple(
                Experience(title=s(e.get("title")), company=s(e.get("company")),
                           start=Date.parse(e.get("starts_at")), end=Date.parse(e.get("ends_at")),
                           location=s(e.get("location")), description=s(e.get("description")))
                for e in data.get("experiences") or []
            ),
            education=tuple(
                Education(school=s(e.get("school")), degree=s(e.get("degree_name")),
                          field_of_study=s(e.get("field_of_study")),
                          start=Date.parse(e.get("starts_at")), end=Date.parse(e.get("ends_at")))
                for e in data.get("education") or []
            ),
            certifications=tuple(
                Certification(name=s(c.get("name")), start=Date.parse(c.get("starts_at")))
                for c in data.get("certifications") or [] if c.get("name")
            ),
        )

    def to_prompt_text(self) -> str:
        """Compact, labelled text the LLM writes from. Empty fields are omitted."""
        lines: list[str] = []

        def add(label: str, value: str) -> None:
            if value:
                lines.append(f"{label}: {value}")

        add("Headline", self.headline)
        add("Occupation", self.occupation)
        add("Location", ", ".join(p for p in (self.city, self.state, self.country) if p))
        add("Summary", self.summary)
        if self.experiences:
            lines.append("Experience:")
            for e in self.experiences:
                where = " at ".join(p for p in (e.title, e.company) if p)
                extra = "; ".join(p for p in (_span(e.start, e.end), e.location, e.description) if p)
                lines.append(f"  - {where}" + (f" ({extra})" if extra else ""))
        if self.education:
            lines.append("Education:")
            for ed in self.education:
                what = ", ".join(p for p in (ed.degree, ed.field_of_study) if p)
                span = _span(ed.start, ed.end)
                lines.append(f"  - {ed.school}" + (f": {what}" if what else "") + (f" ({span})" if span else ""))
        if self.certifications:
            lines.append("Certifications: " + ", ".join(c.name for c in self.certifications))
        return "\n".join(lines)
