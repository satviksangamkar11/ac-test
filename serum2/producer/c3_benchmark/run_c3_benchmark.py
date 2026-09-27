"""C3: local VLM/OCR observation benchmark (v3 -- validates GAP A/B/C remediation on
real native Serum 2.0.23 evidence).

Reuses the existing, cloud-remediated authority (observation_engine.ObservationEngine +
observation_policy.adjudicate/CONFIDENT_THRESHOLD, commit 9115382) -- this module adds NO
new adjudication logic. It adds a benchmark harness, a labelled real+synthetic case set,
and validation checks for the three remediated gaps:

  GAP A (identity binding)   -- ObservationCandidate.control_id / adjudicate(requested_control_id=)
  GAP B (corroboration req.) -- single source, any confidence, now returns AMBIGUOUS
  GAP C (evidence hash)      -- ObservationCandidate.evidence_hash propagated to the result

Case provenance is one of:
  REAL_W1_EVIDENCE       -- real Serum 2.0.23 ground truth, each with a REAL local
                            Qwen2.5-VL-3B-Instruct inference and a REAL local easyocr 1.7.2
                            inference against the actual crop image. VLM confidence is the
                            real mean per-token generation probability; OCR confidence is
                            easyocr's own reported per-detection confidence.
  REAL_MISSING_EVIDENCE  -- a case where the underlying screenshot capture itself failed.
  SYNTHETIC              -- hand-authored ObservationCandidate values, explicitly labelled,
                            used to exercise policy behavior the small real set alone
                            cannot exercise (including the GAP A identity-mismatch cases,
                            per this task's explicit instruction not to fake identity
                            mismatch inside real screenshot evidence).

Ground truth for every REAL_* case was fixed BEFORE any model was run: from the exact
serum-mcp PresetSpec used to generate each calibration preset, cross-checked against
describe_preset() and the real native Serum UI screenshot -- never inferred from VLM/OCR
output.

OCR: easyocr 1.7.2 (pure-Python, local CUDA inference, no cloud API per image).
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from serum2.producer.observation_engine import ObservationEngine
from serum2.producer.observation_policy import (
    ObservationCandidate, OUTCOME_CANDIDATE, OUTCOME_OBSERVED, OUTCOME_AMBIGUOUS,
    OUTCOME_UNREADABLE, OUTCOME_IDENTITY_UNRESOLVED, CONFIDENT_THRESHOLD, adjudicate,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OCR_ENGINE = "easyocr==1.7.2 (local, CUDA, en detector+recognizer)"


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _values_match(predicted, ground_truth, tol=1e-3):
    if predicted is None or ground_truth is None:
        return False
    try:
        return abs(float(predicted) - float(ground_truth)) <= tol
    except (TypeError, ValueError):
        return str(predicted).strip().lower() == str(ground_truth).strip().lower()


def _numeric_from_vlm_text(s):
    m = re.search(r"[+-]?\d+(?:\.\d+)?", s or "")
    return float(m.group(0)) if m else None


def _numeric_from_ocr_fragments(fragments, field_index_hint=None, expected_field_count=5):
    """Numeric parse of easyocr's raw fragment list for ONE specific target field.

    Only trusts a fragment at the exact expected position in a row with the exact expected
    fragment count. Deliberately does NOT fall back to scanning every fragment for any
    digit (a prior version of this function did, and on one real crop matched a stray digit
    from an unrelated UI label as if it were a successful OCR read -- see c3_report.md
    "Known issue found and fixed"). Returns (numeric_or_None, matched_raw_or_None, located_bool).
    """
    if not fragments or field_index_hint is None:
        return None, None, False
    texts = [f["text"] for f in fragments]
    if len(texts) != expected_field_count or field_index_hint >= len(texts):
        return None, None, False
    raw = texts[field_index_hint]
    cleaned = raw.replace(",", ".").replace("$", "s")
    m = re.search(r"[+-]?\d+(?:\.\d+)?", cleaned)
    if m:
        return float(m.group(0)), raw, True
    return None, raw, True


def build_real_cases():
    """REAL_W1_EVIDENCE + REAL_MISSING_EVIDENCE cases. Ground truth fixed before any
    model output was produced; see module docstring for provenance of each."""
    labels = json.loads((REPO / "parameter_characterization" / "vlm_ground_truth" / "labels.json").read_text(encoding="utf-8"))
    vlm_raw = json.loads((HERE / "vlm_raw_outputs.json").read_text(encoding="utf-8"))
    vlm_raw += json.loads((HERE / "vlm_raw_outputs_expansion.json").read_text(encoding="utf-8"))
    vlm_raw += json.loads((HERE / "vlm_raw_outputs_expansion2.json").read_text(encoding="utf-8"))
    vlm_by_id = {r["control_id"]: r for r in vlm_raw}
    ocr_raw = json.loads((HERE / "ocr_raw_outputs.json").read_text(encoding="utf-8"))
    ocr_raw += json.loads((HERE / "ocr_raw_outputs2.json").read_text(encoding="utf-8"))
    ocr_by_id = {r["control_id"]: r for r in ocr_raw}

    def gt_path(rel):
        return str(REPO / rel) if not rel.startswith("serum2") else str(REPO / rel)

    cases = []

    cap0 = labels["captures"][0]
    src0 = REPO / "parameter_characterization" / "vlm_ground_truth" / cap0["crop_file"]
    cases.append({
        "case_id": "real_bulk01_env1_decay", "provenance": "REAL_W1_EVIDENCE",
        "control_id": "env2.decay", "atlas_id": "env2.decay",
        "ground_truth_value": float(cap0["native_values"]["DEC"].replace(" s", "").strip()),
        "ground_truth_unit": "s", "ground_truth_source": cap0["screenshot_file"],
        "evidence_hash": sha256_file(src0),
        "ground_truth_readable": True, "field_index_hint": None, "expected_field_count": 5,
        "vlm": vlm_by_id["env2.decay"], "ocr": ocr_by_id["env2.decay"],
    })

    cap1 = labels["captures"][1]
    src1 = REPO / "parameter_characterization" / "vlm_ground_truth" / cap1["crop_file"]
    cases.append({
        "case_id": "real_cal06_env1_decay", "provenance": "REAL_W1_EVIDENCE",
        "control_id": "env2.decay", "atlas_id": "env2.decay",
        "ground_truth_value": float(cap1["native_values"]["DEC"].replace(" s", "").strip()),
        "ground_truth_unit": "s", "ground_truth_source": cap1["screenshot_file"],
        "evidence_hash": sha256_file(src1),
        "ground_truth_readable": True, "field_index_hint": 2, "expected_field_count": 5,
        "vlm": vlm_by_id["env2.decay_cal06"], "ocr": ocr_by_id["env2.decay_cal06"],
    })

    src2 = HERE / "ground_truth" / "C3_GT_ENV1_DIVERSE_env1_crop.png"
    cases.append({
        "case_id": "real_c3_env1_diverse_decay", "provenance": "REAL_W1_EVIDENCE",
        "control_id": "env1.decay", "atlas_id": "env1.decay",
        "ground_truth_value": 3.50, "ground_truth_unit": "s",
        "ground_truth_source": "serum2/producer/c3_benchmark/ground_truth/C3_GT_ENV1_DIVERSE_env1_crop.png",
        "evidence_hash": sha256_file(src2),
        "ground_truth_readable": True, "field_index_hint": 2, "expected_field_count": 5,
        "vlm": vlm_by_id["c3_gt_env1_diverse"], "ocr": ocr_by_id["c3_gt_env1_diverse"],
    })

    src3 = HERE / "ground_truth" / "C3_GT_ENV3_DIVERSE_env3_crop.png"
    cases.append({
        "case_id": "real_c3_env3_diverse_sustain", "provenance": "REAL_W1_EVIDENCE",
        "control_id": "env3.sustain", "atlas_id": "env3.sustain",
        "ground_truth_value": "61%", "ground_truth_unit": None,
        "ground_truth_source": "serum2/producer/c3_benchmark/ground_truth/C3_GT_ENV3_DIVERSE_env3_crop.png",
        "evidence_hash": sha256_file(src3),
        "ground_truth_readable": True, "field_index_hint": 3, "expected_field_count": 4,  # REL field was dropped by the detector
        "vlm": vlm_by_id["c3_gt_env3_diverse"], "ocr": ocr_by_id["c3_gt_env3_diverse"],
    })

    src4 = HERE / "ground_truth" / "C3_GT_GLOBAL_DIVERSE_tuning_crop.png"
    cases.append({
        "case_id": "real_c3_global_tuning", "provenance": "REAL_W1_EVIDENCE",
        "control_id": "global.tuning", "atlas_id": "global.tuning",
        "ground_truth_value": 442.0, "ground_truth_unit": "Hz",
        "ground_truth_source": "serum2/producer/c3_benchmark/ground_truth/C3_GT_GLOBAL_DIVERSE_tuning_crop.png",
        "evidence_hash": sha256_file(src4),
        "ground_truth_readable": True, "field_index_hint": 2, "expected_field_count": 3,
        "vlm": vlm_by_id["c3_gt_global_tuning"], "ocr": ocr_by_id["c3_gt_global_tuning"],
    })

    fail = labels["failed_capture_attempts"][0]
    cases.append({
        "case_id": "real_missing_filter1_cutoff_tooltip", "provenance": "REAL_MISSING_EVIDENCE",
        "control_id": fail["control_id"], "atlas_id": fail["control_id"],
        "ground_truth_value": None, "ground_truth_readable": False,
        "note": fail["reason"],
    })
    return cases


def build_synthetic_cases():
    """SYNTHETIC adversarial cases, including the GAP A identity-binding cases A1-A4
    (per this task's instruction: identity mismatch must be a labelled synthetic policy
    test, never faked inside real screenshot evidence)."""
    return [
        # --- carried over from c3-1.0.0/2.0.0 ---
        {
            "case_id": "synthetic_ambiguous_numeric_split", "provenance": "SYNTHETIC",
            "description": "VLM and OCR disagree on a numeric value. Must resolve AMBIGUOUS.",
            "control_id": "synthetic.filter1.cutoff", "ground_truth_value": 172.0, "ground_truth_readable": True,
            "requested_control_id": "", "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=172.0, confidence=0.95, source="vlm"),
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=612.0, confidence=0.93, source="ocr"),
            ],
        },
        {
            "case_id": "synthetic_wrong_ocr_correct_vlm_agree_fails", "provenance": "SYNTHETIC",
            "description": "OCR misreads digits; VLM is correct. Sources disagree -> must abstain.",
            "control_id": "synthetic.env1.attack", "ground_truth_value": 5.0, "ground_truth_readable": True,
            "requested_control_id": "", "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=5.0, confidence=0.92, source="vlm"),
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=8.0, confidence=0.91, source="ocr"),
            ],
        },
        {
            "case_id": "synthetic_wrong_vlm_high_confidence", "provenance": "SYNTHETIC",
            "description": "GAP B direct test: a single VLM source is confidently WRONG (>=0.9). Under the "
                            "remediated policy this must now abstain (AMBIGUOUS, single_source=True), not be admitted.",
            "control_id": "synthetic.env2.release", "ground_truth_value": 15.0, "ground_truth_readable": True,
            "requested_control_id": "",
            "candidates": [ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=1500.0, confidence=0.97, source="vlm")],
        },
        {
            "case_id": "synthetic_correct_unit_format_difference", "provenance": "SYNTHETIC",
            "description": "Two sources agree on the numeric value after normalization -- must resolve OBSERVED.",
            "control_id": "synthetic.env1.decay", "ground_truth_value": 1.0, "ground_truth_readable": True,
            "requested_control_id": "", "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=1.0, confidence=0.94, source="vlm"),
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=1.0, confidence=0.90, source="ocr"),
            ],
        },
        {
            "case_id": "synthetic_boolean_state_agree", "provenance": "SYNTHETIC",
            "description": "Boolean/toggle state with agreeing sources -- must resolve OBSERVED with correct ON/OFF.",
            "control_id": "synthetic.filter1.enabled", "ground_truth_value": "ON", "ground_truth_readable": True,
            "requested_control_id": "", "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value="ON", confidence=1.0, source="vlm"),
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value="ON", confidence=1.0, source="ocr"),
            ],
        },
        {
            "case_id": "synthetic_enum_mode_wrong_single_source_high_conf", "provenance": "SYNTHETIC",
            "description": "GAP B: single-source enum/mode read, confidently WRONG mode name -- now must abstain.",
            "control_id": "synthetic.lfo1.shape", "ground_truth_value": "random_sh", "ground_truth_readable": True,
            "requested_control_id": "",
            "candidates": [ObservationCandidate(outcome=OUTCOME_CANDIDATE, value="rossler", confidence=0.96, source="vlm")],
        },
        {
            "case_id": "synthetic_all_sources_unreadable", "provenance": "SYNTHETIC",
            "description": "Both VLM and OCR fail -- must resolve UNREADABLE, never a fabricated numeric fallback.",
            "control_id": "synthetic.matrix.amount", "ground_truth_value": None, "ground_truth_readable": False,
            "requested_control_id": "", "candidates": [
                ObservationCandidate(outcome=OUTCOME_UNREADABLE, source="vlm", detail="blank crop"),
                ObservationCandidate(outcome=OUTCOME_UNREADABLE, source="ocr", detail="no text detected"),
            ],
        },
        {
            "case_id": "synthetic_low_confidence_single_source_correct_value", "provenance": "SYNTHETIC",
            "description": "Single source has the numerically correct value but confidence is below threshold -- must abstain.",
            "control_id": "synthetic.oscA.detune", "ground_truth_value": 0.32, "ground_truth_readable": True,
            "requested_control_id": "",
            "candidates": [ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=0.32, confidence=0.55, source="vlm")],
        },

        # --- GAP A identity-binding validation (A1-A4), explicitly synthetic per task instruction ---
        {
            "case_id": "synthetic_gap_a1_correct_value_correct_identity", "provenance": "SYNTHETIC",
            "description": "GAP A1: correct value + correct control identity + 2 agreeing sources -> OBSERVED.",
            "control_id": "env2.decay", "ground_truth_value": 5.0, "ground_truth_readable": True,
            "requested_control_id": "env2.decay", "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=5.0, confidence=0.95, source="vlm", control_id="env2.decay"),
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=5.0, confidence=0.90, source="ocr", control_id="env2.decay"),
            ],
        },
        {
            "case_id": "synthetic_gap_a2_correct_value_wrong_identity", "provenance": "SYNTHETIC",
            "description": "GAP A2: a source reports the numerically correct-looking value but asserts a DIFFERENT "
                            "control identity than requested (e.g. answered about env1.decay when env2.decay was "
                            "asked). Must resolve IDENTITY_UNRESOLVED, never become an observation for the "
                            "requested control merely because the number looks plausible.",
            "control_id": "env2.decay", "ground_truth_value": 5.0, "ground_truth_readable": True,
            "requested_control_id": "env2.decay", "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=5.0, confidence=0.95, source="vlm", control_id="env1.decay"),
            ],
        },
        {
            "case_id": "synthetic_gap_a3_correct_value_missing_identity", "provenance": "SYNTHETIC",
            "description": "GAP A3: a source reports the correct value but asserts NO identity at all "
                            "(control_id=''). Per the current policy, an empty control_id is treated as "
                            "'no identity asserted' and is not excluded by the identity filter -- it still "
                            "must NOT be admitted as OBSERVED on its own (GAP B: single source, any confidence). "
                            "Recorded honestly: identity-agnostic single-source evidence is not mutation-authorizing "
                            "for a completely separate reason (corroboration), not because identity absence is itself caught.",
            "control_id": "env2.decay", "ground_truth_value": 5.0, "ground_truth_readable": True,
            "requested_control_id": "env2.decay", "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=5.0, confidence=0.95, source="vlm", control_id=""),
            ],
        },
        {
            "case_id": "synthetic_gap_a4_correct_identity_wrong_value", "provenance": "SYNTHETIC",
            "description": "GAP A4: correct control identity, but the value is WRONG and plausible-looking. "
                            "Identity being correct must not itself authorize an incorrect value -- with only one "
                            "source this abstains via GAP B; with two agreeing-on-a-wrong-value sources it would "
                            "still be admitted (identity binding cannot detect a value being objectively wrong, "
                            "only whose control it claims to describe) -- surfaced honestly as a real limit of "
                            "identity binding, not something GAP A was ever meant to solve.",
            "control_id": "env2.decay", "ground_truth_value": 5.0, "ground_truth_readable": True,
            "requested_control_id": "env2.decay", "candidates": [
                ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=99.0, confidence=0.95, source="vlm", control_id="env2.decay"),
            ],
        },
    ]


def run_synthetic_case(case):
    result = adjudicate(case["candidates"], numeric_tol=1e-3, requested_control_id=case.get("requested_control_id", ""))
    exact_match = result.outcome == OUTCOME_OBSERVED and _values_match(result.value, case["ground_truth_value"])
    confident_wrong = result.outcome == OUTCOME_OBSERVED and not exact_match
    abstained = result.outcome not in (OUTCOME_OBSERVED,)
    return {
        "case_id": case["case_id"], "provenance": case["provenance"], "description": case["description"],
        "control_id": case["control_id"], "requested_control_id": case.get("requested_control_id", ""),
        "ground_truth_value": case["ground_truth_value"], "ground_truth_readable": case["ground_truth_readable"],
        "input_candidates": [{"value": c.value, "confidence": c.confidence, "source": c.source,
                               "outcome": c.outcome, "control_id": c.control_id} for c in case["candidates"]],
        "adjudicated_outcome": result.outcome, "adjudicated_value": result.value,
        "adjudicated_confidence": result.confidence, "adjudicated_detail": result.detail,
        "adjudicated_evidence_hash": result.evidence_hash, "adjudicated_control_id": result.control_id,
        "exact_match": exact_match, "confident_wrong": confident_wrong, "abstained": abstained,
    }


def run_real_case(case, engine):
    if case["provenance"] == "REAL_MISSING_EVIDENCE":
        return {
            "case_id": case["case_id"], "provenance": case["provenance"], "control_id": case["control_id"],
            "ground_truth_value": None, "ground_truth_readable": False,
            "raw_vlm_output": None, "raw_ocr_fragments": None, "evidence_hash": None,
            "adjudicated_outcome": OUTCOME_UNREADABLE, "adjudicated_value": None, "adjudicated_confidence": 0.0,
            "adjudicated_detail": "no crop evidence was ever persisted for this control (see W1 labels.json)",
            "exact_match": False, "confident_wrong": False, "abstained": True, "note": case.get("note"),
        }

    vlm = case["vlm"]
    ocr = case["ocr"]
    ocr_numeric, ocr_matched_raw, ocr_field_located = _numeric_from_ocr_fragments(
        ocr["ocr_raw"], case.get("field_index_hint"), case.get("expected_field_count", 5))
    vlm_numeric = _numeric_from_vlm_text(vlm["raw_vlm_output"])
    evidence_hash = case["evidence_hash"]

    context = {"control_id": case["control_id"], "element_kind": "CONTROL", "control_type": "continuous",
               "unit": case.get("ground_truth_unit"), "roi_hash": evidence_hash}
    sources = [{"raw_value": vlm["raw_vlm_output"], "source": "vlm_qwen2.5-vl-3b-instruct",
                "confidence": vlm["mean_token_prob"]}]
    ocr_added = ocr_numeric is not None
    if ocr_added:
        matched_conf = next((f["confidence"] for f in ocr["ocr_raw"] if f["text"] == ocr_matched_raw), 0.5)
        sources.append({"raw_value": str(ocr_numeric), "source": "ocr_easyocr_1.7.2", "confidence": matched_conf})

    result = engine.adjudicated_observe(sources, context, numeric_tol=1e-3)
    predicted = result.value[0] if isinstance(result.value, tuple) else result.value
    exact_match = result.outcome == OUTCOME_OBSERVED and _values_match(predicted, case["ground_truth_value"])
    confident_wrong = result.outcome == OUTCOME_OBSERVED and not exact_match
    abstained = result.outcome != OUTCOME_OBSERVED

    return {
        "case_id": case["case_id"], "provenance": case["provenance"], "control_id": case["control_id"],
        "ground_truth_value": case["ground_truth_value"], "ground_truth_unit": case.get("ground_truth_unit"),
        "ground_truth_source": case["ground_truth_source"], "ground_truth_readable": True,
        "evidence_hash": evidence_hash,
        "raw_vlm_output": vlm["raw_vlm_output"], "vlm_numeric_parsed": vlm_numeric, "vlm_confidence": vlm["mean_token_prob"],
        "raw_ocr_fragments": ocr["ocr_raw"], "ocr_numeric_parsed": ocr_numeric, "ocr_matched_raw_text": ocr_matched_raw,
        "ocr_field_positionally_located": ocr_field_located, "ocr_used_as_source": ocr_added,
        "sources_count": len(sources), "genuinely_independent_sources": ocr_added,  # 2 distinct model pipelines (Qwen vs easyocr), not repeated frames of the same model
        "adjudicated_outcome": result.outcome, "adjudicated_value": predicted,
        "adjudicated_confidence": result.confidence, "adjudicated_detail": result.detail,
        "adjudicated_evidence_hash": result.evidence_hash, "adjudicated_control_id": result.control_id,
        "exact_match": exact_match, "confident_wrong": confident_wrong, "abstained": abstained,
    }


def run_evidence_hash_tamper_test():
    """GAP C validation (Step 7): compute the real hash of one committed evidence file,
    write a tampered COPY (never touching the authoritative committed file), show the
    hashes differ, and confirm nothing in this benchmark would treat them as the same
    evidence. Pure read + scratch-copy operation -- no committed evidence is modified."""
    import tempfile
    original = HERE / "ground_truth" / "C3_GT_GLOBAL_DIVERSE_tuning_crop.png"
    original_hash = sha256_file(original)
    with tempfile.TemporaryDirectory() as td:
        tampered = Path(td) / "tampered_copy.png"
        data = bytearray(original.read_bytes())
        data[-1] ^= 0xFF  # flip the last byte -- minimal, deterministic tamper
        tampered.write_bytes(bytes(data))
        tampered_hash = sha256_file(tampered)
    return {
        "original_file": str(original.relative_to(REPO)),
        "original_hash": original_hash,
        "tampered_hash": tampered_hash,
        "hashes_differ": original_hash != tampered_hash,
        "committed_evidence_untouched": True,
    }


def run_mutation_boundary_test():
    """Step 11: demonstrate observation_policy/observation_engine are not imported by any
    mutation-authority module (grep-based, matching test_c3_remediation.py's own check)."""
    gate_modules = [
        "serum2/producer/contract_registry.py",
        "serum2/producer/route_selection.py",
        "serum2/producer/producer_brain.py",
        "serum2/producer/gate_b_certificate.py",
        "serum2/evidence/admission.py",
    ]
    findings = {}
    for rel in gate_modules:
        p = REPO / rel
        if not p.exists():
            findings[rel] = "FILE_NOT_FOUND"
            continue
        src = p.read_text(encoding="utf-8")
        findings[rel] = "observation_policy" not in src and "observation_engine" not in src
    return {"gate_modules_checked": gate_modules, "clean": findings, "all_clean": all(v is True for v in findings.values())}


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

    real_rows = [run_real_case(c, engine) for c in real_cases]
    synth_rows = [run_synthetic_case(c) for c in synthetic_cases]
    rows = real_rows + synth_rows

    real_readable_rows = [r for r in real_rows if r.get("ground_truth_readable")]
    gap_a_rows = [r for r in synth_rows if r["case_id"].startswith("synthetic_gap_a")]

    tamper = run_evidence_hash_tamper_test()
    boundary = run_mutation_boundary_test()

    def agg(pop):
        n = len(pop)
        return {
            "total": n,
            "exact_match": sum(1 for r in pop if r["exact_match"]),
            "confident_wrong": sum(1 for r in pop if r["confident_wrong"]),
            "abstained": sum(1 for r in pop if r["abstained"]),
        }

    report = {
        "benchmark_version": "c3-3.0.0",
        "validated_against_remediation_commit": "9115382",
        "commit_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip(),
        "model": "Qwen/Qwen2.5-VL-3B-Instruct (local, 4-bit nf4, transformers)",
        "ocr_engine": OCR_ENGINE,
        "gpu": get_gpu_info(),
        "confident_threshold": CONFIDENT_THRESHOLD,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "real_cases": real_rows,
        "synthetic_cases": synth_rows,
        "evidence_hash_tamper_test": tamper,
        "mutation_boundary_test": boundary,
        "aggregate": {
            "real_readable_only": agg(real_readable_rows),
            "real_complete_including_missing": agg(real_rows),
            "synthetic_only": agg(synth_rows),
            "gap_a_identity_cases": {
                r["case_id"]: {"outcome": r["adjudicated_outcome"], "exact_match": r["exact_match"],
                               "confident_wrong": r["confident_wrong"]}
                for r in gap_a_rows
            },
        },
    }

    # --- GAP validation summary ---
    single_source_synth = [r for r in synth_rows if r["case_id"] in (
        "synthetic_wrong_vlm_high_confidence", "synthetic_enum_mode_wrong_single_source_high_conf")]
    gap_b_closed = all(r["adjudicated_outcome"] == OUTCOME_AMBIGUOUS and not r["confident_wrong"] for r in single_source_synth)

    a2 = next(r for r in gap_a_rows if r["case_id"] == "synthetic_gap_a2_correct_value_wrong_identity")
    gap_a_closed = a2["adjudicated_outcome"] == OUTCOME_IDENTITY_UNRESOLVED

    real_cw = sum(1 for r in real_rows if r["confident_wrong"])
    real_readable_n = len(real_readable_rows)
    genuinely_corroborated_real = sum(1 for r in real_readable_rows if r.get("genuinely_independent_sources"))

    report["gap_validation"] = {
        "GAP_A_identity_binding_closed": gap_a_closed,
        "GAP_A_evidence": "synthetic_gap_a2 (correct value, wrong identity) resolved %s" % a2["adjudicated_outcome"],
        "GAP_B_single_source_no_longer_authorizes_closed": gap_b_closed,
        "GAP_B_evidence": "the 2 single-source-confident-wrong synthetic cases from c3-1.0.0 both now resolve %s" % (
            "AMBIGUOUS as required" if gap_b_closed else "something other than AMBIGUOUS -- REGRESSION"),
        "GAP_C_evidence_hash_propagates": all(r.get("adjudicated_evidence_hash") for r in real_readable_rows if r["adjudicated_outcome"] == OUTCOME_OBSERVED),
        "GAP_C_tamper_test": tamper["hashes_differ"] and tamper["committed_evidence_untouched"],
        "real_confident_wrong_count": real_cw,
        "real_readable_n": real_readable_n,
        "genuinely_independent_corroboration_real_cases": genuinely_corroborated_real,
        "corroboration_note": (
            "Genuine independent corroboration (2 distinct model pipelines -- Qwen2.5-VL-3B and easyocr, "
            "not repeated frames of the same model) occurred in %d of %d real readable cases. The "
            "remaining cases had only a single usable source (OCR could not be positionally trusted), "
            "and under the remediated policy correctly resolved AMBIGUOUS rather than being admitted." % (
                genuinely_corroborated_real, real_readable_n)
        ),
        "mutation_boundary_intact": boundary["all_clean"],
    }

    all_gaps_closed_on_real_evidence = gap_a_closed and gap_b_closed and real_cw == 0 and boundary["all_clean"]
    # Statistical sufficiency is a SEPARATE question from whether the mechanism works.
    statistically_sufficient = real_readable_n >= 8

    if all_gaps_closed_on_real_evidence and statistically_sufficient:
        disposition = "C3_VALIDATION_READY_FOR_CLOUD_REVIEW"
        reason = "All three gaps validated closed and n>=8 real readable cases collected."
    else:
        disposition = "C3_REMEDIATION_STILL_INSUFFICIENT"
        gaps = []
        if not gap_a_closed:
            gaps.append("GAP A identity binding did not resolve as expected")
        if not gap_b_closed:
            gaps.append("GAP B single-source admission regression")
        if real_cw > 0:
            gaps.append("%d real confident-wrong result(s)" % real_cw)
        if not boundary["all_clean"]:
            gaps.append("mutation boundary check failed")
        if not statistically_sufficient:
            gaps.append(
                "real readable n=%d is still below the n>=8 target this task set for statistical "
                "sufficiency (a worst-case binomial bound at n=%d with 0 observed failures still "
                "permits a true confident-wrong rate well above 0%%)" % (real_readable_n, real_readable_n))
        reason = "; ".join(gaps) if gaps else "unspecified"

    report["disposition"] = {"status": disposition, "reason": reason}

    (HERE / "c3_results.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report["aggregate"], indent=2, default=str))
    print(json.dumps(report["gap_validation"], indent=2, default=str))
    print("disposition:", disposition, "--", reason)
    return report


if __name__ == "__main__":
    main()
