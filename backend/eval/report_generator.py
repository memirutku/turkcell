"""Report generation for AI evaluation results."""

from __future__ import annotations

from datetime import datetime, timezone

CATEGORY_LABELS = {
    "intent_detection": "Niyet Algilama Dogrulugu",
    "tool_selection": "Arac Secimi Dogrulugu",
    "response_accuracy": "Yanit Dogrulugu",
    "hallucination": "Halusinasyon Temizligi",
    "recommendation_relevance": "Oneri Uygunlugu",
    "turkish_nlu": "Turkce NLU Kalitesi",
}


def generate_console_report(category_scores: dict) -> str:
    """Generate a formatted console table for the evaluation results."""
    lines = []
    lines.append("")
    lines.append("=" * 64)
    lines.append("  Umay AI-Gen — Yapay Zeka Degerlendirme Raporu")
    lines.append("=" * 64)
    lines.append(f"  {'Kategori':<32} {'Skor':>8}   {'Detay':<18}")
    lines.append("-" * 64)

    for cat_key, label in CATEGORY_LABELS.items():
        if cat_key not in category_scores:
            continue
        cat = category_scores[cat_key]
        score_pct = f"%{cat['score'] * 100:.1f}"
        passed = cat.get("passed", 0)
        total = cat.get("total", 0)

        if cat_key == "hallucination":
            detail = f"{passed}/{total} temiz"
        elif cat_key == "turkish_nlu":
            detail = f"{passed}/{total} varyant"
        else:
            detail = f"{passed}/{total} basarili"

        lines.append(f"  {label:<32} {score_pct:>8}   {detail:<18}")

    lines.append("-" * 64)

    overall = category_scores.get("overall", {})
    overall_pct = f"%{overall.get('score', 0) * 100:.1f}"
    total_cases = sum(
        c.get("total", 0) for k, c in category_scores.items() if k != "overall"
    )
    lines.append(f"  {'GENEL AI BASARISI':<32} {overall_pct:>8}   {total_cases} degerlendirme")
    lines.append("=" * 64)
    lines.append("")
    lines.append(
        "  * Metrikler Gemini 2.5 Flash (temperature=0) ile olculmustur."
    )
    lines.append("")

    return "\n".join(lines)


def generate_json_report(category_scores: dict, eval_results: dict) -> dict:
    """Generate a JSON-serializable report."""
    report = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "model": "gemini-2.5-flash",
        "temperature": 0,
        "categories": {},
        "overall": category_scores.get("overall", {}),
    }

    for cat_key, label in CATEGORY_LABELS.items():
        if cat_key not in category_scores:
            continue
        cat_score = category_scores[cat_key]

        case_details = []
        if cat_key in eval_results:
            for item in eval_results[cat_key]:
                if cat_key == "turkish_nlu":
                    case_details.append({
                        "case_id": item["case"]["id"],
                        "score": item["score"],
                        "variant_details": item["variant_details"],
                    })
                else:
                    r = item["result"]
                    case_details.append({
                        "case_id": r.case_id,
                        "score": r.score,
                        "tool_called": r.tool_called,
                        "latency_ms": r.latency_ms,
                        "details": r.details,
                        "error": r.error,
                    })

        report["categories"][cat_key] = {
            "label": label,
            "score": cat_score["score"],
            "passed": cat_score.get("passed", 0),
            "total": cat_score.get("total", 0),
            "cases": case_details,
        }

    # Total scenarios count
    total = sum(
        c.get("total", 0) for k, c in category_scores.items() if k != "overall"
    )
    report["total_evaluations"] = total

    return report
