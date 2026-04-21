"""Core evaluation engine: runs scenarios against the real Gemini LLM."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from eval.eval_scoring import EvalResult

logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).parent / "dataset" / "eval_cases.json"


def load_dataset() -> dict:
    """Load evaluation dataset from JSON."""
    with open(DATASET_PATH) as f:
        return json.load(f)


async def run_single_eval(
    agent_service,
    case_id: str,
    customer_id: str,
    query: str,
) -> EvalResult:
    """Run a single query through the agent and capture tool calls + response.

    Returns an EvalResult with tool_called, tool_args, and response_text populated.
    """
    result = EvalResult(case_id=case_id, category="")

    config = {"configurable": {"thread_id": f"eval-{case_id}-{int(time.time())}"}}
    input_state = {
        "messages": [HumanMessage(content=query)],
        "customer_id": customer_id,
        "session_id": f"eval-{case_id}",
        "intent": None,
        "proposed_action": None,
        "action_result": None,
        "rag_context": "",
        "customer_context": "",
    }

    start = time.monotonic()

    try:
        tool_calls_found = []
        tokens = []

        async for event in agent_service._graph.astream_events(
            input_state, config=config, version="v2"
        ):
            kind = event["event"]

            # Capture LLM tokens
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    # Gemini may return content as str or list of parts
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, str):
                                tokens.append(part)
                            elif isinstance(part, dict) and "text" in part:
                                tokens.append(part["text"])
                    else:
                        tokens.append(str(content))

            # Capture tool invocations
            elif kind == "on_tool_start":
                tool_name = event.get("name", "")
                tool_input = event.get("data", {}).get("input", {})
                tool_calls_found.append({"name": tool_name, "args": tool_input})

        # Also check for interrupted state (destructive actions)
        graph_state = agent_service._graph.get_state(config)
        if graph_state.next and graph_state.tasks:
            for task in graph_state.tasks:
                if hasattr(task, "interrupts") and task.interrupts:
                    # Interrupted = tool was selected but execution paused
                    # Extract from the last AIMessage in state
                    for msg in reversed(graph_state.values.get("messages", [])):
                        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                if tc["name"] not in [t["name"] for t in tool_calls_found]:
                                    tool_calls_found.append({
                                        "name": tc["name"],
                                        "args": tc.get("args", {}),
                                    })
                            break

        result.response_text = "".join(tokens)
        if tool_calls_found:
            result.tool_called = tool_calls_found[0]["name"]
            result.tool_args = tool_calls_found[0].get("args", {})
        else:
            result.tool_called = None
            result.tool_args = {}

    except Exception as e:
        logger.error("Eval case %s failed: %s", case_id, e, exc_info=True)
        result.error = str(e)
        result.response_text = ""
        result.tool_called = None

    result.latency_ms = int((time.monotonic() - start) * 1000)
    return result


async def run_all_evals(agent_service) -> dict:
    """Run all evaluation cases and return categorized results.

    Returns a dict with category names as keys, each containing a list of
    (case, result) tuples and an aggregate score.
    """
    from eval.eval_scoring import (
        score_hallucination,
        score_intent_detection,
        score_recommendation_relevance,
        score_response_accuracy,
        score_tool_selection,
        score_turkish_nlu,
    )

    dataset = load_dataset()
    cases = dataset["cases"]

    results_by_category: dict[str, list] = {
        "intent_detection": [],
        "tool_selection": [],
        "response_accuracy": [],
        "hallucination": [],
        "recommendation_relevance": [],
        "turkish_nlu": [],
    }

    for case in cases:
        cat = case["category"]
        case_id = case["id"]
        customer_id = case["customer_id"]

        if cat == "turkish_nlu":
            # Run each query variant
            queries = case.get("queries", [])
            variant_results = []
            for i, q in enumerate(queries):
                vr = await run_single_eval(agent_service, f"{case_id}-v{i}", customer_id, q)
                vr.category = cat
                vr.details["query"] = q
                variant_results.append(vr)

            score, variant_details = score_turkish_nlu(case, variant_results)
            results_by_category[cat].append({
                "case": case,
                "score": score,
                "variant_details": variant_details,
                "variant_results": variant_results,
            })
        else:
            query = case["query"]
            result = await run_single_eval(agent_service, case_id, customer_id, query)
            result.category = cat

            # Score based on category
            if cat == "intent_detection":
                score_intent_detection(case, result)
            elif cat == "tool_selection":
                score_tool_selection(case, result)
            elif cat == "response_accuracy":
                score_response_accuracy(case, result)
            elif cat == "hallucination":
                score_hallucination(case, result)
            elif cat == "recommendation_relevance":
                score_recommendation_relevance(case, result)

            results_by_category[cat].append({
                "case": case,
                "result": result,
            })

    return results_by_category


def compute_category_scores(results_by_category: dict) -> dict:
    """Compute aggregate scores per category."""
    summary = {}

    for cat, items in results_by_category.items():
        if cat == "turkish_nlu":
            total_variants = 0
            correct_variants = 0
            for item in items:
                for vd in item["variant_details"]:
                    total_variants += 1
                    correct_variants += int(vd["correct"])
            score = correct_variants / total_variants if total_variants > 0 else 0.0
            summary[cat] = {
                "score": score,
                "passed": correct_variants,
                "total": total_variants,
                "cases": len(items),
            }
        else:
            scores = [item["result"].score for item in items]
            avg = sum(scores) / len(scores) if scores else 0.0
            passed = sum(1 for s in scores if s >= 1.0)
            summary[cat] = {
                "score": avg,
                "passed": passed,
                "total": len(scores),
                "cases": len(items),
            }

    # Overall
    all_scores = [s["score"] for s in summary.values()]
    summary["overall"] = {
        "score": sum(all_scores) / len(all_scores) if all_scores else 0.0,
        "total_categories": len(all_scores),
    }

    return summary
