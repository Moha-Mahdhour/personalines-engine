"""Prompt templates and chat-message construction.

string.Template is used instead of str.format because profile text often
contains braces (JSON fragments, code in bios) that would break format().
"""
from __future__ import annotations

from string import Template

SYSTEM_PROMPT = (
    "You write short, personalized opening lines for outreach emails. "
    "Write about one specific, interesting thing about the prospect in at most two sentences. "
    "Never mention the prospect's name."
)

USER_TEMPLATE = Template("""\
Write one opening line in the style of these examples. Match the tone; never reuse their content.

$examples

Rules:
- Write to the prospect directly, but never use their name.
- Pick one specific thing about their life or career and mention it. Not their connections.
- Sound human, casual, and genuinely interested.
- Do not mention websites.
- Keep it under $max_words words.

Prospect profile:
$profile""")

MAX_PROFILE_CHARS = 10_000
MAX_WORDS = 25


def build_messages(profile_text: str, examples_block: str, *,
                   max_profile_chars: int = MAX_PROFILE_CHARS, max_words: int = MAX_WORDS) -> list[dict[str, str]]:
    """Chat messages for one lead. Long profiles are truncated to keep requests bounded."""
    if len(profile_text) > max_profile_chars:
        profile_text = profile_text[:max_profile_chars].rstrip() + " ..."
    user = USER_TEMPLATE.substitute(examples=examples_block.strip(), profile=profile_text.strip(), max_words=max_words)
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def clean_completion(text: str) -> str:
    """Normalize model output: trim whitespace and a wrapping pair of quotes."""
    text = (text or "").strip()
    for q in ('"', "'", "“”"):
        opener, closer = (q[0], q[-1])
        if len(text) >= 2 and text[0] == opener and text[-1] == closer:
            text = text[1:-1].strip()
    return text
