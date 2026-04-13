"""
Output parsing layer for the Big-O Complexity Estimator.
Safely extracts and validates JSON from LLM responses.
Robust against models that write prose before/after JSON (e.g. codellama).
"""

import json
import re


REQUIRED_KEYS = {"time_complexity", "space_complexity", "reasoning"}


def _repair_json(s: str) -> str:
    """Light repairs: strip trailing commas before } or ]."""
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s


def _try_parse(json_str: str):
    """Try to parse json_str; return dict or None."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_repair_json(json_str))
    except json.JSONDecodeError:
        return None


def _extract_json_string(text: str) -> dict | None:
    """
    Try multiple strategies to find a valid JSON object that contains
    at least the required keys. Returns parsed dict or None.
    """
    # Strategy 1: ```json ... ``` fences
    for m in re.finditer(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL):
        data = _try_parse(m.group(1).strip())
        if data and REQUIRED_KEYS.issubset(data.keys()):
            return data

    # Strategy 2: scan ALL { ... } blocks, prefer the last valid one
    # Use a brace-depth scanner to find balanced blocks
    candidates = []
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start:i + 1])
                start = None

    # Walk candidates in reverse — last JSON block is most likely the answer
    for block in reversed(candidates):
        data = _try_parse(block)
        if data and REQUIRED_KEYS.issubset(data.keys()):
            return data

    # Strategy 3: any candidate even without required keys (best effort)
    for block in reversed(candidates):
        data = _try_parse(block)
        if data and isinstance(data, dict):
            return data

    return None


def parse_output(text: str) -> dict:
    """
    Parse LLM output into a structured result dict.
    Returns a fallback dict if parsing fails.
    """
    if not text or not text.strip():
        return _fallback("Empty response from model")

    data = _extract_json_string(text)

    if data is None:
        return _fallback("No JSON object found in model output")

    if not REQUIRED_KEYS.issubset(data.keys()):
        missing = REQUIRED_KEYS - set(data.keys())
        return _fallback(f"Missing keys in response: {missing}")

    return {
        "language": str(data.get("language", "Unknown")),
        "time_complexity": str(data["time_complexity"]),
        "space_complexity": str(data["space_complexity"]),
        "best_case": str(data.get("best_case", data["time_complexity"])),
        "worst_case": str(data.get("worst_case", data["time_complexity"])),
        "reasoning": str(data["reasoning"]),
        "better_possible": str(data.get("better_possible", "N/A")),
        "suggested_algorithm": str(data.get("suggested_algorithm", "N/A")),
        "expected_complexity": str(data.get("expected_complexity", "N/A")),
        "optimization_reason": str(data.get("optimization_reason", "N/A")),
        "confidence": _safe_confidence(data.get("confidence")),
        "success": True,
        "raw_char_count": len(text),
    }


def parse_batch_output(text: str) -> dict:
    """Alias for parse_output — used for batch analysis results."""
    return parse_output(text)


def _safe_confidence(val) -> float:
    """Parse confidence to a float in [0.0, 1.0], default 0.5."""
    try:
        f = float(val)
        return max(0.0, min(1.0, f))
    except (TypeError, ValueError):
        return 0.5


def _fallback(error_msg: str) -> dict:
    """Return a graceful fallback result."""
    return {
        "language": "Unknown",
        "time_complexity": "Unknown",
        "space_complexity": "Unknown",
        "best_case": "Unknown",
        "worst_case": "Unknown",
        "reasoning": f"Analysis failed — {error_msg}",
        "better_possible": "N/A",
        "suggested_algorithm": "N/A",
        "expected_complexity": "N/A",
        "optimization_reason": "N/A",
        "confidence": 0.0,
        "success": False,
        "raw_char_count": 0,
    }
