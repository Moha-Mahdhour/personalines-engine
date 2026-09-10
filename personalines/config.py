"""Runtime settings, read once from the environment.

Everything the engine needs is declared here, so a missing or malformed
variable fails at startup with a clear message instead of deep inside a
worker thread.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


class ConfigError(RuntimeError):
    """Raised when required settings are missing or invalid."""


def _load_dotenv(path: str = ".env") -> None:
    """Load a .env file if python-dotenv is installed; otherwise do nothing."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(dotenv_path=path)


def _int(env: Mapping[str, str], name: str, default: int, minimum: int = 1) -> int:
    raw = env.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}, got {value}")
    return value


def _float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw in (None, ""):
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    supabase_url: str = ""
    supabase_key: str = ""
    proxycurl_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 1.0
    storage_bucket: str = "Users"
    tasks_table: str = "tasks"
    work_dir: Path = field(default_factory=lambda: Path("Filing"))
    max_concurrency: int = 8
    examples_per_prompt: int = 7
    request_timeout: float = 20.0
    max_retries: int = 5
    webhook_port: int = 10000

    @property
    def supabase_project_id(self) -> str:
        """Project ref derived from SUPABASE_URL (https://<ref>.supabase.co)."""
        host = urlparse(self.supabase_url).hostname or ""
        return host.split(".")[0] if host.endswith(".supabase.co") else ""

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, *, dotenv: bool = True) -> "Settings":
        if env is None:
            if dotenv:
                _load_dotenv()
            env = os.environ
        return cls(
            supabase_url=env.get("SUPABASE_URL", ""),
            supabase_key=env.get("SUPABASE_SECRET", ""),
            proxycurl_key=env.get("PROXYCURL_SECRET", ""),
            openai_api_key=env.get("OPENAI_API_KEY", ""),
            openai_model=env.get("OPENAI_MODEL") or cls.openai_model,
            openai_temperature=_float(env, "OPENAI_TEMPERATURE", cls.openai_temperature),
            storage_bucket=env.get("STORAGE_BUCKET") or cls.storage_bucket,
            tasks_table=env.get("TASKS_TABLE") or cls.tasks_table,
            work_dir=Path(env.get("WORK_DIR") or "Filing"),
            max_concurrency=_int(env, "MAX_CONCURRENCY", cls.max_concurrency),
            examples_per_prompt=_int(env, "EXAMPLES_PER_PROMPT", cls.examples_per_prompt),
            request_timeout=_float(env, "REQUEST_TIMEOUT", cls.request_timeout),
            max_retries=_int(env, "MAX_RETRIES", cls.max_retries, minimum=0),
            webhook_port=_int(env, "PORT", cls.webhook_port),
        )

    def require(self, *fields: str) -> "Settings":
        """Fail fast if any of the named settings are empty."""
        env_names = {
            "supabase_url": "SUPABASE_URL",
            "supabase_key": "SUPABASE_SECRET",
            "proxycurl_key": "PROXYCURL_SECRET",
            "openai_api_key": "OPENAI_API_KEY",
        }
        missing = [env_names.get(f, f) for f in fields if not getattr(self, f)]
        if missing:
            raise ConfigError("Missing required settings: " + ", ".join(missing) + " (see .env.example)")
        return self
