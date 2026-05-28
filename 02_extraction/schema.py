"""Pydantic translation of TARGET_SCHEMA.json.

One model per nested object. `Literal` types mirror the schema's enums so
hallucinated values fail validation immediately. Every field that the source
schema marks as nullable is `Optional[...]` with default `None`.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# interaction
# ---------------------------------------------------------------------------

InteractionType = Literal[
    "sales_inquiry",
    "support_request",
    "cancellation",
    "upgrade_inquiry",
    "general_inquiry",
    "complaint",
    "win_back",
]

Channel = Literal["phone", "live_chat", "email"]

ResolutionStatus = Literal[
    "resolved", "partially_resolved", "unresolved", "escalated", "cancelled"
]


class Agent(BaseModel):
    name: str
    handled_well: bool
    notable_actions: Optional[str] = None


class Resolution(BaseModel):
    status: ResolutionStatus
    summary: str


class Interaction(BaseModel):
    type: InteractionType
    channel: Channel
    duration_seconds: Optional[int] = None
    agent: Agent
    resolution: Resolution


# ---------------------------------------------------------------------------
# customer
# ---------------------------------------------------------------------------

CurrentPlan = Literal[
    "free_trial", "basic", "premium", "family", "enterprise", "unknown"
]

LifecycleStage = Literal[
    "new", "onboarding", "active", "at_risk", "churning", "churned", "win_back"
]

AgeRange = Literal["18-25", "26-35", "36-45", "46-55", "55+", "unknown"]

FitnessLevel = Literal["beginner", "intermediate", "advanced", "unknown"]


class DemographicSignals(BaseModel):
    age_range: AgeRange = "unknown"
    household: Optional[str] = None
    fitness_level: FitnessLevel = "unknown"


class Customer(BaseModel):
    name: Optional[str] = None
    tenure_months: Optional[int] = None
    current_plan: CurrentPlan = "unknown"
    lifecycle_stage: LifecycleStage
    demographic_signals: DemographicSignals


# ---------------------------------------------------------------------------
# sentiment
# ---------------------------------------------------------------------------

OverallSentiment = Literal[
    "very_negative",
    "negative",
    "mixed",
    "neutral",
    "positive",
    "very_positive",
]

Trajectory = Literal["improving", "stable", "declining"]

EmotionalIntensity = Literal["low", "moderate", "high"]

SentimentShift = Literal["positive_spike", "negative_spike", "turning_point"]


class KeyMoment(BaseModel):
    timestamp: Optional[str] = None
    description: str
    sentiment_shift: SentimentShift
    trigger: str


class Sentiment(BaseModel):
    overall: OverallSentiment
    trajectory: Trajectory
    emotional_intensity: EmotionalIntensity
    key_moments: List[KeyMoment] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# insights
# ---------------------------------------------------------------------------

Severity = Literal["low", "medium", "high", "critical"]

Strength = Literal["weak", "moderate", "strong"]

CompetitorContext = Literal[
    "currently_using", "considering", "switched_to", "switched_from", "comparing"
]

SentimentVsUs = Literal["competitor_preferred", "neutral", "we_preferred"]

Urgency = Literal["nice_to_have", "important", "dealbreaker"]


class PainPoint(BaseModel):
    category: str
    description: str
    severity: Severity
    verbatim_quote: str
    actionable: bool


class Motivation(BaseModel):
    type: str
    description: str
    strength: Strength


class CompetitorMention(BaseModel):
    name: str
    context: CompetitorContext
    sentiment_vs_us: SentimentVsUs
    detail: str


class FeatureRequest(BaseModel):
    feature: str
    urgency: Urgency
    existing_workaround: Optional[str] = None


class Insights(BaseModel):
    pain_points: List[PainPoint] = Field(default_factory=list)
    motivations: List[Motivation] = Field(default_factory=list)
    competitor_mentions: List[CompetitorMention] = Field(default_factory=list)
    feature_requests: List[FeatureRequest] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# intent
# ---------------------------------------------------------------------------

ChurnLevel = Literal["none", "low", "medium", "high", "immediate"]

UpsellLevel = Literal["none", "low", "medium", "high"]


class ChurnRisk(BaseModel):
    level: ChurnLevel
    factors: List[str] = Field(default_factory=list)
    save_attempted: bool
    save_successful: Optional[bool] = None


class UpsellOpportunity(BaseModel):
    level: UpsellLevel
    target_plan: Optional[str] = None
    signals: List[str] = Field(default_factory=list)


class Intent(BaseModel):
    primary: str
    secondary: Optional[str] = None
    churn_risk: ChurnRisk
    upsell_opportunity: UpsellOpportunity


# ---------------------------------------------------------------------------
# topics / actions / quality
# ---------------------------------------------------------------------------

TopicRelevance = Literal["primary", "secondary", "mentioned"]

TopicSentiment = Literal["positive", "negative", "neutral"]


class Topic(BaseModel):
    topic: str
    relevance: TopicRelevance
    sentiment: TopicSentiment


ActionOwner = Literal[
    "agent", "customer", "engineering", "billing", "product", "management"
]

ActionPriority = Literal["low", "medium", "high", "urgent"]

ActionStatus = Literal["completed", "pending", "requires_follow_up"]


class ActionItem(BaseModel):
    action: str
    owner: ActionOwner
    priority: ActionPriority
    status: ActionStatus


InteractionQuality = Literal["clean", "minor_issues", "significant_gaps"]

ExtractionConfidence = Literal["high", "medium", "low"]


class QualityFlags(BaseModel):
    interaction_quality: InteractionQuality
    extraction_confidence: ExtractionConfidence
    requires_human_review: bool
    review_reasons: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


class ExtractedInteraction(BaseModel):
    interaction_id: str
    interaction: Interaction
    customer: Customer
    sentiment: Sentiment
    insights: Insights
    intent: Intent
    topics: List[Topic] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    quality_flags: QualityFlags
