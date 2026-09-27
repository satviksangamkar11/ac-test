"""C3: local VLM/OCR observation benchmark.

Reuses the existing authority (observation_engine.ObservationEngine +
observation_policy.adjudicate/CONFIDENT_THRESHOLD) -- this module adds no new
adjudication logic, only a benchmark harness and a labelled case set.

Case provenance is one of:
  REAL_W1_EVIDENCE   -- real Serum 2.0.23 ground truth (parameter_characterization/
                        vlm_ground_truth/labels.json) + a REAL local Qwen2.5-VL-3B-Instruct
                        inference run against the real crop image (this session,
                        serum2/producer/c3_benchmark/vlm_raw_outputs.json). Confidence is the
                        real mean per-token generation probability, not a placeholder.
  REAL_MISSING_EVIDENCE -- a W1 case where the underlying screenshot capture itself failed
                        (documented in W1/vlm_ground_truth/labels.json's failed_capture_attempts).
                        No VLM/OCR was run because there is no valid crop to run it against.
  SYNTHETIC           -- hand-authored ObservationCandidate values used to exercise policy
                        behavior (ambiguity, wrong-OCR, wrong-VLM, unit-format difference,
                        boolean/enum, identity mismatch, high-confidence-wrong) that the 2
                        real captured crops cannot exercise on their own. Never presented as
                        real Serum ground truth.

OCR: no local OCR engine (pytesseract / easyocr / system tesseract) is installed or
cached in this environment (checked this session). OCR columns are recorded as
"OCR_ENGINE_UNAVAILABLE" -- not fabricated -- for every REAL case.
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from serum2.producer.observation_engine import ObservationEngine
from serum2.producer.observation_policy import (
    ObservationCandidate, OUTCOME_CANDIDATE, OUTCOME_OBSERVED, OUTCOME_AMBIGUOUS,
    OUTCOME_UNREADABLE, CONFIDENT_THRESHOLD, adjudicate,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OCR_STATUS = "OCR_ENGINE_UNAVAILABLE"


def _values_match(predicted, ground_truth, tol=1e-3):
    if predicted is None or ground_truth is None:
        return False
    try:
        return abs(float(predicted) - float(ground_truth)) <= tol
    except (TypeError, ValueError):
        return str(predicted).strip().lower() == str(ground_truth).strip().lower()


def _numeric_from_vlm_text(s):
    """Best-effort numeric parse of a raw VLM string, e.g. '1.00 s' -> 1.0, '20' -> 20.0."""
    import re
    m = re.search(r"[+-]?\d+(?:\.\d+)?", s or "")
    return float(m.group(0)) if m else None


def build_real_cases():
    """REAL_W1_EVIDENCE + REAL_MISSING_EVIDENCE cases from committed W1 ground truth
    and this session's real local VLM run. No values invented."""
    labels = json.loads((REPO / "parameter_characterization" / "vlm_ground_truth" / "labels.json").read_text(encoding="utf-8"))
    vlm_raw = json.loads((HERE / "vlm_raw_outputs.json").read_text(encoding="utf-8"))
    vlm_by_id = {r["control_id"]: r for r in vlm_raw}

    cases = []

    # BULK_01 capture -> ground truth DEC = 1.00 s (native_values["DEC"])
    cap0 = labels["captures"][0]
    gt0 = float(cap0["native_values"]["DEC"].replace(" s", "").strip())
    vlm0 = vlm_by_id["env2.decay"]
    cases.append({
        "case_id": "real_bulk01_env1_decay",
        "provenance": "REAL_W1_EVIDENCE",
        "control_id": "env2.decay",
        "atlas_id": "env2.decay",
        "ground_truth_value": gt0,
        "ground_truth_unit": "s",
        "ground_truth_source": cap0["screenshot_file"],
        "ground_truth_readable": True,
        "raw_vlm_output": vlm0["raw_vlm_output"],
        "vlm_numeric": _numeric_from_vlm_text(vlm0["raw_vlm_output"]),
        "vlm_confidence": vlm0["mean_token_prob"],
        "ocr_output": OCR_STATUS,
        "ocr_numeric": None,
    })

    # CAL_06 capture -> ground truth DEC = 1.00 s
    cap1 = labels["captures"][1]
    gt1 = float(cap1["native_values"]["DEC"].replace(" s", "").strip())
    vlm1 = vlm_by_id["env2.decay_cal06"]
    cases.append({
        "case_id": "real_cal06_env1_decay",
        "provenance": "REAL_W1_EVIDENCE",
        "control_id": "env2.decay",
        "atlas_id": "env2.decay",
        "ground_truth_value": gt1,
        "ground_truth_unit": "s",
        "ground_truth_source": cap1["screenshot_file"],
        "ground_truth_readable": True,
        "raw_vlm_output": vlm1["raw_vlm_output"],
        "vlm_numeric": _numeric_from_vlm_text(vlm1["raw_vlm_output"]),
        "vlm_confidence": vlm1["mean_token_prob"],
        "ocr_output": OCR_STATUS,
        "ocr_numeric": None,
    })

    # The documented failed tooltip capture: evidence itself never persisted -> no VLM/OCR run
    fail = labels["failed_capture_attempts"][0]
    cases.append({
        "case_id": "real_missing_filter1_cutoff_tooltip",
        "provenance": "REAL_MISSING_EVIDENCE",
        "control_id": fail["control_id"],
        "atlas_id": fail["control_id"],
        "ground_truth_value": None,
        "ground_truth_unit": None,
        "ground_truth_source": fail["screenshot_file"],
        "ground_truth_readable": False,
        "raw_vlm_output": None,
        "vlm_numeric": None,
        "vlm_confidence": None,
        "ocr_output": OCR_STATUS,
        "ocr_numeric": None,
        "note": fail["reason"],
    })
    return cases


def build_synthetic_cases():
    """SYNTHETIC adversarial cases -- hand-authored, clearly labelled, never presented as
    real Serum ground truth. Each exercises one failure mode the 2 real crops cannot."""
    return [
        {
            "case_id": "synthetic_ambiguous_numeric_split",
            "provenance": "SYNTHETIC",
            "description": "VLM and OCR disagree on a numeric value with both above threshold -- must resolve AMBIGUOUS, not average or pick one.",
            "control_id": "synthetic.filter1.cutoff",
            "ground_truth_value": 172.0, "ground_truth_unit": "Hz", "ground_truth_readable": True,
            "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=172.0, confidence=0.95, source="vlm"),
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=612.0, confidence=0.93, source="ocr"),
            ],
        },
        {
            "case_id": "synthetic_wrong_ocr_correct_vlm_agree_fails",
            "provenance": "SYNTHETIC",
            "description": "OCR misreads digits; VLM is correct. Sources disagree -> must abstain (AMBIGUOUS), not silently trust VLM.",
            "control_id": "synthetic.env1.attack",
            "ground_truth_value": 5.0, "ground_truth_unit": "ms", "ground_truth_readable": True,
            "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=5.0, confidence=0.92, source="vlm"),
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=8.0, confidence=0.91, source="ocr"),
            ],
        },
        {
            "case_id": "synthetic_wrong_vlm_high_confidence",
            "provenance": "SYNTHETIC",
            "description": "The critical safety case: a single VLM source is confidently WRONG (>= CONFIDENT_THRESHOLD). Policy must not admit a single overconfident wrong source as fact -- this case is the direct test of the confident-wrong gate.",
            "control_id": "synthetic.env2.release",
            "ground_truth_value": 15.0, "ground_truth_unit": "ms", "ground_truth_readable": True,
            "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=1500.0, confidence=0.97, source="vlm"),
            ],
        },
        {
            "case_id": "synthetic_correct_unit_format_difference",
            "provenance": "SYNTHETIC",
            "description": "Two sources agree on the numeric value but format units differently upstream (both already normalized to the same unit by the NUMERIC strategy before adjudication) -- must still resolve OBSERVED.",
            "control_id": "synthetic.env1.decay",
            "ground_truth_value": 1.0, "ground_truth_unit": "s", "ground_truth_readable": True,
            "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=1.0, confidence=0.94, source="vlm"),
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=1.0, confidence=0.90, source="ocr"),
            ],
        },
        {
            "case_id": "synthetic_boolean_state_agree",
            "provenance": "SYNTHETIC",
            "description": "Boolean/toggle state (filter enabled) with agreeing sources -- must resolve OBSERVED with the correct ON/OFF value, not a numeric coercion.",
            "control_id": "synthetic.filter1.enabled",
            "ground_truth_value": "ON", "ground_truth_unit": None, "ground_truth_readable": True,
            "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value="ON", confidence=1.0, source="vlm"),
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value="ON", confidence=1.0, source="ocr"),
            ],
        },
        {
            "case_id": "synthetic_enum_mode_wrong_single_source_high_conf",
            "provenance": "SYNTHETIC",
            "description": "Single-source enum/mode read, confidently WRONG mode name (LFO shape). Must not be admitted as fact from one overconfident source.",
            "control_id": "synthetic.lfo1.shape",
            "ground_truth_value": "random_sh", "ground_truth_unit": None, "ground_truth_readable": True,
            "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value="rossler", confidence=0.96, source="vlm"),
            ],
        },
        {
            "case_id": "synthetic_identity_mismatch_env1_vs_env2",
            "provenance": "SYNTHETIC",
            "description": "VLM answers with the RIGHT value but for the WRONG control identity (env1.decay instead of the requested env2.decay) -- exercises the requirement that a correct-looking number for a substituted parameter must not be accepted as this control's observation. Modeled here as a wrong value against the REQUESTED control's ground truth, since the adjudicator has no cross-control identity check of its own -- surfaced as a genuine architecture gap, not papered over.",
            "control_id": "env2.decay",
            "ground_truth_value": 5.0, "ground_truth_unit": "s", "ground_truth_readable": True,
            "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=1.0, confidence=0.95, source="vlm_answered_env1_not_env2"),
            ],
        },
        {
            "case_id": "synthetic_all_sources_unreadable",
            "provenance": "SYNTHETIC",
            "description": "Both VLM and OCR fail to produce a candidate (e.g. occluded/blank crop) -- must resolve UNREADABLE, never a fabricated numeric fallback.",
            "control_id": "synthetic.matrix.amount",
            "ground_truth_value": None, "ground_truth_unit": None, "ground_truth_readable": False,
            "candidates": [
                ObservationCandidate(outcome=OUTCOME_UNREADABLE, source="vlm", detail="blank crop"),
                ObservationCandidate(outcome=OUTCOME_UNREADABLE, source="ocr", detail="no text detected"),
            ],
        },
        {
            "case_id": "synthetic_low_confidence_single_source_correct_value",
            "provenance": "SYNTHETIC",
            "description": "Single source happens to have the numerically correct value but confidence is below threshold -- must abstain (AMBIGUOUS) even though the value itself is right; correctness is not sufficient without confidence.",
            "control_id": "synthetic.oscA.detune",
            "ground_truth_value": 0.32, "ground_truth_unit": None, "ground_truth_readable": True,
            "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=0.32, confidence=0.55, source="vlm"),
            ],
        },
    ]


def run_synthetic_case(case):
    result = adjudicate(case["candidates"], numeric_tol=1e-3)
    exact_match = result.outcome == OUTCOME_OBSERVED and _values_match(result.value, case["ground_truth_value"])
    confident_wrong = result.outcome == OUTCOME_OBSERVED and not exact_match
    abstained = result.outcome != OUTCOME_OBSERVED
    return {
        "case_id": case["case_id"], "provenance": case["provenance"], "description": case["description"],
        "control_id": case["control_id"], "ground_truth_value": case["ground_truth_value"],
        "ground_truth_readable": case["ground_truth_readable"],
        "input_candidates": [{"value": c.value, "confidence": c.confidence, "source": c.source, "outcome": c.outcome} for c in case["candidates"]],
        "adjudicated_outcome": result.outcome, "adjudicated_value": result.value,
        "adjudicated_confidence": result.confidence, "adjudicated_detail": result.detail,
        "exact_match": exact_match, "confident_wrong": confident_wrong, "abstained": abstained,
    }


def run_real_case(case, engine):
    """Real cases: feed the ACTUAL vlm/ocr outputs already collected through the SAME
    observation_engine.adjudicated_observe used in production. No re-invocation of the model."""
    if case["provenance"] == "REAL_MISSING_EVIDENCE":
        return {
            "case_id": case["case_id"], "provenance": case["provenance"], "control_id": case["control_id"],
            "ground_truth_value": None, "ground_truth_readable": False,
            "raw_vlm_output": None, "raw_ocr_output": OCR_STATUS,
            "adjudicated_outcome": OUTCOME_UNREADABLE, "adjudicated_value": None, "adjudicated_confidence": 0.0,
            "adjudicated_detail": "no crop evidence was ever persisted for this control (see W1 labels.json)",
            "exact_match": False, "confident_wrong": False, "abstained": True,
            "note": case.get("note"),
        }

    sources = [{"raw_value": case["raw_vlm_output"], "source": "vlm_qwen2.5-vl-3b-instruct",
                "confidence": case["vlm_confidence"]}]
    context = {"control_id": case["control_id"], "element_kind": "CONTROL", "control_type": "continuous",
               "unit": case["ground_truth_unit"]}
    result = engine.adjudicated_observe(sources, context, numeric_tol=1e-3)

    predicted = result.value[0] if isinstance(result.value, tuple) else result.value
    exact_match = result.outcome == OUTCOME_OBSERVED and _values_match(predicted, case["ground_truth_value"])
    confident_wrong = result.outcome == OUTCOME_OBSERVED and not exact_match
    abstained = result.outcome != OUTCOME_OBSERVED

    return {
        "case_id": case["case_id"], "provenance": case["provenance"], "control_id": case["control_id"],
        "ground_truth_value": case["ground_truth_value"], "ground_truth_unit": case["ground_truth_unit"],
        "ground_truth_source": case["ground_truth_source"], "ground_truth_readable": True,
        "raw_vlm_output": case["raw_vlm_output"], "vlm_numeric_parsed": case["vlm_numeric"],
        "vlm_confidence": case["vlm_confidence"], "raw_ocr_output": OCR_STATUS,
        "adjudicated_outcome": result.outcome, "adjudicated_value": predicted,
        "adjudicated_confidence": result.confidence, "adjudicated_detail": result.detail,
        "exact_match": exact_match, "confident_wrong": confident_wrong, "abstained": abstained,
    }


def get_gpu_info():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                              capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unavailable"


def main():
    engine = ObservationEngine()
    real_cases = build_real_cases()
    synthetic_cases = build_synthetic_cases()

    rows = [run_real_case(c, engine) for c in real_cases]
    rows += [run_synthetic_case(c) for c in synthetic_cases]

    total = len(rows)
    exact = sum(1 for r in rows if r["exact_match"])
    confident_wrong = sum(1 for r in rows if r["confident_wrong"])
    abstained = sum(1 for r in rows if r["abstained"])

    real_rows = [r for r in rows if r["provenance"].startswith("REAL")]
    real_readable_rows = [r for r in real_rows if r.get("ground_truth_readable")]

    report = {
        "benchmark_version": "c3-1.0.0",
        "commit_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip(),
        "model": "Qwen/Qwen2.5-VL-3B-Instruct (local, 4-bit nf4, transformers)",
        "gpu": get_gpu_info(),
        "ocr_engine": OCR_STATUS,
        "confident_threshold": CONFIDENT_THRESHOLD,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cases": rows,
        "aggregate": {
            "total_cases": total,
            "exact_match": {"numerator": exact, "denominator": total, "rate": round(exact / total, 4)},
            "confident_wrong": {"numerator": confident_wrong, "denominator": total, "rate": round(confident_wrong / total, 4)},
            "abstention": {"numerator": abstained, "denominator": total, "rate": round(abstained / total, 4)},
            "real_evidence_only": {
                "total": len(real_rows),
                "readable_total": len(real_readable_rows),
                "exact_match": sum(1 for r in real_readable_rows if r["exact_match"]),
                "confident_wrong": sum(1 for r in real_rows if r["confident_wrong"]),
                "abstained": sum(1 for r in real_rows if r["abstained"]),
            },
            "synthetic_only": {
                "total": len(rows) - len(real_rows),
                "exact_match": sum(1 for r in rows if r["provenance"] == "SYNTHETIC" and r["exact_match"]),
                "confident_wrong": sum(1 for r in rows if r["provenance"] == "SYNTHETIC" and r["confident_wrong"]),
                "abstained": sum(1 for r in rows if r["provenance"] == "SYNTHETIC" and r["abstained"]),
            },
        },
    }

    # Integration decision -- see write-up in c3_report.md for full reasoning.
    n_real_readable = len(real_readable_rows)
    report["integration_decision"] = {
        "integrated": False,
        "status": "NOT_INTEGRATED_INSUFFICIENT_REAL_EVIDENCE",
        "reason": (
            "Only %d real, readable W1 ground-truth samples exist (n=%d). A confident-wrong rate "
            "of 0/%d real cases is consistent with a true rate anywhere up to roughly 1-(0.05)^(1/%d) "
            "(~78%% at n=%d) under a standard binomial worst-case bound -- far too wide a "
            "confidence interval to certify 'safe to authorize mutations'. Zero real confident-wrong "
            "results is a necessary but nowhere near sufficient condition at this sample size. "
            "Production mutation authority (Gate A/B, the A2 final-contract gate, 2.0.23 epoch "
            "enforcement, admit_rows()) is left completely unchanged; no observation output from "
            "this benchmark is wired into any mutation path." % (
                n_real_readable, n_real_readable, n_real_readable, n_real_readable, n_real_readable)
        ),
        "real_readable_n": n_real_readable,
        "real_confident_wrong_count": sum(1 for r in real_rows if r["confident_wrong"]),
    }

    out_dir = HERE
    (out_dir / "c3_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["aggregate"], indent=2))
    print("integration_decision:", report["integration_decision"]["status"])
    return report


if __name__ == "__main__":
    main()
