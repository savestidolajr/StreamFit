# Prompt Design Notes

## Observations from inspecting inputs (Phase 0)

After reading all 24 interactions and the target schema before writing the prompt:

- **24 interactions span 3 channels:** phone (17), live_chat (4), email (1). Most are dense — averaging ~10 min calls — with clear speaker labels.
- **Recurring themes are extremely concentrated.** The same handful of issues surface across many interactions: Samsung TV crashes, Coach Daniels departure, the March 1st price hike to $34.99, FitFlow's lower price + social features, billing system bugs. This means schema enums for `topics` and `pain_points.category` cluster cleanly.
- **Schema fits the data well — no trimming needed.** Every top-level object in `TARGET_SCHEMA.json` is supported by at least one interaction. `customer.demographic_signals` is the lowest-yield section: age/household/fitness level are rarely stated explicitly. Default these to `unknown` rather than guess.
- **Noise: SF-2026-0021 has marked `[inaudible]` segments and a `NOTE:` line.** The prompt must explicitly handle source-quality markers. This is the canary for `quality_flags.interaction_quality = "significant_gaps"`.
- **The schema already enforces evidence quotes** (`pain_points.verbatim_quote`) and self-reported confidence (`quality_flags.extraction_confidence`). Reinforce both in the prompt — they're the audit trail.

## Design decisions

1. **One prompt, channel-aware** rather than three forks. The system prompt has a small "channel-specific guidance" section and the pipeline injects the channel as a variable. Easier to maintain, easier to demo.
2. **JSON-only output, no fences.** Saves tokens and removes a class of parse failures. Reinforced twice in the system prompt and once in the user message.
3. **Schema embedded in the system prompt** in compact human-readable form with enum values inline. Models follow the format much more reliably when they see field names and types in the same place as the role instruction.
4. **No few-shot examples in v1.** Reasoning: the schema is large; adding even one full example doubles prompt tokens. Tested without; if accuracy is poor, add a single noisy-input example as v2.
5. **Hard rules over soft suggestions.** "Use `null` / `[]` for unknowns" is stated, not implied. "Never guess" is stated explicitly. Models reliably honour explicit prohibitions; vague guidance gets fabrication.
6. **Verbatim quote as a substring constraint.** The post-extraction validator should check that every `verbatim_quote` actually appears as a substring of the source — this is the cheapest hallucination check in the whole pipeline.

## What changed (prompt evolution)

### v1 (initial)
- Single system prompt with embedded schema.
- Output contract: JSON only, no fences.
- Channel-aware via injected variable.
- No few-shot examples.

### v2 (after running v1 on a hard interaction)
- Added explicit channel-specific guidance section after noticing that on SF-2026-0021 (noisy audio) the model was inventing details to fill `[inaudible]` gaps. Fix: explicit instruction that `[inaudible]` / `[background noise]` markers must trigger lowered `extraction_confidence` and that nothing should be fabricated to fill them.
- Added the scoring guidance section. Without it, `churn_risk.level` was inconsistent — `medium` was being used for clear `immediate` cases.
- Tightened the verbatim quote rule: "MUST be a direct, word-for-word substring." Earlier wording allowed paraphrase drift.

### v3 (would do with more time)
- Add 1 noisy + 1 clean few-shot example in the system prompt to anchor `quality_flags` calibration.
- Add prompt-cache markers on the system prompt for production (caches the ~3k token system block; cost drop ~90% on repeated runs).
- Split `pain_points.category` enum into a closed set rather than a free string — currently the model uses inconsistent casing/wording across runs.

## Why this design holds up at scale

- **Stateless per-interaction call.** No conversation state to manage. Each interaction is one prompt → one JSON. Trivially parallelisable across an SQS-driven worker pool.
- **The substring check on `verbatim_quote`** catches the most expensive hallucinations (fabricated complaints) for free, with no second model call.
- **`quality_flags.extraction_confidence` is the routing signal** for tiered model retry: anything below `high` gets escalated to Sonnet; anything still `low` after that goes to human review.
