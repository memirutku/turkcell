"""Deterministic scoring functions for AI evaluation categories."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class EvalResult:
    """Result of a single evaluation run."""

    case_id: str
    category: str
    tool_called: str | None = None
    tool_args: dict = field(default_factory=dict)
    response_text: str = ""
    score: float = 0.0
    details: dict = field(default_factory=dict)
    latency_ms: int = 0
    error: str | None = None


def _normalize_turkish(text: str) -> str:
    """Lowercase with Turkish character normalization."""
    return (
        text.lower()
        .replace("İ", "i")
        .replace("I", "ı")
        .replace("ı", "i")  # normalize to ASCII i for matching
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("ğ", "g")
    )


# -- Category 1: Intent Detection --


def score_intent_detection(case: dict, result: EvalResult) -> float:
    """Binary score: 1.0 if correct tool called, 0.0 otherwise."""
    expected = case.get("expected_tool")

    if expected is None:
        # General chat — no tool should be called
        score = 1.0 if result.tool_called is None else 0.0
        result.details = {
            "expected": "no_tool",
            "actual": result.tool_called or "no_tool",
            "match": score == 1.0,
        }
    else:
        score = 1.0 if result.tool_called == expected else 0.0
        result.details = {
            "expected": expected,
            "actual": result.tool_called or "no_tool",
            "match": score == 1.0,
        }

    result.score = score
    return score


# -- Category 2: Tool Selection + Parameters --


def score_tool_selection(case: dict, result: EvalResult) -> float:
    """1.0 if tool+args match, 0.5 if tool matches but args differ, 0.0 otherwise."""
    expected_tool = case.get("expected_tool")
    expected_args = case.get("expected_args", {})

    if result.tool_called != expected_tool:
        result.score = 0.0
        result.details = {
            "expected_tool": expected_tool,
            "actual_tool": result.tool_called or "no_tool",
            "tool_match": False,
            "args_match": False,
        }
        return 0.0

    # Tool matches — check args
    if not expected_args:
        # No args expected (e.g., get_available_packages)
        result.score = 1.0
        result.details = {
            "expected_tool": expected_tool,
            "actual_tool": result.tool_called,
            "tool_match": True,
            "args_match": True,
            "note": "no_args_required",
        }
        return 1.0

    args_match = True
    mismatches = {}
    for key, expected_val in expected_args.items():
        actual_val = result.tool_args.get(key)
        if str(actual_val) != str(expected_val):
            args_match = False
            mismatches[key] = {"expected": expected_val, "actual": actual_val}

    score = 1.0 if args_match else 0.5
    result.score = score
    result.details = {
        "expected_tool": expected_tool,
        "actual_tool": result.tool_called,
        "tool_match": True,
        "args_match": args_match,
        "expected_args": expected_args,
        "actual_args": result.tool_args,
        "mismatches": mismatches,
    }
    return score


# -- Category 3: Response Accuracy --


def score_response_accuracy(case: dict, result: EvalResult) -> float:
    """Score = matched_keys / total_keys based on expected_values presence in response."""
    expected_values = case.get("expected_values", {})
    if not expected_values:
        result.score = 1.0
        return 1.0

    response_lower = _normalize_turkish(result.response_text)
    matched = 0
    key_results = {}

    for key, acceptable_variants in expected_values.items():
        found = False
        for variant in acceptable_variants:
            if _normalize_turkish(variant) in response_lower:
                found = True
                key_results[key] = {"found": True, "matched_variant": variant}
                break
        if not found:
            key_results[key] = {"found": False, "searched": acceptable_variants}
        matched += int(found)

    score = matched / len(expected_values)
    result.score = score
    result.details = {
        "total_keys": len(expected_values),
        "matched_keys": matched,
        "key_results": key_results,
    }
    return score


# -- Category 4: Hallucination Detection --


def score_hallucination(case: dict, result: EvalResult) -> float:
    """1.0 if response contains required values and no forbidden values, 0.0 otherwise."""
    response_lower = _normalize_turkish(result.response_text)

    required_values = case.get("required_values", [])
    forbidden_values = case.get("forbidden_values", [])
    forbidden_patterns = case.get("forbidden_patterns", [])

    # Check required values
    missing_required = []
    for val in required_values:
        if _normalize_turkish(val) not in response_lower:
            missing_required.append(val)

    # Check forbidden values
    found_forbidden = []
    for val in forbidden_values:
        if _normalize_turkish(val) in response_lower:
            found_forbidden.append(val)

    # Check forbidden patterns (regex)
    found_patterns = []
    for pattern in forbidden_patterns:
        if re.search(pattern, result.response_text, re.IGNORECASE):
            found_patterns.append(pattern)

    has_issues = bool(missing_required or found_forbidden or found_patterns)
    score = 0.0 if has_issues else 1.0

    result.score = score
    result.details = {
        "missing_required": missing_required,
        "found_forbidden": found_forbidden,
        "found_forbidden_patterns": found_patterns,
        "clean": not has_issues,
    }
    return score


# -- Category 5: Recommendation Relevance --


def score_recommendation_relevance(case: dict, result: EvalResult) -> float:
    """Multi-criteria score based on relevance_criteria."""
    criteria = case.get("relevance_criteria", {})
    response_lower = _normalize_turkish(result.response_text)
    total_checks = 0
    passed_checks = 0
    check_results = {}

    # Check if correct tool called
    expected_tools = case.get("expected_tool_any", [])
    if expected_tools:
        total_checks += 1
        tool_ok = result.tool_called in expected_tools
        passed_checks += int(tool_ok)
        check_results["tool_called"] = {
            "passed": tool_ok,
            "expected_any": expected_tools,
            "actual": result.tool_called,
        }

    # Check acceptable tariffs mentioned
    acceptable = criteria.get("acceptable_tariffs", []) + criteria.get("acceptable_packages", [])
    if acceptable:
        total_checks += 1
        found_acceptable = False
        for name in acceptable:
            if _normalize_turkish(name) in response_lower:
                found_acceptable = True
                break
        passed_checks += int(found_acceptable)
        check_results["acceptable_option_mentioned"] = {
            "passed": found_acceptable,
            "searched": acceptable,
        }

    # Check unacceptable tariffs NOT mentioned
    unacceptable = criteria.get("unacceptable_tariffs", []) + criteria.get(
        "unacceptable_packages", []
    )
    if unacceptable:
        total_checks += 1
        found_bad = []
        for name in unacceptable:
            if _normalize_turkish(name) in response_lower:
                found_bad.append(name)
        no_bad = len(found_bad) == 0
        passed_checks += int(no_bad)
        check_results["no_unacceptable_mentioned"] = {
            "passed": no_bad,
            "found_bad": found_bad,
        }

    # Check savings mentioned if expected
    if criteria.get("should_mention_savings"):
        total_checks += 1
        savings_keywords = ["tasarruf", "ucuz", "ekonomik", "indirim", "dusur", "duşur",
                           "kazanc", "avantaj", "uygun", "hesapli"]
        found_savings = any(kw in response_lower for kw in savings_keywords)
        passed_checks += int(found_savings)
        check_results["mentions_savings"] = {"passed": found_savings}

    score = (passed_checks / total_checks) if total_checks > 0 else 0.0
    result.score = score
    result.details = {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "check_results": check_results,
    }
    return score


# -- Category 6: Turkish NLU --


def score_turkish_nlu(case: dict, variant_results: list[EvalResult]) -> float:
    """Score = correct_variants / total_variants."""
    expected_tool = case.get("expected_tool")
    total = len(variant_results)
    correct = 0

    variant_details = []
    for vr in variant_results:
        if expected_tool is None:
            is_correct = vr.tool_called is None
        else:
            is_correct = vr.tool_called == expected_tool
        correct += int(is_correct)
        variant_details.append({
            "query": vr.details.get("query", ""),
            "expected": expected_tool or "no_tool",
            "actual": vr.tool_called or "no_tool",
            "correct": is_correct,
        })

    score = correct / total if total > 0 else 0.0
    return score, variant_details
