from __future__ import annotations

import os

from crewai import Agent, Crew, Process, Task

from market_opportunity_analyst.schemas import MarketAnalysis
from market_opportunity_analyst.tools import MarketPageFetchTool, MarketWebSearchTool


WEIGHTS = {
    "territory_presence": 25,
    "target_customer_overlap": 20,
    "problem_solution_overlap": 25,
    "public_traction": 15,
    "offer_strength": 10,
    "evidence_quality": 5,
}


def create_market_crew() -> Crew:
    model = os.getenv("CREWAI_MODEL", "openai/mimo-v2.6-pro")
    search = MarketWebSearchTool()
    fetch = MarketPageFetchTool()
    market_scout = Agent(
        role="Market Scope Analyst",
        goal="Define a useful market boundary from a product idea and territory while making uncertainty explicit",
        backstory=(
            "You are a product-market analyst. Separate direct competitors, indirect alternatives, and non-digital substitutes. "
            "Infer likely users and constraints cautiously; state assumptions rather than turning them into facts."
        ),
        llm=model,
        allow_delegation=False,
        verbose=False,
        max_iter=8,
    )
    researcher = Agent(
        role="Competitive Market Researcher",
        goal="Find current comparable products and document their business strategies with traceable evidence",
        backstory=(
            "You conduct market research across company sites, app stores, public data, industry material, and news. "
            "Search in the territory's language and English when useful. Prioritize first-party evidence for pricing, "
            "features, coverage, and business model; use app-store and reputable news sources for public traction signals. "
            "A search snippet is only a lead. Fetch pages before treating claims as verified. Do not estimate revenue, "
            "market share, downloads, or rankings without a credible source and clear label."
        ),
        llm=model,
        tools=[search, fetch],
        allow_delegation=False,
        verbose=False,
        max_iter=24,
        max_rpm=10,
    )
    strategist = Agent(
        role="Market Opportunity Strategist",
        goal="Identify defensible market opportunities and an initial positioning based on competitor evidence",
        backstory=(
            "You connect unmet customer needs to competitor gaps and feasible business models. You treat opportunity areas "
            "as hypotheses until customer evidence exists, state the evidence behind each one, and propose low-cost tests. "
            "You do not confuse market size, company popularity, and product fit."
        ),
        llm=model,
        tools=[search, fetch],
        allow_delegation=False,
        verbose=False,
        max_iter=14,
    )
    reviewer = Agent(
        role="Evidence and Ranking Reviewer",
        goal="Remove unsupported claims and make competitor scoring comparable, transparent, and territory-specific",
        backstory=(
            "You review market reports skeptically. Check that each named competitor is relevant to the territory, business "
            "models are distinguished from verified revenue, opportunity claims cite real evidence, and estimates are labeled. "
            "Use only the supplied sources or facts you can verify with the research tools. Keep score rationales consistent "
            "with the declared 1–5 criteria. Do not invent market-share data."
        ),
        llm=model,
        tools=[search, fetch],
        allow_delegation=False,
        verbose=False,
        max_iter=12,
    )

    scope = Task(
        description=(
            "Define the relevant market for this product idea in this territory. Infer likely users, use cases, direct and "
            "indirect alternatives, and key constraints from the prompt, clearly marking every inference as an assumption. "
            "Identify what further information would materially change the market boundary.\n\n"
            "PRODUCT IDEA: {idea}\nTERRITORY: {territory}\nADDITIONAL CONSTRAINTS: {constraints}"
        ),
        expected_output="A concise market scope brief: category, territory boundary, target users, direct/indirect competitors, assumptions, and open questions.",
        agent=market_scout,
    )
    research = Task(
        description=(
            "Research the current competitive landscape for {idea} in {territory}. Use the scope brief as context. "
            "Find a useful set of direct competitors, indirect alternatives, and substitutes (normally 5–12, fewer if the "
            "market is genuinely small). For each, investigate target users, geographic availability, value proposition, "
            "products, monetization/revenue streams, public pricing, acquisition/distribution strategy, partnerships, and "
            "public traction signals. Search official company sources, relevant App Store/Google Play listings, news, and "
            "public/regulatory data. Search Spanish/local-language and English queries when useful. Use country_code "
            "mx and language es for Mexico; otherwise infer the most relevant codes from {territory}. Fetch important pages. "
            "Keep source title, URL, publisher, type, and access date with each factual claim. Report exact numbers only when "
            "the source supports them; label estimates and inferences. Include uncertainty, inaccessible sources, and gaps."
        ),
        expected_output="A source-backed competitive landscape dossier with individual competitor profiles, business strategies, signals, and unknowns.",
        agent=researcher,
        context=[scope],
    )
    opportunities = Task(
        description=(
            "Analyze the researched landscape for {idea} in {territory}. Compare the competitors and alternatives, then "
            "identify concrete opportunity areas. For each area state the target segment, unmet need, evidence of the gap, "
            "why the existing options may leave room, a plausible product wedge, possible business model, a validation test, "
            "risks, confidence, and supporting source URLs. Separate observed evidence from strategic inference. Do not "
            "claim an opportunity is validated without customer research. Give an initial positioning recommendation and a "
            "30-day validation plan.\n\nAdditional constraints: {constraints}"
        ),
        expected_output="A detailed strategic market analysis with evidence-linked opportunity hypotheses and validation steps.",
        agent=strategist,
        context=[scope, research],
    )
    final = Task(
        description=(
            "Produce the final structured market analysis for {idea} in {territory}, using all prior work. Review and correct "
            "unsupported, stale, or geographically irrelevant claims. Preserve URLs and distinguish verified statements, "
            "estimates, and inferences. Include direct, indirect, and substitute competitors when relevant. Include a profile "
            "for each competitor with business model, revenue streams, pricing where public, target customer, go-to-market "
            "strategy, strengths, gaps, traction signals, evidence, and unknowns. Assign 1–5 ratings with rationale and "
            "evidence URLs for these fixed criteria and weights: territory_presence 25%; target_customer_overlap 20%; "
            "problem_solution_overlap 25%; public_traction 15%; offer_strength 10%; evidence_quality 5%. These rate "
            "competitive relevance/presence, not market share. The code will calculate the weighted 0–100 total. Ensure "
            "all six criteria appear per competitor. If there is not enough evidence, say so, lower confidence, and explain "
            "the weak rating.\n\nDo not fabricate downloads, revenue, market size, ranking, or market-share estimates. If public evidence is "
            "incomplete, mark the estimate as such or report the data as unavailable. Keep assumptions and open questions."
        ),
        expected_output="A complete MarketAnalysis with explainable competitor ratings, traceable sources, and testable opportunity hypotheses.",
        agent=reviewer,
        context=[scope, research, opportunities],
        output_pydantic=MarketAnalysis,
    )
    return Crew(
        agents=[market_scout, researcher, strategist, reviewer],
        tasks=[scope, research, opportunities, final],
        process=Process.sequential,
        verbose=False,
        cache=True,
    )
