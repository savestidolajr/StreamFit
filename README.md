# StreamFit — Customer Interaction Insight Pipeline

Take-home assessment for the Data & AI Builder role. Pipeline that converts
raw customer-service interactions into structured insights answering three
leadership questions about churn, segments, and product priorities.

## Read in this order (matches presentation order)

1. [`01_architecture/ARCHITECTURE.md`](01_architecture/ARCHITECTURE.md) — pipeline design at scale (10k+/month). Most important deliverable. See also [`01_architecture/diagram.md`](01_architecture/diagram.md).
2. [`02_extraction/`](02_extraction/) — working pipeline.
   - [`pipeline.py`](02_extraction/pipeline.py) — runnable entry point.
   - [`schema.py`](02_extraction/schema.py) — Pydantic translation of `TARGET_SCHEMA.json`.
   - [`prompts/system.md`](02_extraction/prompts/system.md) — extraction prompt.
   - [`prompts/README.md`](02_extraction/prompts/README.md) — prompt design rationale.
   - [`outputs/raw/`](02_extraction/outputs/raw/) — raw LLM outputs.
   - [`outputs/structured/`](02_extraction/outputs/structured/) — validated JSON.
   - [`run_log.md`](02_extraction/run_log.md) — verification command and result.
3. [`03_analysis/insights.md`](03_analysis/insights.md) — answers to the three business questions, computed from the structured extractions by [`insights.py`](03_analysis/insights.py). Charts in [`charts/`](03_analysis/charts/).
4. [`04_ai_workflow/README.md`](04_ai_workflow/README.md) — how AI tools were used during the build; see also [`prompt_evolution.md`](04_ai_workflow/prompt_evolution.md).

## What was processed

8 of 24 interactions, deliberately chosen to span every channel (phone,
live_chat, email) and every `type` enum (cancellation, complaint,
general_inquiry, support_request). Quality > completeness, per the brief.
See [`02_extraction/run_log.md`](02_extraction/run_log.md) for the list and
the verification command output.

## Running it

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# Re-validate the existing raw outputs (no API key needed):
.venv/bin/python 02_extraction/pipeline.py --validate-only

# Run the analysis (produces CSV + charts under 03_analysis/):
.venv/bin/python 03_analysis/insights.py

# Extract more interactions via the Anthropic API:
export ANTHROPIC_API_KEY=...
.venv/bin/python 02_extraction/pipeline.py
```

## Inputs (provided)

- [`interactions/`](interactions/) — 24 raw customer interactions.
- [`TARGET_SCHEMA.json`](TARGET_SCHEMA.json) — target output schema.

## Headline findings (from `insights.md`)

- **Billing system propagation reliability is the #1 priority by impact /
  effort.** Three of eight interactions trace back to this single bug
  class; engineering work is bounded.
- **Long-tenure Premium customers citing "stale catalogue + specific
  trainer/content gap" are the highest-risk retention cohort.** Both
  examples in this sample (0001, 0022) were retained conditionally with
  April re-evaluation deadlines — a measurable follow-up cohort.
- **Best upsell archetype** in this sample is the active Premium yoga
  power-user who already pays separately for meditation — verbatim
  "id literally pay more for that" signal for a wellness bundle.

Numbers above are derived from 8 interactions and are for methodology
demonstration; production-scale conclusions need the full month's volume.
