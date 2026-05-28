"""StreamFit extraction pipeline.

Reads each file in `../interactions/`, sends it through the LLM with the
system prompt at `prompts/system.md`, validates the response against
`schema.py`, and writes:

- raw model output     -> `outputs/raw/<id>.txt`
- validated JSON       -> `outputs/structured/<id>.json`
- validation failures  -> `outputs/errors/<id>.json`

Designed for two execution modes:

1. **API mode** (default if `ANTHROPIC_API_KEY` is set) — calls the
   Anthropic SDK directly. Use this at scale.
2. **Manual mode** (no API key) — emits the assembled prompt for each
   interaction to stdout so a human can paste it into the Claude.ai web UI
   and drop the response into `outputs/raw/<id>.txt`. The pipeline then
   re-validates from disk on subsequent runs.

Usage:
    python pipeline.py                       # process all interactions
    python pipeline.py SF-2026-0001          # process a single interaction
    python pipeline.py --validate-only       # re-validate existing raw outputs
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from schema import ExtractedInteraction

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
INTERACTIONS_DIR = PROJECT / "interactions"
RAW_DIR = ROOT / "outputs" / "raw"
STRUCTURED_DIR = ROOT / "outputs" / "structured"
ERRORS_DIR = ROOT / "outputs" / "errors"
PROMPT_DIR = ROOT / "prompts"

MODEL = "claude-sonnet-4-6"  # tier-A: swap for haiku at scale; sonnet for the demo


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_system_prompt() -> str:
    return (PROMPT_DIR / "system.md").read_text()


def load_user_template() -> str:
    return (PROMPT_DIR / "user_template.md").read_text()


def build_user_message(interaction_id: str, channel: str, raw_text: str) -> str:
    template = load_user_template()
    # The template file is documentation; the actual block we send is the
    # code-fenced section.
    body = template.split("```")[1].strip("\n")
    return (
        body.replace("{{interaction_id}}", interaction_id)
        .replace("{{channel}}", channel)
        .replace("{{raw_text}}", raw_text)
    )


def detect_channel(raw_text: str) -> str:
    m = re.search(r"^CHANNEL:\s*(\S+)", raw_text, flags=re.MULTILINE)
    if not m:
        return "phone"
    value = m.group(1).strip().lower()
    return {"phone": "phone", "live": "live_chat", "live_chat": "live_chat", "email": "email"}.get(
        value, "phone"
    )


def extract_json(response_text: str) -> dict:
    """Robust JSON extractor for models that occasionally wrap output."""
    text = response_text.strip()
    # Strip code fences if present.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    # Trim to outermost braces in case prose leaked.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in model output")
    return json.loads(text[start : end + 1])


def verify_quotes_in_source(parsed: dict, source: str) -> list[str]:
    """Return any verbatim_quote values that don't appear in the source.

    Cheap hallucination check — runs no extra model calls.
    """
    failures = []
    for pp in parsed.get("insights", {}).get("pain_points", []) or []:
        quote = pp.get("verbatim_quote")
        if quote and quote not in source:
            failures.append(quote)
    return failures


# ---------------------------------------------------------------------------
# LLM call (API mode)
# ---------------------------------------------------------------------------


def call_llm(system_prompt: str, user_message: str) -> str:
    """Return raw model output. Requires ANTHROPIC_API_KEY in env."""
    from anthropic import Anthropic

    client = Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )
    return msg.content[0].text


# ---------------------------------------------------------------------------
# Per-interaction processing
# ---------------------------------------------------------------------------


def process(interaction_path: Path, mode: str) -> Optional[ExtractedInteraction]:
    interaction_id = interaction_path.stem
    raw_text = interaction_path.read_text()
    channel = detect_channel(raw_text)
    user_message = build_user_message(interaction_id, channel, raw_text)

    raw_path = RAW_DIR / f"{interaction_id}.txt"
    structured_path = STRUCTURED_DIR / f"{interaction_id}.json"
    error_path = ERRORS_DIR / f"{interaction_id}.json"

    if mode == "api":
        system_prompt = load_system_prompt()
        try:
            response_text = call_llm(system_prompt, user_message)
        except Exception as e:  # noqa: BLE001
            error_path.write_text(json.dumps({"error": f"LLM call failed: {e}"}, indent=2))
            return None
        raw_path.write_text(response_text)
    elif mode == "validate":
        if not raw_path.exists():
            print(f"[skip] no raw output for {interaction_id}")
            return None
        response_text = raw_path.read_text()
    else:
        raise ValueError(f"unknown mode: {mode}")

    try:
        parsed = extract_json(response_text)
    except (ValueError, json.JSONDecodeError) as e:
        error_path.write_text(json.dumps({"error": f"JSON parse failed: {e}"}, indent=2))
        return None

    quote_failures = verify_quotes_in_source(parsed, raw_text)
    if quote_failures:
        # Hallucinated quotes -> flag but still validate; the validator can
        # bump confidence down. In production this would trigger a retry.
        parsed.setdefault("quality_flags", {})
        parsed["quality_flags"].setdefault("review_reasons", []).extend(
            [f"verbatim_quote not found in source: {q[:60]}..." for q in quote_failures]
        )
        parsed["quality_flags"]["requires_human_review"] = True

    try:
        validated = ExtractedInteraction.model_validate(parsed)
    except ValidationError as e:
        error_path.write_text(
            json.dumps({"error": "schema validation failed", "detail": e.errors()}, indent=2)
        )
        return None

    structured_path.write_text(validated.model_dump_json(indent=2))
    return validated


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("interaction_id", nargs="?")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="re-parse existing raw/*.txt files; do not call the LLM",
    )
    args = parser.parse_args()

    for d in (RAW_DIR, STRUCTURED_DIR, ERRORS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    if args.validate_only:
        mode = "validate"
    elif os.environ.get("ANTHROPIC_API_KEY"):
        mode = "api"
    else:
        print(
            "ANTHROPIC_API_KEY not set. Run with --validate-only to "
            "re-validate raw outputs that were produced manually.",
            file=sys.stderr,
        )
        return 2

    if args.interaction_id:
        paths = [INTERACTIONS_DIR / f"{args.interaction_id}.txt"]
    else:
        paths = sorted(INTERACTIONS_DIR.glob("SF-*.txt"))

    ok = 0
    skipped = 0
    fail = 0
    for p in paths:
        if not p.exists():
            print(f"[missing] {p.name}")
            fail += 1
            continue
        # In validate-only mode, an interaction with no raw output isn't a
        # failure — it just wasn't extracted yet. Skip silently.
        if mode == "validate" and not (RAW_DIR / f"{p.stem}.txt").exists():
            skipped += 1
            continue
        result = process(p, mode=mode)
        if result is not None:
            print(f"[ok]   {p.stem}")
            ok += 1
        else:
            print(f"[fail] {p.stem}")
            fail += 1

    summary = f"\n{ok} ok, {fail} fail"
    if skipped:
        summary += f", {skipped} not extracted"
    print(summary)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
