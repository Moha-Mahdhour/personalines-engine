"""Profile enrichment: LinkedIn URL in, profile JSON out.

Results are aligned with the input list; a lead that cannot be enriched
gets None rather than failing the whole batch. Invalid URLs are filtered
before any paid API call is made.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Mapping, Protocol, Sequence

ProfileData = Mapping[str, Any]

_LINKEDIN_PROFILE = re.compile(r"^(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[^/?#\s]+/?", re.IGNORECASE)


def normalize_linkedin_url(raw: str | None) -> str | None:
    """Canonical https URL for a LinkedIn profile, or None if it is not one."""
    if not raw:
        return None
    raw = raw.strip()
    match = _LINKEDIN_PROFILE.match(raw)
    if not match:
        return None
    url = match.group(0).rstrip("/")
    return url if url.lower().startswith("http") else "https://" + url


class Enricher(Protocol):
    def enrich(self, urls: Sequence[str | None]) -> list[ProfileData | None]: ...


class StaticEnricher:
    """Looks profiles up in a dict. Used by tests and offline demos."""

    def __init__(self, profiles: Mapping[str, ProfileData]) -> None:
        self.profiles = {normalize_linkedin_url(k): v for k, v in profiles.items()}
        self.requested: list[str] = []

    def enrich(self, urls: Sequence[str | None]) -> list[ProfileData | None]:
        out: list[ProfileData | None] = []
        for raw in urls:
            url = normalize_linkedin_url(raw)
            if url:
                self.requested.append(url)
            out.append(self.profiles.get(url) if url else None)
        return out


class ProxycurlEnricher:
    """Bulk, async lookups through the Proxycurl SDK (optional 'enrichment' extra)."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("PROXYCURL_SECRET is not set")
        self._api_key = api_key

    def enrich(self, urls: Sequence[str | None]) -> list[ProfileData | None]:
        normalized = [normalize_linkedin_url(u) for u in urls]
        wanted = [(i, u) for i, u in enumerate(normalized) if u]
        results: list[ProfileData | None] = [None] * len(urls)
        if not wanted:
            return results          # nothing billable to look up
        try:
            from proxycurl.asyncio import Proxycurl, do_bulk
        except ImportError as exc:
            raise RuntimeError("Install the 'enrichment' extra: pip install '.[enrichment]'") from exc
        client = Proxycurl(api_key=self._api_key)
        calls = [(client.linkedin.person.get, {"linkedin_profile_url": u}) for _, u in wanted]
        for (i, _), res in zip(wanted, asyncio.run(do_bulk(calls))):
            if getattr(res, "success", False):
                results[i] = res.value
        return results
