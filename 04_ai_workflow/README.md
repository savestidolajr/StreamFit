# AI Workflow Evidence

How AI tools were used to build this assessment — what worked, what didn't,
and what I overrode.

## Tools used

| Tool | Used for |
|---|---|
| **Claude Code (CLI / VSCode extension)** | Whole-session orchestration: scaffolding folder structure, writing the Pydantic schema, drafting the system prompt, running the validation pipeline against the eight extractions, building the analysis script. |
| **Claude (anthropic SDK / pipeline)** | The pipeline calls Claude in production mode. For this demo run, the same prompt was executed in the orchestrating session as a stand-in (no API key required), producing the eight `outputs/raw/*.txt` files. |
| **Local Python (`.venv`)** | Pydantic for schema validation, pandas + matplotlib for analysis charts. No LLM in this layer — deterministic code. |

## How I worked with the tools

1. **Read the brief once, end-to-end, before touching code.** I asked the
   planning agent to produce a written implementation plan against the
   brief verbatim (see top of `04_ai_workflow/transcripts/`) and used that
   plan as the spine of the build. Reviewing the plan before agreeing to
   execute it saved at least one full restart — the plan flagged that the
   architecture write-up is judged most important and made me weight the
   diagram and the write-up higher than I would have by instinct.
2. **Schema first, prompt second.** Translating `TARGET_SCHEMA.json` into
   `schema.py` was the first concrete step. Doing this before the prompt
   was deliberate — the model can be told to emit any shape, but the
   Pydantic `Literal` types are what actually catches drift later.
3. **Hand-validated the first extraction against the source.** SF-2026-0001
   was extracted, then I walked the JSON back through the source
   transcript line-by-line confirming every `verbatim_quote` was an actual
   substring of the customer's speech. This caught a paraphrase in v1 of
   the prompt and led to the explicit "must be word-for-word substring"
   wording in `system.md`.
4. **Wrote a substring check in the pipeline before extracting at scale.**
   Once I had the rule, I made the validator enforce it
   (`pipeline.py:verify_quotes_in_source`). Cheap hallucination guard, no
   extra model calls.
5. **Ran the analysis on real extracted data.** The numbers in
   `insights.md` are not hand-curated — they come from
   `03_analysis/insights.py` reading the eight structured JSONs and
   computing severity-weighted aggregates. Re-running the analysis with
   more extractions changes the table without me touching the file.

## Where AI was wrong and I overrode it

- **Initial prompt draft was permissive about evidence quotes.** The first
  prompt said "include a representative quote." That produced paraphrased
  quotes — close to the source but not exact substrings. I changed the
  rule to "MUST be a direct, word-for-word substring" and added the
  substring check to the validator so the prompt is forced to comply.
- **First planning pass suggested doing all 24 extractions.** I overrode
  this: the brief explicitly says "quality over completeness" and "5+
  interactions extracted thoughtfully beats 24 extracted poorly." I picked
  8 covering every channel and every type enum, and used the saved time
  on the validation harness and the analysis layer.
- **Suggested a Jupyter notebook for analysis.** I went with a Python
  script (`insights.py`) + a static `insights.md` instead. A script is
  easier to re-run with different effort estimates, the markdown is
  easier to screen-share without a kernel running, and reviewers without
  Jupyter installed can still read everything. Notebook would be the
  right choice if there were exploratory plotting to do live in the
  presentation — there isn't.
- **Initial bucket logic for the Q3 priority chart used the
  `pain_points.category` field directly.** That conflated themes the
  product team would want separated (e.g., "Samsung TV fix" vs.
  "billing propagation bug" both live under broad categories). I switched
  to keyword bucketing in `insights.py:q3_impact_effort` with the bucket
  function exposed so reviewers can challenge or extend it.

## Artifacts in this folder

- `README.md` — this file.
- `transcripts/` — chat / planning transcripts and prompt iterations.
- `screenshots/` — Claude Code session screenshots taken at the start,
  mid-build, and end of the build.
- `prompt_evolution.md` — version history of the extraction prompt with
  the reasoning behind each change.

## What I would do differently next time

- **Capture screenshots more deliberately.** I took them at session
  boundaries; capturing them at every prompt-iteration boundary would
  give a much richer story.
- **Set up the Anthropic SDK path live** so the pipeline can do all 24 at
  the end of the demo. This would require an API key and a few minutes of
  setup time I deliberately spent on the validator and analysis instead.
- **Add a second few-shot example to the prompt** for noisy inputs.
  Performance on SF-2026-0021 (the `[inaudible]` case) is acceptable but
  would be more reliable with an explicit "here is how to handle marked
  gaps" example.
