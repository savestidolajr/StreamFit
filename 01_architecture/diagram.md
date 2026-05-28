# Diagram source notes

The architecture diagram referenced by `ARCHITECTURE.md` exists as:

- `diagram.png` — exported PNG for embedding in the README and the
  presentation slide deck.
- `diagram.excalidraw` — editable source so the diagram can be modified
  live during Q&A if a reviewer wants to challenge a specific edge.

A faithful ASCII fallback is embedded inside `ARCHITECTURE.md` itself so the
document is useful when read on a phone or in a terminal.

## What the diagram depicts

Single-page left-to-right swimlane:

1. **Sources column** — phone recording, live chat log, email inbox.
2. **S3 landing zone**, fanning out into SQS.
3. **Pre-processing band** — ASR / PII redaction / normalisation into a
   uniform interaction JSON.
4. **Extractor lane** — Tier-A (Haiku) is the default path. Validator
   gates output. Tier-B (Sonnet) handles failures and low-confidence
   cases. HITL queue is the final fallback.
5. **Storage** — Postgres (operational) + Snowflake (analytical), both fed
   by the same writer.
6. **Consumption** — dbt models → BI dashboards + weekly digest.

Side annotations on the diagram:

- Prompt caching marker on the extractor's system message.
- Golden-set evaluation loop pointing into Tier A from a "fixtures" box.
- DLQ pointing back into Tier B from the validator on retry exhaustion.

A whiteboard photo would convey the same content and is explicitly accepted
by the brief. If the editable source file is missing on review, treat the
ASCII block in `ARCHITECTURE.md` as the source of truth.
