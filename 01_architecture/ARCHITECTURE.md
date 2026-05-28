# StreamFit Insight Pipeline — Architecture

**Goal.** Convert raw customer interactions (phone, chat, email) into
structured insights at a volume of 10,000+ interactions per month, with
cost, quality, and operability characteristics suitable for a production
system at a ~50,000-subscriber business.

The demo in this repo is the leftmost two stages of this diagram running
locally on eight interactions. Everything else is the same code path with
queues, retries, and storage attached.

---

## Diagram

See `diagram.png` (also `diagram.excalidraw` for an editable source).
ASCII fallback below for reviewers reading on a phone:

```
                                  ┌───────────────────────────────┐
   ┌──────────┐                   │  Tier-A extractor (Haiku 4.5) │
   │ Phone    │───┐               │  - prompt cache on system msg │
   │ recording│   │               │  - JSON-only output           │
   └──────────┘   │  ┌─────────┐  └──────────────┬────────────────┘
                  ├─▶│ S3 raw  │                 │
   ┌──────────┐   │  │ landing │     ┌───────────▼───────────┐
   │ Live chat│───┤  └────┬────┘     │  Pydantic validator   │
   │ logs     │   │       │          │  + verbatim_quote     │
   └──────────┘   │       ▼          │    substring check    │
                  │ ┌──────────────┐ └───────────┬───────────┘
   ┌──────────┐   │ │Pre-processing│             │
   │ Email    │───┘ │ ASR (Whisper │             │ confidence?
   │ inbox    │     │   / Transc.) │   ┌─────────┴────────┐
   └──────────┘     │ PII redaction│   │ high             │ low / fail
                    │ Normalise →  │   ▼                  ▼
                    │ uniform JSON │ ┌────────────┐  ┌────────────────┐
                    └──────┬───────┘ │ Postgres + │  │ Tier-B retry   │
                           │         │ Snowflake  │  │ (Sonnet 4.6)   │
                       ┌───▼────┐    └──────┬─────┘  └────────┬───────┘
                       │  SQS   │           │                 │
                       └───┬────┘           │                 ▼
                           │                │         ┌──────────────┐
                           ▼                │         │ HITL queue   │
                  to extractor              │         │ (analyst UI) │
                                            ▼         └──────────────┘
                                  ┌──────────────────┐
                                  │ dbt models →     │
                                  │ BI / dashboards  │
                                  │ + weekly digest  │
                                  └──────────────────┘
```

---

## Stages

### 1. Ingestion

Three source types land in S3 under partitioned prefixes:

- `s3://streamfit-raw/phone/{yyyy}/{mm}/{dd}/...` — call recordings (raw
  audio) plus a small JSON sidecar with agent name, call duration, and any
  CRM context.
- `s3://streamfit-raw/chat/{yyyy}/{mm}/{dd}/...` — chat transcripts as
  JSON-Lines (one turn per line).
- `s3://streamfit-raw/email/{yyyy}/{mm}/{dd}/...` — RFC-822 emails.

A landing-zone event (EventBridge) fans out one SQS message per
interaction. Each downstream stage consumes from SQS, so scaling and
back-pressure are independent per stage.

**Cost note.** Raw archive is retained 90+ days so that prompt or schema
changes can be back-applied by replaying the SQS queue without re-paying
ASR.

### 2. Pre-processing

The job of this stage is to deliver a uniform "normalised interaction"
object to the extractor regardless of channel. Same shape as the demo
inputs in `interactions/`, but produced from arbitrary sources:

```json
{
  "interaction_id": "SF-2026-0001",
  "channel": "phone | live_chat | email",
  "timestamp": "ISO-8601",
  "agent_name": "...",
  "duration_seconds": 702,
  "segments": [
    {"speaker": "agent", "text": "...", "ts": "00:00:03"},
    {"speaker": "customer", "text": "...", "ts": "00:00:07"}
  ],
  "source_metadata": { ... }
}
```

- **Phone** — AWS Transcribe (or Whisper via Bedrock / Deepgram) with
  speaker diarisation. Quality markers (`[inaudible]`, `[background noise]`)
  preserved so the extractor can lower its confidence appropriately —
  validated on SF-2026-0021.
- **Chat** — strip system messages, merge consecutive turns by the same
  speaker, attach wall-clock timestamps.
- **Email** — `talon` or `mailparser` to strip signatures and quoted reply
  chains; treat the most recent customer message as the primary signal.

**PII redaction** runs here, before any LLM call: AWS Comprehend PII or
Microsoft Presidio over the normalised text, replacing emails, phone
numbers, account numbers, and credit-card-like patterns with typed
placeholders. This shortens prompts (cost) and reduces compliance surface
(legal).

### 3. Extraction

Stateless per-interaction LLM call. The prompt lives in
`02_extraction/prompts/system.md` and is unchanged between dev and prod.

**Tiered model routing.**

| Tier | Model | When invoked | Approx unit cost |
|---|---|---|---|
| A | Claude Haiku 4.5 | Default — clean interactions, default routing | ~$0.001 per interaction |
| B | Claude Sonnet 4.6 | Validation failure, low self-confidence, long inputs (>30k chars), or noisy quality markers detected | ~$0.015 per interaction |
| C | Claude Opus 4.7 | Golden-set spot checks only; never production traffic | n/a |

Prompt caching is applied to the system prompt (≈3k tokens). At Haiku
prices with cache hits, the steady-state extraction cost for 10k
interactions/month is **roughly $5–15/month** in token spend. The
engineering effort is the real cost line, not the LLM.

**Concurrency.** SQS-driven worker pool. Lambda for spiky load; ECS/Fargate
for steady throughput. 10k/month ≈ 333/day — trivial. The architecture is
sized for 10× headroom so seasonal spikes (e.g. January resolution
churn) don't require scaling work.

**Idempotency.** Each message carries `interaction_id`; consumer checks for
an existing structured output before doing work. Re-runs are safe.

### 4. Validation and quality control

Three checks per extraction, all of them implemented locally in `pipeline.py`
and exposed in the demo:

1. **JSON parse.** If the model wraps its output, the extractor trims the
   first `{` to the last `}` before parsing.
2. **Pydantic validation** against the Literal-typed schema in `schema.py`.
   Hallucinated enum values fail here immediately.
3. **`verbatim_quote` substring check.** Every `pain_points[].verbatim_quote`
   must be a substring of the source interaction text. This is the
   cheapest hallucination guard in the system — no extra model call.

**Confidence routing.** Each extraction self-reports
`quality_flags.extraction_confidence`. The router uses this to send `low`
results back through Tier B before storing.

**Golden-set evaluation.** 50 hand-labelled interactions are re-extracted on
every prompt or model version change. Field-level precision/recall is
tracked; a regression > 5pp on any field blocks the prompt change.

**Human-in-the-loop queue.** Anything still failing after Tier B
(`requires_human_review=true`) goes to a small Streamlit / Retool app
where a CS analyst can correct fields, with corrections feeding the
golden set. Estimated 5–10% of traffic at maturity.

### 5. Storage

Two stores, populated from the same writer:

- **Postgres (RDS)** — operational reads. One row per interaction with the
  full structured JSON in a `jsonb` column plus a small number of
  promoted columns (`interaction_id`, `customer_id` if linkable,
  `churn_risk`, `lifecycle_stage`, `created_at`) for indexing and the
  agent-tooling reads.
- **Snowflake / BigQuery / DuckDB** — analytics. Daily batch loaded from
  Postgres. dbt models materialise the views the BI dashboards point at.

**Raw archive** in S3 is retained for ≥90 days alongside the structured
output. If the schema changes, the SQS queue is replayed against the new
prompt; no source data is ever re-collected.

### 6. Analysis and consumption

- **dbt models** aggregate to the views that answer the three leadership
  questions: churn-driver mix over time, segment cohorts by lifecycle ×
  plan × dominant pain category, impact-vs-effort ranking with engineering
  effort estimates joined in.
- **Dashboards** in Metabase / Superset / Hex — one per leadership
  question.
- **Weekly digest** — a small LLM job summarises the prior week's
  structured data into a one-page brief that goes to product, CS, and
  exec leadership. (This is the same prompt-engineering pattern as
  extraction, just over aggregated data rather than raw text.)

---

## Cost management

The single highest-leverage cost control is **tiered model routing**.
Always-Sonnet would cost ~10× more than the Haiku-first approach. Other
levers:

- **Prompt caching** on the ~3k-token system message — cuts input tokens
  ~90% on repeated calls.
- **PII redaction** shortens prompts before the LLM ever sees them.
- **Batch API** (Anthropic) for non-time-sensitive backfills — 50%
  discount.
- **Idempotency** — re-running the pipeline does not re-pay for already
  processed work.

For 10k/month at the Haiku rate with caching, steady-state LLM spend is on
the order of **$5–15/month**. The dominant cost in the system is people
time (engineering, analyst review), not tokens.

---

## Quality and accuracy

- **Schema validation** at the boundary — Pydantic Literal types catch
  invented enum values immediately.
- **`verbatim_quote` substring check** — catches fabricated complaints
  with zero extra model calls. Demonstrated in `pipeline.py:verify_quotes_in_source`.
- **Self-reported confidence + Tier-B retry** — extractions where the
  model is unsure get escalated automatically.
- **Golden-set evaluation** — every prompt or model change is gated by a
  rerun against 50 hand-labelled fixtures; field-level precision/recall is
  tracked over time.
- **HITL queue** — the safety net for the ~5–10% the system can't handle
  alone. Analyst corrections feed back into the golden set, improving the
  baseline over time.

---

## Error handling

| Failure | Response |
|---|---|
| LLM transient error | Exponential backoff, 3 retries |
| JSON parse failure | One retry with the parse error appended to the prompt |
| Pydantic validation failure | One retry with the field error appended; if still failing, send to Tier B |
| Tier B also failing | Write to dead-letter queue + HITL queue |
| Source data unprocessable (corrupt audio, empty email) | Mark `unprocessable`, log reason, surface count on dashboard |
| Schema or prompt changes | Output tagged with `schema_version` + `prompt_version`; replay S3 archive through new pipeline |

---

## Edge cases worth calling out

- **Multi-language interactions** — language detection in pre-processing
  routes to a translation step or a multilingual model variant.
- **Multi-issue interactions** — schema explicitly allows arrays for
  `pain_points`, `feature_requests`, etc. Don't force one.
- **Anonymous interactions** — extract anyway, just can't join to
  subscriber data. The lifecycle stage falls back to `unknown`.
- **Very long calls (>15 min / >30k chars)** — chunk + map-reduce
  summarise before extraction.
- **Noisy or low-quality source** — the demo's SF-2026-0021 is the
  reference case. `quality_flags.interaction_quality = significant_gaps`
  + `requires_human_review = true` triggers the HITL queue automatically.

---

## What this design buys at the assessment level vs. production

| Assessment-grade shortcut | What production requires |
|---|---|
| Single tier (Sonnet via demo) | Haiku → Sonnet → human tiered routing |
| Pydantic validation + one retry | Full validation framework + DLQ + golden-set eval |
| No PII redaction | Mandatory pre-LLM PII scrub |
| 8 interactions hand-run | SQS worker pool, 10k+/month, auto-scaled |
| pandas in a notebook | dbt models in warehouse, daily refresh |
| Confidence self-reported by model | Calibrated confidence + HITL queue |
| No multilingual handling | Language detection + routed translation |
| Hand-keyed effort estimates in `insights.py` | Effort joined from engineering planning tool |

The schema and the prompts are identical between the two columns. Only the
infrastructure around them changes.
