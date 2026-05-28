# Extraction Run Log

## Summary

8 of 24 interactions processed through the extraction pipeline for the demo.
Chosen to span every channel (phone, live_chat, email) and every interaction
`type` enum we expect at scale.

| Interaction | Channel | Type | Notes |
|---|---|---|---|
| SF-2026-0001 | phone | cancellation | Long-tenure save with loyalty discount |
| SF-2026-0002 | phone | complaint | Billing double-charge |
| SF-2026-0010 | live_chat | general_inquiry | Positive feedback + 4 feature requests |
| SF-2026-0017 | email | complaint | Escalation of unresolved refund |
| SF-2026-0021 | phone | support_request | Noisy audio, Samsung TV app crash |
| SF-2026-0022 | phone | cancellation | Three stacked dealbreakers, retained conditionally |
| SF-2026-0023 | phone | complaint | Cancellation never propagated to billing |
| SF-2026-0024 | phone | general_inquiry | Privacy and AI-data inquiry |

## Verification command + output

```
$ .venv/bin/python 02_extraction/pipeline.py --validate-only

[ok]   SF-2026-0001
[ok]   SF-2026-0002
[ok]   SF-2026-0010
[ok]   SF-2026-0017
[ok]   SF-2026-0021
[ok]   SF-2026-0022
[ok]   SF-2026-0023
[ok]   SF-2026-0024

8 ok, 0 fail, 16 not extracted
```

All 8 raw outputs parsed cleanly as JSON, validated against the Pydantic
schema in `schema.py`, and passed the `verbatim_quote` substring check (no
hallucinated quotes). The `16 not extracted` line refers to interactions
deliberately left for the at-scale run.

## At-scale path

With `ANTHROPIC_API_KEY` exported, removing `--validate-only` causes
`pipeline.py` to call the Anthropic API for every interaction in
`interactions/` that lacks a raw output. The same validation gate runs after
each call. See `pipeline.py:call_llm` for the API integration including
prompt caching on the system message.

## Why we did not extract all 24 for the demo

Time was deliberately spent on:

1. Designing the prompt so it is robust to noisy inputs (verified on
   SF-2026-0021 — the file with `[inaudible]` markers).
2. Building the validation harness with the verbatim-quote substring check
   (cheapest hallucination guard available).
3. Picking eight interactions covering every channel and every type, so the
   analysis is forced to surface variety rather than a single dominant
   pattern.

A reviewer wanting to extend the run can export an API key, remove the eight
existing raw outputs they want to re-do, and re-run without
`--validate-only`.
