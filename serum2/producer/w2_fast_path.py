"""W2 fast path helper — existing-frame reuse, contract-first filtering, temporal candidates.

Reads from committed artifacts (manifest, contract) only.
Never calls yt-dlp, ffmpeg download, or network fetch.
Does NOT import observation_policy, state_admission, authorized_state_compiler,
or gate_b_certificate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
W2_MANIFEST_PATH = REPO_ROOT / "tests/fixtures/w2/w2_acquisition_manifest.json"
W2_METADATA_PATH = REPO_ROOT / "tests/fixtures/w2/w2_run_metadata.json"
CONTRACT_PATH = REPO_ROOT / "parameter_characterization/bulk_causal_evidence/final_execution_contract_v1.json"

# OCR character allowlist for generic numeric readouts (no per-control hardcode).
# Covers: digits, decimal point, minus sign.  Callers must NOT branch on control_id.
NUMERIC_OCR_ALLOWLIST = "0123456789-."

# Recommended EasyOCR kwargs for small numeric glyphs in Serum UI.
# These are generic; do not add control-specific branches here.
NUMERIC_OCR_KWARGS = {
    "allowlist": NUMERIC_OCR_ALLOWLIST,
    "detail": 1,
    "mag_ratio": 2.0,         # upscale for small glyphs
    "beamWidth": 10,
    "text_threshold": 0.5,
    "low_text": 0.4,
    "link_threshold": 0.4,
}


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_existing_manifest(manifest_path: Path = W2_MANIFEST_PATH) -> dict:
    """Load the committed W2 acquisition manifest.

    Raises FileNotFoundError if not present (means caller is on a machine without it).
    Never initiates a download.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"W2 manifest not found at {manifest_path}. "
            "Run W2 acquisition on the LOCAL session first (Phase 2 of W2_RUNBOOK.md)."
        )
    with open(manifest_path) as f:
        return json.load(f)


def manifest_frame_ids(manifest: dict) -> List[str]:
    """Return all frame IDs from the manifest, in acquisition order."""
    return [fr["frame_id"] for fr in manifest.get("frames", [])]


def select_frames_by_timestamp(
    manifest: dict,
    t_min_sec: float,
    t_max_sec: float,
) -> List[dict]:
    """Return all manifest frames whose timestamp falls in [t_min_sec, t_max_sec]."""
    return [
        fr for fr in manifest.get("frames", [])
        if t_min_sec <= fr.get("timestamp_sec", -1.0) <= t_max_sec
    ]


def frame_artifact_path(frame: dict) -> Path:
    """Resolve the artifact path for a frame entry (relative to repo root)."""
    return REPO_ROOT / frame["artifact_path"]


# ---------------------------------------------------------------------------
# Contract helpers (read-only)
# ---------------------------------------------------------------------------

def load_contract(contract_path: Path = CONTRACT_PATH) -> dict:
    """Load final_execution_contract_v1.json read-only. Never modifies the file."""
    with open(contract_path) as f:
        return json.load(f)


def contract_covered_controls(
    contract: Optional[dict] = None,
    *,
    require_class: str = "MCP_EXEC_HOST_CONFIRMED",
    require_no_exception: bool = True,
) -> Set[str]:
    """Return the set of control_ids present in the execution contract.

    Filters to ``require_class`` and (by default) requires ``exception_policy == 'NONE'``.
    Does not modify the contract.
    """
    if contract is None:
        contract = load_contract()
    lookup: Dict[str, dict] = contract.get("producer_lookup", {})
    result: Set[str] = set()
    for cid, entry in lookup.items():
        if entry.get("class") != require_class:
            continue
        if require_no_exception and entry.get("exception_policy", "NONE") != "NONE":
            continue
        result.add(cid)
    return result


def filter_contract_covered(
    candidates: List[str],
    contract_covered: Optional[Set[str]] = None,
) -> Tuple[List[str], List[str]]:
    """Split ``candidates`` into (covered, excluded).

    ``excluded`` contains candidates NOT in the execution contract — e.g. oscA.rand_phase.
    Never modifies the contract.
    """
    if contract_covered is None:
        contract_covered = contract_covered_controls()
    covered = [c for c in candidates if c in contract_covered]
    excluded = [c for c in candidates if c not in contract_covered]
    return covered, excluded


# ---------------------------------------------------------------------------
# Temporal candidate selection
# ---------------------------------------------------------------------------

def all_manifest_frames_for_control(
    manifest: dict,
    control_id: str,
    contract_covered: Optional[Set[str]] = None,
) -> List[dict]:
    """Return ALL manifest frames for a given control (if contract-covered).

    DEPRECATED: temporal_candidates() was tutorial-specific and hardcoded
    for a single video's transcript landmarks.
    The universal frame observer uses all_manifest_frames_for_control() to
    ensure every frame is evaluated in evidence-first observation.

    Returns [] if ``control_id`` is not contract-covered.
    """
    if contract_covered is None:
        contract_covered = contract_covered_controls()
    if control_id not in contract_covered:
        return []

    # Return all frames, sorted by timestamp
    frames = manifest.get("frames", [])
    return sorted(frames, key=lambda f: float(f.get("timestamp_sec", 0.0)))


# ---------------------------------------------------------------------------
# Numeric OCR profile (generic — no per-control branches)
# ---------------------------------------------------------------------------

def numeric_ocr_profile(
    *,
    signed: bool = True,
    decimal: bool = True,
) -> dict:
    """Return EasyOCR kwargs for a generic numeric ROI.

    ``signed`` includes '-' in the allowlist (True by default).
    ``decimal`` includes '.' (True by default).
    No per-control special cases.  Caller must NOT add control_id branches.
    """
    chars = "0123456789"
    if decimal:
        chars += "."
    if signed:
        chars += "-"
    profile = dict(NUMERIC_OCR_KWARGS)
    profile["allowlist"] = chars
    return profile


# ---------------------------------------------------------------------------
# Sanity helpers
# ---------------------------------------------------------------------------

def assert_no_redownload(manifest: dict) -> None:
    """Raise AssertionError if the manifest shows storyboard_only=True.

    Callers must check this before any OCR/VLM run to ensure real frames.
    """
    if manifest.get("storyboard_only"):
        raise AssertionError(
            "Manifest has storyboard_only=True. "
            "Frames are low-res storyboard sprites, not real frames. "
            "Re-run acquisition on the LOCAL machine with Phase 2 of W2_RUNBOOK.md."
        )


def rand_phase_exclusion_reason() -> str:
    """Return the documented reason oscA.rand_phase is excluded from execution."""
    return (
        "oscA.rand_phase reached OBSERVED (62, VLM+OCR agreement) in W2 Stage-A "
        "but has no row in final_execution_contract_v1.json (producer_lookup). "
        "Per W2 stop condition: controls without a contract row are not admissible "
        "and must NOT be added to the contract to make the tutorial pass."
    )
