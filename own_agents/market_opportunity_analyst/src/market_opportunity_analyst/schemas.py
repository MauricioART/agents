from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RatingCriterion = Literal[
    "territory_presence",
    "target_customer_overlap",
    "problem_solution_overlap",
    "public_traction",
    "offer_strength",
    "evidence_quality",
]


class Evidence(BaseModel):
    claim: str
    title: str
    url: str
    publisher: str
    source_type: Literal["company", "app_store", "news", "public_data", "industry", "other"]
    accessed_on: str
    status: Literal["verified", "estimate", "inference"] = "verified"


class CriterionRating(BaseModel):
    criterion: RatingCriterion
    score: int = Field(ge=1, le=5)
    rationale: str
    evidence_urls: list[str] = Field(default_factory=list)


class CompetitorProfile(BaseModel):
    name: str
    directness: Literal["direct", "indirect", "substitute"]
    territory_presence: str
    target_customers: list[str] = Field(default_factory=list)
    value_proposition: str
    product_and_service: str
    business_model: str
    revenue_streams: list[str] = Field(default_factory=list)
    pricing: str
    go_to_market: list[str] = Field(default_factory=list)
    traction_signals: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses_or_gaps: list[str] = Field(default_factory=list)
    ratings: list[CriterionRating] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class OpportunityArea(BaseModel):
    title: str
    target_segment: str
    unmet_need: str
    evidence_of_gap: list[str] = Field(default_factory=list)
    why_existing_options_leave_room: str
    product_wedge: str
    possible_business_model: str
    validation_experiment: str
    key_risks: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
    evidence_urls: list[str] = Field(default_factory=list)


class MarketAnalysis(BaseModel):
    product_idea: str
    territory: str
    executive_summary: str
    market_definition: str
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    demand_signals: list[str] = Field(default_factory=list)
    market_context_and_constraints: list[str] = Field(default_factory=list)
    business_model_patterns: list[str] = Field(default_factory=list)
    ranking_methodology: str
    competitors: list[CompetitorProfile] = Field(default_factory=list)
    opportunity_areas: list[OpportunityArea] = Field(default_factory=list)
    recommended_positioning: str
    validation_plan_30_days: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    sources: list[Evidence] = Field(default_factory=list)
