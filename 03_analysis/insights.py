"""StreamFit analysis: load structured extractions, answer the 3 leadership questions.

Outputs:
- data/extracted.csv         — one row per interaction, flattened
- data/pain_points.csv       — one row per pain point across all interactions
- data/feature_requests.csv  — one row per feature request
- charts/q1_churn_drivers.png
- charts/q2_segment_quadrant.png
- charts/q3_impact_effort.png
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
STRUCTURED = ROOT.parent / "02_extraction" / "outputs" / "structured"
DATA_DIR = ROOT / "data"
CHARTS_DIR = ROOT / "charts"
DATA_DIR.mkdir(exist_ok=True)
CHARTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


def load_all() -> list[dict]:
    rows = []
    for p in sorted(STRUCTURED.glob("SF-*.json")):
        rows.append(json.loads(p.read_text()))
    return rows


# ---------------------------------------------------------------------------
# Flatten
# ---------------------------------------------------------------------------


def flatten(extractions: list[dict]) -> pd.DataFrame:
    out = []
    for e in extractions:
        out.append(
            {
                "interaction_id": e["interaction_id"],
                "type": e["interaction"]["type"],
                "channel": e["interaction"]["channel"],
                "duration_seconds": e["interaction"]["duration_seconds"],
                "agent": e["interaction"]["agent"]["name"],
                "agent_handled_well": e["interaction"]["agent"]["handled_well"],
                "resolution_status": e["interaction"]["resolution"]["status"],
                "customer_name": e["customer"]["name"],
                "tenure_months": e["customer"]["tenure_months"],
                "current_plan": e["customer"]["current_plan"],
                "lifecycle_stage": e["customer"]["lifecycle_stage"],
                "fitness_level": e["customer"]["demographic_signals"]["fitness_level"],
                "sentiment_overall": e["sentiment"]["overall"],
                "sentiment_trajectory": e["sentiment"]["trajectory"],
                "emotional_intensity": e["sentiment"]["emotional_intensity"],
                "churn_risk": e["intent"]["churn_risk"]["level"],
                "save_attempted": e["intent"]["churn_risk"]["save_attempted"],
                "save_successful": e["intent"]["churn_risk"]["save_successful"],
                "upsell_level": e["intent"]["upsell_opportunity"]["level"],
                "n_pain_points": len(e["insights"]["pain_points"]),
                "n_feature_requests": len(e["insights"]["feature_requests"]),
                "n_competitor_mentions": len(e["insights"]["competitor_mentions"]),
                "primary_intent": e["intent"]["primary"],
            }
        )
    return pd.DataFrame(out)


def flatten_pain_points(extractions: list[dict]) -> pd.DataFrame:
    rows = []
    for e in extractions:
        for pp in e["insights"]["pain_points"]:
            rows.append(
                {
                    "interaction_id": e["interaction_id"],
                    "category": pp["category"],
                    "description": pp["description"],
                    "severity": pp["severity"],
                    "actionable": pp["actionable"],
                    "verbatim_quote": pp["verbatim_quote"],
                    "churn_risk": e["intent"]["churn_risk"]["level"],
                    "current_plan": e["customer"]["current_plan"],
                    "tenure_months": e["customer"]["tenure_months"],
                }
            )
    return pd.DataFrame(rows)


def flatten_feature_requests(extractions: list[dict]) -> pd.DataFrame:
    rows = []
    for e in extractions:
        for fr in e["insights"]["feature_requests"]:
            rows.append(
                {
                    "interaction_id": e["interaction_id"],
                    "feature": fr["feature"],
                    "urgency": fr["urgency"],
                    "existing_workaround": fr["existing_workaround"],
                    "current_plan": e["customer"]["current_plan"],
                    "lifecycle_stage": e["customer"]["lifecycle_stage"],
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Q1 — Churn drivers weighted by severity × actionability
# ---------------------------------------------------------------------------

SEVERITY_WEIGHT = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def q1_churn_drivers(pp: pd.DataFrame) -> pd.DataFrame:
    df = pp.copy()
    df["severity_weight"] = df["severity"].map(SEVERITY_WEIGHT)
    grouped = (
        df.groupby("category")
        .agg(
            frequency=("interaction_id", "count"),
            total_severity=("severity_weight", "sum"),
            actionable_rate=("actionable", "mean"),
        )
        .sort_values("total_severity", ascending=False)
    )
    return grouped


def chart_q1(grouped: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#2ca02c" if r >= 0.99 else "#ff7f0e" if r >= 0.5 else "#d62728"
              for r in grouped["actionable_rate"]]
    ax.barh(grouped.index, grouped["total_severity"], color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("Severity-weighted frequency (low=1 / med=2 / high=3 / critical=4)")
    ax.set_title("Q1 — Churn driver categories\ngreen = 100% actionable, orange = partial, red = mostly not actionable")
    for i, (cat, row) in enumerate(grouped.iterrows()):
        ax.text(row["total_severity"] + 0.1, i,
                f"n={row['frequency']} • act={row['actionable_rate']:.0%}",
                va="center", fontsize=9)
    plt.tight_layout()
    fig.savefig(CHARTS_DIR / "q1_churn_drivers.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Q2 — Segment quadrant: tenure × churn risk × upsell signal
# ---------------------------------------------------------------------------

CHURN_NUM = {"none": 0, "low": 1, "medium": 2, "high": 3, "immediate": 4}
UPSELL_NUM = {"none": 0, "low": 1, "medium": 2, "high": 3}


def chart_q2(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 6))
    df = df.copy()
    df["churn_num"] = df["churn_risk"].map(CHURN_NUM)
    df["upsell_num"] = df["upsell_level"].map(UPSELL_NUM)
    # Jitter so overlapping points are visible.
    import numpy as np
    rng = np.random.default_rng(seed=1)
    jitter = rng.uniform(-0.15, 0.15, size=(len(df), 2))
    xs = df["churn_num"] + jitter[:, 0]
    ys = df["upsell_num"] + jitter[:, 1]
    size = df["tenure_months"].fillna(6).clip(lower=3) * 25
    scatter = ax.scatter(xs, ys, s=size, alpha=0.65,
                         c=["#d62728" if s == "premium" else "#1f77b4" if s == "basic" else "#7f7f7f"
                            for s in df["current_plan"]])
    for _, r in df.iterrows():
        ax.annotate(r["interaction_id"].replace("SF-2026-", ""),
                    (CHURN_NUM[r["churn_risk"]], UPSELL_NUM[r["upsell_level"]]),
                    fontsize=8, ha="center", va="center")
    ax.set_xlabel("Churn risk (none → immediate)")
    ax.set_ylabel("Upsell opportunity (none → high)")
    ax.set_xticks(list(CHURN_NUM.values()))
    ax.set_xticklabels(list(CHURN_NUM.keys()))
    ax.set_yticks(list(UPSELL_NUM.values()))
    ax.set_yticklabels(list(UPSELL_NUM.keys()))
    ax.set_title("Q2 — Segment quadrant\nbubble size = tenure months • red = Premium • blue = Basic • grey = unknown")
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    fig.savefig(CHARTS_DIR / "q2_segment_quadrant.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Q3 — Feature requests / improvements: impact (frequency × urgency) vs effort
# ---------------------------------------------------------------------------

URGENCY_WEIGHT = {"nice_to_have": 1, "important": 2, "dealbreaker": 3}

# Hand-estimated effort per feature theme (1=low / 5=high). In production this
# would come from engineering. Documented so reviewers see the heuristic.
EFFORT = {
    "samsung_tv_app_fix": 2,
    "social_features": 4,
    "advanced_strength_content": 3,
    "yin_restorative_yoga": 2,
    "meditation_programmes": 3,
    "granular_search": 2,
    "billing_propagation_bug": 1,
    "aggregated_data_opt_out": 1,
    "replacement_hiit_trainer": 4,
    "streak_protection": 1,
}


def q3_impact_effort(fr: pd.DataFrame, pp: pd.DataFrame) -> pd.DataFrame:
    """Combine feature requests with dealbreaker-class pain points."""
    # Bucket free-text features into themes the leadership team would recognise.
    def bucket(text: str) -> str | None:
        t = text.lower()
        if "samsung" in t or "tv app" in t or "stable samsung" in t:
            return "samsung_tv_app_fix"
        if "social" in t or "challenge" in t or "leaderboard" in t:
            return "social_features"
        if "strength" in t:
            return "advanced_strength_content"
        if "yin" in t or "restorative" in t or "nidra" in t:
            return "yin_restorative_yoga"
        if "meditation" in t:
            return "meditation_programmes"
        if "search" in t or "filter" in t:
            return "granular_search"
        if "cancellation propagation" in t or "billing" in t:
            return "billing_propagation_bug"
        if "opt out" in t or "opt-out" in t or "aggregated" in t:
            return "aggregated_data_opt_out"
        if "hiit" in t:
            return "replacement_hiit_trainer"
        if "streak" in t:
            return "streak_protection"
        return None

    fr = fr.copy()
    fr["theme"] = fr["feature"].map(bucket)
    fr = fr.dropna(subset=["theme"])
    fr["urgency_weight"] = fr["urgency"].map(URGENCY_WEIGHT)

    # Severity-weighted pain-point votes feed the impact score too.
    pp_themed = pp.copy()
    pp_themed["theme"] = pp_themed["description"].map(bucket)
    pp_themed = pp_themed.dropna(subset=["theme"])
    pp_themed["severity_weight"] = pp_themed["severity"].map(SEVERITY_WEIGHT)

    impact_from_requests = fr.groupby("theme")["urgency_weight"].sum()
    impact_from_pain = pp_themed.groupby("theme")["severity_weight"].sum()
    impact = impact_from_requests.add(impact_from_pain, fill_value=0)

    out = pd.DataFrame(
        {
            "impact": impact,
            "effort": [EFFORT.get(t, 3) for t in impact.index],
        }
    )
    out["priority_score"] = out["impact"] / out["effort"]
    return out.sort_values("priority_score", ascending=False)


def chart_q3(scored: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(scored["effort"], scored["impact"], s=200, alpha=0.7, c="#1f77b4")
    for theme, r in scored.iterrows():
        ax.annotate(theme.replace("_", " "), (r["effort"], r["impact"]),
                    fontsize=9, xytext=(8, 4), textcoords="offset points")
    ax.set_xlabel("Effort (1=low, 5=high) — engineering estimate")
    ax.set_ylabel("Impact (severity-weighted pain + urgency-weighted requests)")
    ax.set_xlim(0, 6)
    ax.set_title("Q3 — Product improvement priority\ntop-left quadrant = high impact, low effort = ship first")
    ax.axhline(scored["impact"].median(), color="grey", linestyle="--", alpha=0.5)
    ax.axvline(scored["effort"].median(), color="grey", linestyle="--", alpha=0.5)
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    fig.savefig(CHARTS_DIR / "q3_impact_effort.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    extractions = load_all()
    df = flatten(extractions)
    pp = flatten_pain_points(extractions)
    fr = flatten_feature_requests(extractions)

    df.to_csv(DATA_DIR / "extracted.csv", index=False)
    pp.to_csv(DATA_DIR / "pain_points.csv", index=False)
    fr.to_csv(DATA_DIR / "feature_requests.csv", index=False)

    q1 = q1_churn_drivers(pp)
    q1.to_csv(DATA_DIR / "q1_churn_drivers.csv")
    chart_q1(q1)

    chart_q2(df)

    q3 = q3_impact_effort(fr, pp)
    q3.to_csv(DATA_DIR / "q3_priority.csv")
    chart_q3(q3)

    print(f"loaded {len(extractions)} extractions")
    print(f"flattened to {len(df)} interaction rows, {len(pp)} pain points, {len(fr)} feature requests")
    print("\nQ1 — Churn driver categories")
    print(q1)
    print("\nQ3 — Improvement priorities")
    print(q3)


if __name__ == "__main__":
    main()
