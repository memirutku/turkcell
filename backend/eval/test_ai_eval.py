"""AI Evaluation test suite — requires real GEMINI_API_KEY.

Run with: uv run pytest eval/test_ai_eval.py -m ai_eval -v
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest

from eval.eval_runner import compute_category_scores, load_dataset, run_all_evals
from eval.report_generator import generate_console_report, generate_json_report

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


@pytest.mark.ai_eval
class TestAIEvaluation:
    """Full AI evaluation suite across 6 categories."""

    @pytest.fixture(scope="class")
    async def eval_results(self, eval_agent_service):
        """Run all 72 evaluation cases (cached for the class)."""
        results = await run_all_evals(eval_agent_service)
        return results

    @pytest.fixture(scope="class")
    def category_scores(self, eval_results):
        """Compute aggregate scores from results."""
        return compute_category_scores(eval_results)

    async def test_intent_detection(self, eval_results, category_scores):
        """Niyet Algilama: Turkce sorgu → dogru tool secildi mi?"""
        cat = "intent_detection"
        score = category_scores[cat]["score"]
        total = category_scores[cat]["total"]
        passed = category_scores[cat]["passed"]
        logger.info("Intent Detection: %.1f%% (%d/%d)", score * 100, passed, total)

        # Log individual results
        for item in eval_results[cat]:
            r = item["result"]
            status = "PASS" if r.score >= 1.0 else "FAIL"
            logger.info(
                "  [%s] %s: expected=%s actual=%s",
                status,
                r.case_id,
                r.details.get("expected", "?"),
                r.details.get("actual", "?"),
            )

        assert score >= 0.5, f"Intent detection score too low: {score:.1%}"

    async def test_tool_selection(self, eval_results, category_scores):
        """Arac Secimi: Dogru tool + dogru parametreler?"""
        cat = "tool_selection"
        score = category_scores[cat]["score"]
        total = category_scores[cat]["total"]
        passed = category_scores[cat]["passed"]
        logger.info("Tool Selection: %.1f%% (%d/%d)", score * 100, passed, total)

        for item in eval_results[cat]:
            r = item["result"]
            status = "PASS" if r.score >= 1.0 else ("PARTIAL" if r.score > 0 else "FAIL")
            logger.info(
                "  [%s] %s: tool=%s args_match=%s",
                status,
                r.case_id,
                r.details.get("tool_match", False),
                r.details.get("args_match", False),
            )

        assert score >= 0.5, f"Tool selection score too low: {score:.1%}"

    async def test_response_accuracy(self, eval_results, category_scores):
        """Yanit Dogrulugu: AI'in verdigi bilgi mock veriye uyuyor mu?"""
        cat = "response_accuracy"
        score = category_scores[cat]["score"]
        total = category_scores[cat]["total"]
        passed = category_scores[cat]["passed"]
        logger.info("Response Accuracy: %.1f%% (%d/%d)", score * 100, passed, total)

        for item in eval_results[cat]:
            r = item["result"]
            matched = r.details.get("matched_keys", 0)
            total_keys = r.details.get("total_keys", 0)
            logger.info(
                "  [%.0f%%] %s: %d/%d keys matched",
                r.score * 100,
                r.case_id,
                matched,
                total_keys,
            )

        assert score >= 0.5, f"Response accuracy score too low: {score:.1%}"

    async def test_hallucination(self, eval_results, category_scores):
        """Halusinasyon: AI uydurma bilgi uretiyor mu?"""
        cat = "hallucination"
        score = category_scores[cat]["score"]
        total = category_scores[cat]["total"]
        passed = category_scores[cat]["passed"]
        hallucination_rate = 1.0 - score
        logger.info(
            "Hallucination: %.1f%% clean (%d/%d), rate=%.1f%%",
            score * 100,
            passed,
            total,
            hallucination_rate * 100,
        )

        for item in eval_results[cat]:
            r = item["result"]
            status = "CLEAN" if r.score >= 1.0 else "HALLUC"
            details = r.details
            logger.info(
                "  [%s] %s: forbidden=%s missing=%s",
                status,
                r.case_id,
                details.get("found_forbidden", []),
                details.get("missing_required", []),
            )

        assert score >= 0.5, f"Hallucination rate too high: {hallucination_rate:.1%}"

    async def test_recommendation_relevance(self, eval_results, category_scores):
        """Oneri Uygunlugu: Kisisellestirilmis oneri segmente uygun mu?"""
        cat = "recommendation_relevance"
        score = category_scores[cat]["score"]
        total = category_scores[cat]["total"]
        passed = category_scores[cat]["passed"]
        logger.info("Recommendation Relevance: %.1f%% (%d/%d)", score * 100, passed, total)

        for item in eval_results[cat]:
            r = item["result"]
            checks = r.details.get("check_results", {})
            logger.info(
                "  [%.0f%%] %s: %d/%d checks passed",
                r.score * 100,
                r.case_id,
                r.details.get("passed_checks", 0),
                r.details.get("total_checks", 0),
            )

        assert score >= 0.4, f"Recommendation relevance score too low: {score:.1%}"

    async def test_turkish_nlu(self, eval_results, category_scores):
        """Turkce NLU: Farkli Turkce ifadeler ayni intent'e eslenebiliyor mu?"""
        cat = "turkish_nlu"
        score = category_scores[cat]["score"]
        total = category_scores[cat]["total"]
        passed = category_scores[cat]["passed"]
        logger.info("Turkish NLU: %.1f%% (%d/%d variants)", score * 100, passed, total)

        for item in eval_results[cat]:
            case = item["case"]
            for vd in item["variant_details"]:
                status = "PASS" if vd["correct"] else "FAIL"
                logger.info(
                    '  [%s] %s: "%s" -> %s',
                    status,
                    case["id"],
                    vd["query"],
                    vd["actual"],
                )

        assert score >= 0.5, f"Turkish NLU score too low: {score:.1%}"

    async def test_generate_report(self, eval_results, category_scores):
        """Generate and save evaluation report."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        # Console report
        console_output = generate_console_report(category_scores)
        logger.info("\n%s", console_output)

        # JSON report
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_path = RESULTS_DIR / f"eval_report_{timestamp}.json"
        report = generate_json_report(category_scores, eval_results)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        logger.info("Report saved to: %s", report_path)

        # Also write latest report
        latest_path = RESULTS_DIR / "eval_report_latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        assert report_path.exists()
