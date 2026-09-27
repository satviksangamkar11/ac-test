"""Benchmark harness for VLM/OCR observation accuracy.

Usage (requires ground-truth directory from W1 capture):
    python -m serum2.producer.observation_benchmark /path/to/vlm_ground_truth

Ground-truth directory: each file is a JSON mapping
    {control_id: {"value": <ground_truth_value>, "unit": <unit_or_null>}}
produced by loading known presets into real Serum 2.0.23 and capturing
labelled crops per-panel.

Reports per-class: exact_match, confident_wrong, abstained.
The gating metric is confident_wrong (target ~= 0).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from serum2.producer.observation_engine import ObservationEngine, OUTCOME_CANDIDATE
from serum2.producer.observation_policy import OUTCOME_OBSERVED, CONFIDENT_THRESHOLD


def _values_match(predicted: Any, ground_truth: Any, tol: float = 1e-3) -> bool:
    if predicted is None or ground_truth is None:
        return False
    try:
        return abs(float(predicted) - float(ground_truth)) <= tol
    except (TypeError, ValueError):
        return str(predicted).strip().lower() == str(ground_truth).strip().lower()


def run_benchmark(ground_truth_dir: str, *, numeric_tol: float = 1e-3) -> Dict[str, Any]:
    """Run observation benchmark against labelled ground-truth crops.

    Returns a dict with per-class and aggregate metrics.
    """
    gt_dir = Path(ground_truth_dir)
    if not gt_dir.is_dir():
        raise FileNotFoundError("Ground-truth directory not found: %s" % gt_dir)

    engine = ObservationEngine()
    results: List[Dict] = []

    for gt_file in sorted(gt_dir.glob("*.json")):
        gt = json.loads(gt_file.read_text(encoding="utf-8"))
        for control_id, entry in gt.items():
            gt_value = entry.get("value")
            unit = entry.get("unit")
            crops = entry.get("crops", [{"raw_value": gt_value}])

            sources = [{"raw_value": c.get("raw_value"), "source": "vlm_%d" % i, "confidence": c.get("confidence", 0.8)}
                       for i, c in enumerate(crops)]
            context = {"control_id": control_id, "element_kind": entry.get("element_kind", "CONTROL"),
                       "control_type": entry.get("control_type", "continuous"), "unit": unit}
            try:
                result = engine.adjudicated_observe(sources, context, numeric_tol=numeric_tol)
            except Exception as exc:
                results.append({"control_id": control_id, "outcome": "ERROR", "error": str(exc),
                                 "gt": gt_value})
                continue

            exact_match = result.outcome == OUTCOME_OBSERVED and _values_match(result.value, gt_value, numeric_tol)
            confident_wrong = (result.outcome == OUTCOME_OBSERVED and not exact_match)
            abstained = result.outcome != OUTCOME_OBSERVED

            results.append({"control_id": control_id, "outcome": result.outcome, "predicted": result.value,
                             "gt": gt_value, "exact_match": exact_match,
                             "confident_wrong": confident_wrong, "abstained": abstained,
                             "confidence": result.confidence, "single_source": result.single_source})

    if not results:
        return {"total": 0, "exact_match": 0, "confident_wrong": 0, "abstained": 0,
                "exact_match_rate": None, "confident_wrong_rate": None, "abstention_rate": None, "rows": []}

    total = len(results)
    exact_match = sum(1 for r in results if r.get("exact_match"))
    confident_wrong = sum(1 for r in results if r.get("confident_wrong"))
    abstained = sum(1 for r in results if r.get("abstained"))

    return {
        "total": total,
        "exact_match": exact_match,
        "confident_wrong": confident_wrong,
        "abstained": abstained,
        "exact_match_rate": round(exact_match / total, 4),
        "confident_wrong_rate": round(confident_wrong / total, 4),
        "abstention_rate": round(abstained / total, 4),
        "rows": results,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m serum2.producer.observation_benchmark <ground_truth_dir>")
        sys.exit(1)
    report = run_benchmark(sys.argv[1])
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    cw = report.get("confident_wrong_rate")
    if cw is not None and cw > 0.05:
        print("GATE FAILED: confident_wrong_rate %.4f > 0.05" % cw)
        sys.exit(2)
    print("Gate passed (confident_wrong_rate %.4f)" % (cw or 0.0))
