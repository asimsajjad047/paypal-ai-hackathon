"""
One small wrapper around the Claude API, used by every AI feature.

ask_json()  -> Claude must reply in a fixed shape (a Pydantic model), so our
               Python code can trust the fields. Returns None if AI is off or
               anything goes wrong, and the caller then uses its offline rules.
ask_text()  -> a normal written answer (explanations). Also None on failure.

Why None instead of crashing? A live demo must never die because of a network
blip or a missing key. Every caller has a plain-code fallback.
"""
import logging

import anthropic

import config

log = logging.getLogger("rigagent.ai")

_client = None


def _get_client():
    global _client
    if _client is None:
        # pass the key explicitly (same lesson as the Channel3 SDK)
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=60.0)
    return _client


def ask_json(system, prompt, schema, max_tokens=4000):
    """Ask Claude for structured output matching `schema` (a Pydantic class)."""
    if not config.AI_ENABLED:
        return None
    try:
        response = _get_client().messages.parse(
            model=config.AI_MODEL,
            max_tokens=max_tokens,
            output_config={"effort": config.AI_EFFORT},
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
        if response.stop_reason == "refusal":
            log.warning("Claude declined the request; using offline rules")
            return None
        return response.parsed_output
    except (anthropic.APIError, ValueError) as e:
        log.warning("AI call failed (%s); using offline rules", e)
        return None


def ask_text(system, prompt, max_tokens=4000):
    """Ask Claude for a plain-text (Markdown) answer."""
    if not config.AI_ENABLED:
        return None
    try:
        response = _get_client().messages.create(
            model=config.AI_MODEL,
            max_tokens=max_tokens,
            output_config={"effort": config.AI_EFFORT},
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            return None
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return text or None
    except anthropic.APIError as e:
        log.warning("AI call failed (%s); using offline text", e)
        return None
