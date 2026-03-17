import json
import time
from statistics import mean
from typing import Any, Dict, List, Optional

import requests


API_URL = "https://midhunpa-fact-check-bot.hf.space/check"


"""Standalone script to exercise the live /check endpoint.

Request/response contract (derived from backend models):

POST /check
  Request JSON body (backend.models.CheckRequest):
    { "post": <str> }

  Response JSON body (backend.models.CheckResponse serialized):
    {
      "original_post": <str>,
      "is_claim": <bool>,
      "extracted_claim": <str | null>,
      "verdict": <str>,          # Enum backend.models.Verdict
      "response": <str>,
      "sources": [               # Optional list of source objects
         {"title": <str>, "url": <str>, "snippet": <str>},
      ],
      "confidence": <float>,
      "latency_ms": <int>,       # Backend-measured latency
      "bart_label": <str | null>,
      "bart_score": <float | null>,
      "detection_method": <str | null>
    }

This harness measures its own end-to-end latency using time.perf_counter()
in addition to the backend-provided latency_ms.

Verdict normalization
---------------------
The backend uses enum values: "TRUE", "FALSE", "UNVERIFIABLE", "NOT_A_CLAIM".
For comparison with expected verdicts, we normalize API responses into
canonical labels:

  TRUE          -> "TRUE"
  FALSE         -> "FALSE"
  UNVERIFIABLE  -> "UNVERIFIABLE"
  NOT_A_CLAIM   -> "NOT A CLAIM"

We also accept case variations and spaces/underscores (e.g. "not a claim",
"NOT_A_CLAIM") and map them to "NOT A CLAIM".
"""


TEST_CASES: List[Dict[str, Any]] = [
    # FALSE claims
    {
        "id": 1,
        "text": "COVID vaccines contain microchips that track your location",
        "expected_verdict": "FALSE",
        "category": "FALSE",
    },
    {
        "id": 2,
        "text": "The Great Wall of China is visible from space",
        "expected_verdict": "FALSE",
        "category": "FALSE",
    },
    {
        "id": 3,
        "text": "Einstein failed math in school",
        "expected_verdict": "FALSE",
        "category": "FALSE",
    },
    {
        "id": 4,
        "text": "Napoleon was only 5 feet 2 inches tall",
        "expected_verdict": "FALSE",
        "category": "FALSE",
    },
    {
        "id": 5,
        "text": "Humans only use 10% of their brain",
        "expected_verdict": "FALSE",
        "category": "FALSE",
    },

    # TRUE claims
    {
        "id": 6,
        "text": "Elon Musk bought Twitter for $44 billion in 2022",
        "expected_verdict": "TRUE",
        "category": "TRUE",
    },
    {
        "id": 7,
        "text": "The Amazon River is the largest river by discharge",
        "expected_verdict": "TRUE",
        "category": "TRUE",
    },
    {
        "id": 8,
        "text": "Mount Everest is the tallest mountain above sea level",
        "expected_verdict": "TRUE",
        "category": "TRUE",
    },
    {
        "id": 9,
        "text": "Water boils at 100 degrees Celsius at sea level",
        "expected_verdict": "TRUE",
        "category": "TRUE",
    },
    {
        "id": 10,
        "text": "The US has won the most Olympic gold medals in history",
        "expected_verdict": "TRUE",
        "category": "TRUE",
    },

    # UNVERIFIABLE claims
    {
        "id": 11,
        "text": "5G towers are causing health problems in nearby residents",
        "expected_verdict": "UNVERIFIABLE",
        "category": "UNVERIFIABLE",
    },
    {
        "id": 12,
        "text": "The government is hiding evidence of alien contact",
        "expected_verdict": "UNVERIFIABLE",
        "category": "UNVERIFIABLE",
    },

    # NOT A CLAIM
    {
        "id": 13,
        "text": "omg this pizza is so good i cant even rn",
        "expected_verdict": "NOT A CLAIM",
        "category": "NOT A CLAIM",
    },
    {
        "id": 14,
        "text": "what time does the library close on sundays?",
        "expected_verdict": "NOT A CLAIM",
        "category": "NOT A CLAIM",
    },
    {
        "id": 15,
        "text": "Monday should be illegal lmao",
        "expected_verdict": "NOT A CLAIM",
        "category": "NOT A CLAIM",
    },
]


def normalize_verdict(verdict_raw: Any) -> Optional[str]:
    """Normalize API verdict strings to canonical labels for comparison.

    Canonical labels used in this script:
      - "TRUE"
      - "FALSE"
      - "UNVERIFIABLE"
      - "NOT A CLAIM"

    The backend's enum uses "NOT_A_CLAIM"; we map that (and case/spacing
    variations) to "NOT A CLAIM".
    """

    if verdict_raw is None:
        return None

    v = str(verdict_raw).strip()
    if not v:
        return None

    upper = v.upper()

    # Normalize various NOT A CLAIM spellings
    if upper in {"NOT_A_CLAIM", "NOT A CLAIM", "NOT-A-CLAIM"}:
        return "NOT A CLAIM"

    if upper in {"TRUE", "FALSE", "UNVERIFIABLE"}:
        return upper

    # Fallback: upper-case string as-is
    return upper


def safe_get_confidence(data: Dict[str, Any]) -> Optional[float]:
    value = data.get("confidence")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def run_test_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test case against the live API.

    Returns a result dictionary with at least the following keys:
      - id, text, expected_verdict, actual_verdict, category
      - passed (bool)
      - confidence (float | None)
      - latency_ms (float | None)          # client-measured
      - api_latency_ms (int | None)        # if present in response
      - sources_count (int)
      - error (str | None)
    """

    payload = {"post": case["text"]}
    start = time.perf_counter()

    result: Dict[str, Any] = {
        "id": case["id"],
        "text": case["text"],
        "expected_verdict": case["expected_verdict"],
        "actual_verdict": None,
        "category": case["category"],
        "passed": False,
        "confidence": None,
        "latency_ms": None,
        "api_latency_ms": None,
        "sources_count": 0,
        "error": None,
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        result["latency_ms"] = elapsed_ms

        if not (200 <= response.status_code < 300):
            # Non-success HTTP status
            result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
            return result

        try:
            data = response.json()
        except ValueError as exc:  # JSON decode error
            result["error"] = f"JSON decode error: {exc}"
            return result

        raw_verdict = data.get("verdict")
        normalized_verdict = normalize_verdict(raw_verdict)

        if normalized_verdict is None:
            result["error"] = "Missing or invalid 'verdict' in response"
            return result

        result["actual_verdict"] = normalized_verdict
        result["confidence"] = safe_get_confidence(data)

        sources = data.get("sources")
        if isinstance(sources, list):
            result["sources_count"] = len(sources)
        else:
            result["sources_count"] = 0

        api_latency = data.get("latency_ms")
        if isinstance(api_latency, (int, float)):
            result["api_latency_ms"] = int(api_latency)

        # PASS if normalized verdict exactly matches expected
        result["passed"] = normalized_verdict == case["expected_verdict"]

    except requests.RequestException as exc:
        result["error"] = f"Request error: {exc}"

    return result


def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_tests = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    failed = total_tests - passed
    pass_rate = (passed / total_tests * 100.0) if total_tests > 0 else 0.0

    successful_latencies = [
        r["latency_ms"]
        for r in results
        if r.get("latency_ms") is not None and not r.get("error")
    ]
    avg_latency_ms = mean(successful_latencies) if successful_latencies else None

    # Per-category statistics
    categories: Dict[str, Dict[str, int]] = {}
    for r in results:
        cat = r.get("category", "UNKNOWN")
        bucket = categories.setdefault(cat, {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        if r.get("passed"):
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1

    summary: Dict[str, Any] = {
        "total_tests": total_tests,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(pass_rate, 2),
        "average_latency_ms": round(avg_latency_ms, 2) if avg_latency_ms is not None else None,
        "per_category": categories,
    }

    return summary


def print_results(results: List[Dict[str, Any]], summary: Dict[str, Any]) -> None:
    print("=" * 80)
    print("FACT-CHECK BOT LIVE API TESTS")
    print("Endpoint:", API_URL)
    print("=" * 80)
    print()

    # Per-test details
    for r in results:
        status = "PASS" if r.get("passed") else "FAIL"
        print(f"Test {r['id']:>2} [{r['category']}]: {status}")
        print(f"  Text: {r['text']}")
        print(f"  Expected verdict: {r['expected_verdict']}")
        print(f"  Actual verdict:   {r.get('actual_verdict')}")
        print(f"  Confidence:       {r.get('confidence')}")
        print(f"  Latency (ms):     {r.get('latency_ms'):.2f}" if isinstance(r.get("latency_ms"), (int, float)) else f"  Latency (ms):     {r.get('latency_ms')}")
        print(f"  API latency (ms): {r.get('api_latency_ms')}")
        print(f"  Sources count:    {r.get('sources_count')}")
        if r.get("error"):
            print(f"  ERROR: {r['error']}")
        print("-" * 80)

    # Summary
    print()
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed:      {summary['passed']}")
    print(f"Failed:      {summary['failed']}")
    print(f"Pass rate:   {summary['pass_rate']:.2f}%")
    if summary.get("average_latency_ms") is not None:
        print(f"Avg latency (ms) across successful requests: {summary['average_latency_ms']:.2f}")
    else:
        print("Avg latency (ms) across successful requests: N/A")

    print()
    print("RESULTS BY CATEGORY")
    print("=" * 80)
    for cat, stats in summary.get("per_category", {}).items():
        print(f"Category {cat}:")
        print(f"  Total:  {stats['total']}")
        print(f"  Passed: {stats['passed']}")
        print(f"  Failed: {stats['failed']}")
        print("-" * 80)


def write_results_json(results: List[Dict[str, Any]], summary: Dict[str, Any]) -> None:
    """Write structured test results to fact-check-bot/test_results.json.

    The script is intended to be run from the fact-check-bot/ directory, so we
    write to ./test_results.json here. From the project root this resolves to
    fact-check-bot/test_results.json as required.
    """

    payload = {
        "summary": summary,
        "tests": results,
    }

    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    results: List[Dict[str, Any]] = []

    for case in TEST_CASES:
        result = run_test_case(case)
        results.append(result)

    summary = summarize_results(results)
    print_results(results, summary)
    write_results_json(results, summary)


if __name__ == "__main__":
    main()

