# User Message Template

Variables filled in by the pipeline at runtime:

- `{{interaction_id}}` — e.g. `SF-2026-0001`
- `{{channel}}` — `phone` | `live_chat` | `email`
- `{{raw_text}}` — the full interaction file contents

---

```
INTERACTION_ID: {{interaction_id}}
CHANNEL: {{channel}}

----- RAW INTERACTION START -----
{{raw_text}}
----- RAW INTERACTION END -----

Return a single JSON object matching the target schema. No prose, no markdown
fences. First character `{`, last character `}`. Every required field present.
All `verbatim_quote` values must be exact substrings of the raw interaction
above.
```
