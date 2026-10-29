from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
import argparse

from market_opportunity_analyst.crew import WEIGHTS, create_market_crew
from market_opportunity_analyst.schemas import MarketAnalysis


def _ranking(analysis: MarketAnalysis) -> list[dict[str, object]]:
    ranked: list[dict[str, object]] = []
    for competitor in analysis.competitors:
        by_criterion = {rating.criterion: rating for rating in competitor.ratings}
        detail: list[dict[str, object]] = []
        total = 0.0
        for criterion, weight in WEIGHTS.items():
            rating = by_criterion.get(criterion)
            score = rating.score if rating else 1
            rationale = rating.rationale if rating else "No assessment supplied; minimum score used pending evidence."
            evidence_urls = rating.evidence_urls if rating else []
            weighted = weight * score / 5
            total += weighted
            detail.append({
                "criterion": criterion,
                "weight_percent": weight,
                "rating_1_to_5": score,
                "weighted_points": round(weighted, 2),
                "rationale": rationale,
                "evidence_urls": evidence_urls,
            })
        ranked.append({
            "name": competitor.name,
            "directness": competitor.directness,
            "score_0_to_100": round(total, 2),
            "rating_coverage": f"{len(by_criterion)}/{len(WEIGHTS)} criteria supplied",
            "criteria": detail,
        })
    ranked.sort(key=lambda item: float(item["score_0_to_100"]), reverse=True)
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    return ranked


def _render_markdown(analysis: MarketAnalysis, ranking: list[dict[str, object]]) -> str:
    lines = [
        f"# Análisis de mercado: {analysis.product_idea}",
        "",
        f"**Territorio:** {analysis.territory}  ",
        f"**Consulta:** {date.today().isoformat()}",
        "",
        "## Resumen ejecutivo",
        "",
        analysis.executive_summary,
        "",
        "## Definición del mercado",
        "",
        analysis.market_definition,
    ]

    def bullets(title: str, values: list[str]) -> None:
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {value}" for value in values if value)
        if not values:
            lines.append("_Sin información suficiente._")

    bullets("Supuestos", analysis.assumptions)
    bullets("Preguntas abiertas", analysis.open_questions)
    bullets("Señales de demanda", analysis.demand_signals)
    bullets("Contexto y restricciones del mercado", analysis.market_context_and_constraints)
    bullets("Patrones de modelo de negocio", analysis.business_model_patterns)
    lines.extend([
        "",
        "## Ranking de competidores",
        "",
        "El score expresa cercanía competitiva para esta idea y territorio; no es cuota de mercado ni valoración empresarial.",
        "",
        "| # | Competidor | Tipo | Score / 100 | Cobertura de criterios |",
        "|---:|---|---|---:|---|",
    ])
    for item in ranking:
        lines.append(
            f"| {item['rank']} | {item['name']} | {item['directness']} | {item['score_0_to_100']:.2f} | {item['rating_coverage']} |"
        )
    lines.extend(["", "### Pesos y puntuación", "", analysis.ranking_methodology, ""])
    for item in ranking:
        lines.extend([f"#### {item['rank']}. {item['name']}", ""])
        for criterion in item["criteria"]:
            lines.append(
                f"- **{criterion['criterion']}** — {criterion['rating_1_to_5']}/5 × {criterion['weight_percent']}% "
                f"= {criterion['weighted_points']} puntos. {criterion['rationale']}"
            )
            for url in criterion["evidence_urls"]:
                lines.append(f"  - Evidencia: {url}")
        lines.append("")

    lines.extend(["## Perfiles de competidores", ""])
    for competitor in analysis.competitors:
        lines.extend([
            f"### {competitor.name} ({competitor.directness})",
            "",
            f"- **Presencia territorial:** {competitor.territory_presence}",
            f"- **Clientes objetivo:** {'; '.join(competitor.target_customers) or 'No determinado'}",
            f"- **Propuesta de valor:** {competitor.value_proposition}",
            f"- **Producto/servicio:** {competitor.product_and_service}",
            f"- **Modelo de negocio:** {competitor.business_model}",
            f"- **Ingresos:** {'; '.join(competitor.revenue_streams) or 'No públicos/no determinados'}",
            f"- **Precios:** {competitor.pricing}",
            f"- **Adquisición y distribución:** {'; '.join(competitor.go_to_market) or 'No determinado'}",
            f"- **Señales de tracción:** {'; '.join(competitor.traction_signals) or 'No hay evidencia pública suficiente'}",
            f"- **Fortalezas:** {'; '.join(competitor.strengths) or 'No determinadas'}",
            f"- **Debilidades o brechas:** {'; '.join(competitor.weaknesses_or_gaps) or 'No determinadas'}",
        ])
        if competitor.unknowns:
            lines.append("- **Datos desconocidos:** " + "; ".join(competitor.unknowns))
        if competitor.evidence:
            lines.append("- **Fuentes:**")
            lines.extend(f"  - [{source.title}]({source.url}) — {source.publisher}, {source.source_type}, {source.status}, consultado {source.accessed_on}. {source.claim}" for source in competitor.evidence)
        lines.append("")

    lines.extend(["## Áreas de oportunidad", ""])
    for index, opportunity in enumerate(analysis.opportunity_areas, start=1):
        lines.extend([
            f"### {index}. {opportunity.title}",
            "",
            f"- **Segmento:** {opportunity.target_segment}",
            f"- **Necesidad no atendida:** {opportunity.unmet_need}",
            f"- **Brecha observada:** {opportunity.why_existing_options_leave_room}",
            f"- **Wedge de producto:** {opportunity.product_wedge}",
            f"- **Modelo de negocio posible:** {opportunity.possible_business_model}",
            f"- **Experimento de validación:** {opportunity.validation_experiment}",
            f"- **Confianza:** {opportunity.confidence}",
        ])
        if opportunity.evidence_of_gap:
            lines.append("- **Evidencia de la brecha:** " + "; ".join(opportunity.evidence_of_gap))
        if opportunity.key_risks:
            lines.append("- **Riesgos:** " + "; ".join(opportunity.key_risks))
        if opportunity.evidence_urls:
            lines.append("- **Fuentes:** " + "; ".join(opportunity.evidence_urls))
        lines.append("")

    lines.extend(["## Posicionamiento recomendado", "", analysis.recommended_positioning])
    bullets("Plan de validación de 30 días", analysis.validation_plan_30_days)
    bullets("Limitaciones", analysis.limitations)
    lines.extend(["", "## Fuentes consultadas", ""])
    for source in analysis.sources:
        lines.append(f"- [{source.title}]({source.url}) — {source.publisher}; {source.source_type}; {source.status}; consultado {source.accessed_on}. {source.claim}")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Research competitors and market opportunities for a product idea.")
    parser.add_argument("--idea", required=True, help="Product idea")
    parser.add_argument("--territory", required=True, help="Geographic scope, such as Mexico or Mexico City")
    parser.add_argument("--constraints", default="No additional constraints supplied; infer cautiously and mark assumptions.", help="Optional segment, budget, channel, or product constraints")
    parser.add_argument("--country-code", default="", help="Optional two-letter local search country code, for example mx")
    parser.add_argument("--language", default="", help="Optional two-letter search language code, for example es")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Report output directory")
    args = parser.parse_args()
    if not args.idea.strip() or not args.territory.strip():
        parser.error("--idea and --territory cannot be empty")
    if not os.getenv("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is required for the default OpenAI model (or configure another provider).")
    if not os.getenv("SERPER_API_KEY"):
        parser.error("SERPER_API_KEY is required for the requested current web research.")
    if args.country_code:
        os.environ["MARKET_SEARCH_COUNTRY"] = args.country_code.lower()
    elif "méxico" in args.territory.lower() or "mexico" in args.territory.lower():
        os.environ["MARKET_SEARCH_COUNTRY"] = "mx"
    if args.language:
        os.environ["MARKET_SEARCH_LANGUAGE"] = args.language.lower()
    elif "méxico" in args.territory.lower() or "mexico" in args.territory.lower():
        os.environ["MARKET_SEARCH_LANGUAGE"] = "es"
    try:
        crew = create_market_crew()
        result = crew.kickoff(inputs={"idea": args.idea, "territory": args.territory, "constraints": args.constraints})
        output = result.pydantic
        if isinstance(output, MarketAnalysis):
            analysis = output
        elif output is not None:
            analysis = MarketAnalysis.model_validate(output.model_dump() if hasattr(output, "model_dump") else output)
        else:
            raise ValueError("The final task did not return a structured MarketAnalysis.")
        ranking = _ranking(analysis)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", f"{args.idea}-{args.territory}".lower()).strip("-")[:64] or "market-analysis"
        markdown_path = args.output_dir / f"{slug}-market-opportunities.md"
        json_path = args.output_dir / f"{slug}-market-opportunities.json"
        markdown_path.write_text(_render_markdown(analysis, ranking), encoding="utf-8")
        json_path.write_text(json.dumps({"analysis": analysis.model_dump(mode="json"), "ranking": ranking, "weights": WEIGHTS}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"Market analysis failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"Created reports:\n- {markdown_path}\n- {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
