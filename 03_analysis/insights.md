# StreamFit Insights — From 8 Customer Interactions

This is the analysis layer on top of `02_extraction/outputs/structured/`. The
numbers below come from `insights.py` running over 8 structured extractions
(8 of the 24 inputs — see [run_log.md](../02_extraction/run_log.md) for why).

**Caveat up front.** N=8 is methodology, not findings. Every percentage and
ranking on this page is shown to demonstrate how the pipeline answers the
business questions; the production version of this analysis runs over the
full month's interaction volume (~hundreds–thousands), with confidence
intervals attached.

---

## Q1 — Top drivers of churn, and which are most actionable?

**Method.** Each `insights.pain_point` from every extraction is bucketed by
`category`, weighted by `severity` (low=1, medium=2, high=3, critical=4), and
the per-category `actionable` rate is computed.

| Category | Mentions | Severity-weighted score | Actionable rate |
|---|---:|---:|---:|
| **content** | 7 | 19 | 100% |
| **billing** | 5 | 17 | 80% |
| **customer_service** | 6 | 17 | 100% |
| **app_performance** | 3 | 11 | 100% |
| **feature_gap** | 3 | 6 | 100% |
| **pricing** | 2 | 5 | 100% |
| **ux** | 1 | 2 | 100% |

Chart: [charts/q1_churn_drivers.png](charts/q1_churn_drivers.png).

### Reading the table

- **Content** is the largest aggregate driver — but the picture splits two
  ways: (a) catalogue staleness and missing strength content (the Coach
  Daniels gap), (b) yoga sub-genre gaps (yin / restorative). The first is a
  retention threat, the second is an upsell threat (see Q2).
- **Billing and customer service together account for 34 severity points** —
  more than content. Three of our eight interactions involve billing failures
  (0002, 0017, 0023) and **all three are the same underlying problem class**:
  cancellation / charge events not propagating reliably. This is the single
  highest-leverage technical fix in the dataset.
- **Actionability is high almost everywhere** — only 1 of 27 pain points is
  not actionable (a customer venting about the 3–5 day refund settlement
  window, which is a bank-side reality). Translation: there is no "external
  factors" category absorbing churn here. Whatever leadership prioritises,
  it can be addressed.

### Three churn drivers leadership should act on first

1. **Billing system reliability** — three interactions, two of them serious
   trust-destroyers (0017 threatening chargeback, 0023 "completely destroyed
   my trust"). The fix is a propagation contract between the account system
   and the billing system, not a UX tweak. Confirmed by the engineering
   notes Marcus surfaced in 0017 ("payment gateway retry bug" deployed Feb 5,
   "race condition during a billing system migration" patched Feb 11).
2. **Content velocity** — long-tenure customers (0001, 0022) explicitly say
   the catalogue feels static. Both cited the same dimensions: advanced
   strength content and replacement HIIT after Coach Daniels left.
3. **Samsung TV app stability** — three interactions (0005, 0021, 0022)
   share this issue. Customer 0021 has been hit four times in one month;
   0022 cited it as one of three stacked dealbreakers. The mid-March fix is
   the right answer if it actually ships.

---

## Q2 — Customer segments with highest upsell or retention opportunity

Chart: [charts/q2_segment_quadrant.png](charts/q2_segment_quadrant.png).

### Segments visible in this small sample

| Segment | Example | Direction | Why |
|---|---|---|---|
| **Long-tenure Premium (≥18 mo)** | 0001, 0022 | **Retention** | Both at high churn risk citing content staleness + specific trainers. Save costs (price lock, free month, loyalty discount) are small vs. CLV. |
| **Active Premium power-user** | 0010 | **Upsell** (medium–high) | 5x/week yoga user already paying $42.98/mo across StreamFit + Headspace; **explicit verbatim signal**: "id literally pay more for that" for combined fitness + meditation. |
| **Basic with repeated billing pain** | 0002, 0017 | **Retention** | Customer is already on the cheapest tier, can't be downsold, threatening chargeback. Save them with operational competence, not discounts. |
| **Churned via billing failure** | 0023 | **Already gone** | Lifecycle stage `churned` — the work here is preventing repeats, not winning back. |
| **Privacy-sensitive Premium** | 0024 | **Retention** (risk) | High-visibility customer (20k-subscriber security blog). Low immediate churn risk but disproportionate brand consequence if mishandled. |

### The single highest-value segment we can name from this data

**Long-tenure Premium customers with a "stale catalogue + specific
trainer/content gap" complaint pattern.** Two of our eight interactions
(0001 and 0022) are in this segment. Both were retained with combinations of
price lock + free month + dated content commitments. Both have **April
re-evaluation deadlines** baked into their accounts — that is a measurable
follow-up cohort the agent team can re-engage with personally.

### Upsell archetype we should design around

The 0010 customer is the upsell archetype. Heavy yoga user, on Premium, has
articulated a willingness to pay ~$35–40/mo for a bundle that absorbs
Headspace. **Recommended action:** instrument an opt-in beta for the
in-development meditation programmes, sized to the ~5x/week active-yoga
cohort. This is a known-bigger market than the eight people in this dataset.

---

## Q3 — Product/service improvements with highest impact

**Method.** For each improvement theme, impact = severity-weighted
pain-point votes + urgency-weighted feature-request votes. Effort is a
hand-estimated 1–5 score. Priority = impact ÷ effort. Effort estimates are
in `insights.py:EFFORT` so a reviewer can adjust and re-run.

Chart: [charts/q3_impact_effort.png](charts/q3_impact_effort.png).

| Theme | Impact | Effort | Priority |
|---|---:|---:|---:|
| **Billing propagation bug fix** | 13.0 | 1 | **13.0** |
| **Samsung TV app fix** | 11.0 | 2 | **5.5** |
| **Workout streak protection** | 5.0 | 1 | **5.0** |
| **Aggregated-data opt-out** | 4.0 | 1 | **4.0** |
| **Yin / restorative yoga library** | 8.0 | 2 | **4.0** |
| **Advanced strength content** | 6.0 | 3 | 2.0 |
| **Replacement HIIT trainer** | 7.0 | 4 | 1.75 |
| **Granular class search** | 3.0 | 2 | 1.5 |
| **Social / challenges features** | 4.0 | 4 | 1.0 |
| **Meditation programmes** | 2.0 | 3 | 0.67 |

### What this says

1. **Billing propagation is the obvious top priority.** It is the dominant
   driver of the worst-rated interactions (0017, 0023), the engineering
   work is bounded (per Marcus's email in 0017, the underlying bugs were
   patched Feb 5 + Feb 11; the missing piece is the propagation contract
   itself), and the impact-per-engineer-day is enormous.
2. **Samsung TV fix and streak protection ship together.** Both reduce the
   harm from app crashes. Streak protection ("if the app crashes mid-class,
   auto-credit the class") removes the most painful symptom even before the
   underlying fix lands. The mid-March update target is already public-facing.
3. **Yin / restorative yoga is the cheapest content win.** It's a content
   production task, not an engineering one, and it has explicit demand
   signal from a happy power-user (0010) who would also pay more for the
   adjacent meditation bundle.
4. **Social features are deferred.** They are the loudest single ask (0011,
   0019, 0022 all mention it; 0019 calls it "the one thing that tempts me
   to switch"), but the engineering effort is high relative to alternatives
   above it on the list. Recommendation: scope a thin v1 (workout-streak
   sharing between explicit friend pairs) rather than a full leaderboard
   product. Re-rank after that scoping.

---

## How this analysis differs at scale (bonus)

| At this sample (N=8) | At production scale (10k+/month) |
|---|---|
| Hand-flattened pandas DataFrame from JSON files | dbt models materialised in a warehouse, refreshed daily |
| Single snapshot of severity-weighted frequencies | Time-series: churn-driver mix-shift week-over-week, alerting on emerging categories |
| Customer segments named anecdotally from 8 examples | Clustered segments fit on the structured fields (lifecycle × plan × tenure × dominant pain category) with cohort sizing |
| Effort estimates hand-keyed in `insights.py` | Effort pulled from engineering planning tool, not heuristic |
| Improvement priority ranked once for a meeting | Priority list recomputed each week; leadership sees deltas, not absolutes |
| No statistical confidence | Bootstrap CI on every ranking; categories with overlapping intervals merged on the chart |
| Manual review = a human reading every interaction | `quality_flags.requires_human_review = true` rows routed to a CS-analyst queue (Retool / Streamlit); ~5–10% of volume |

The schema does not change. The pipeline does not change. Only the storage
and aggregation layer above it become more disciplined.

---

## Honest limitations of this analysis

- **N=8 means almost every percentage in here is noisy.** Treat the ordering
  of categories as suggestive, not definitive.
- **Effort scores are guesses.** They influence Q3 ranking heavily and would
  be the first thing to firm up with engineering input.
- **Pain point bucketing into improvement themes is regex-based in
  `insights.py`.** At scale this becomes a small LLM call over the
  unique-description list — cheap, more robust, and survives wording drift.
- **No cohort retention math here.** With 8 interactions there is no
  meaningful baseline. At scale, you'd quantify "long-tenure Premium churn
  rate ↑ when content velocity ↓" with proper survival analysis.
