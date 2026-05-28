# Prompt Evolution

Three rough versions of the extractor prompt. v3 is what currently lives in
`02_extraction/prompts/system.md`. v1 and v2 below are reconstructed for the
audit trail.

---

## v1 — first draft

**Shape.** Single system prompt, embedded JSON schema, JSON-only output
contract, no few-shot examples, channel-aware via injected variable. The
prompt was about half the length of the current version.

**What went wrong.**

1. **Paraphrased "evidence" quotes.** v1 wrote "include a representative
   quote from the customer." The model produced quotes that were
   close-to-source but not exact substrings — e.g. for SF-2026-0001 it
   produced "the catalogue feels static" as a quote when the actual line
   was "I'm doing the same workouts I was doing in October."
2. **Inconsistent `churn_risk.level`.** The model used `medium` for cases
   where the customer was actively cancelling (`immediate`) and `high` for
   what should have been `medium`. No clear scoring rubric was provided.
3. **On the noisy SF-2026-0021 input, the model filled in `[inaudible]`
   gaps with plausible-sounding invented detail** — e.g. it claimed the
   class title was specific when the source clearly marked it as
   inaudible. Pure hallucination driven by completion pressure.

---

## v2 — after running v1 on three test inputs

**Changes.**

1. **Added an explicit "no fabrication" rule** in its own subsection. "If a
   field cannot be determined, set it to null. Never guess."
2. **Tightened the verbatim quote rule.** "MUST be a direct, word-for-word
   substring of the customer's speech." Plus a separate paragraph
   explaining that if a clean quote can't be found, the pain point should
   be omitted rather than paraphrased.
3. **Added a channel-specific guidance section** covering how to read
   phone transcripts (ASR artefacts as noise), chat logs (brevity is not
   low importance), and emails (most recent customer message is primary).
4. **Added a scoring guidance section** defining the `churn_risk` ladder
   and `pain_points.actionable` rule explicitly, with examples of what
   counts as `immediate` vs `high` vs `medium`.

**What still wasn't great.**

- `pain_points.category` was a free string. Different runs used "billing
  issue", "billing", "Billing" — inconsistent casing and wording.
- No few-shot example for noisy inputs. Performance on SF-2026-0021
  improved with the no-fabrication rule but was not bulletproof.

---

## v3 — current version in `02_extraction/prompts/system.md`

**Changes from v2.**

1. **Added an explicit reminder section** at the bottom of the prompt
   ("Reminders before returning") so the model re-checks the contract
   right before generation. This is a well-documented technique for
   improving format adherence.
2. **Added the `interaction_id` matching reminder** because earlier runs
   occasionally emitted the wrong ID.
3. **Embedded the schema as a fenced JSON block** within the system
   message, not just as prose. The model adheres to structured templates
   more reliably than to narrative descriptions of the same structure.
4. **Added handling guidance for source-quality markers** (`[inaudible]`,
   `[background noise]`) that explicitly link to lowered
   `quality_flags.extraction_confidence`.

## v4 — what I'd do with more time

- **Add 1–2 few-shot examples** at the bottom of the system message: one
  clean interaction with its ideal output, one noisy interaction
  demonstrating correct `null` + lowered-confidence behaviour. Eats ~1k
  tokens but should improve calibration on edge cases noticeably.
- **Close the `pain_points.category` enum** to a fixed set (`billing`,
  `content`, `app_performance`, `pricing`, `customer_service`,
  `feature_gap`, `ux`, `other`) and add it to the schema's `Literal`
  types. Currently the bucket logic in `insights.py` papers over the
  drift; a closed enum upstream is cleaner.
- **Add prompt-cache markers** on the system message for production. The
  pipeline already does this; the prompt file itself should call it out
  in a comment so future editors don't reorder content that would
  invalidate the cache.
- **Tool use instead of JSON-mode** for the actual call path. The model
  emits a `submit_interaction` tool call whose argument schema is the
  same Pydantic class. This removes the JSON-parse step entirely and
  guarantees enum validity at the model layer.
