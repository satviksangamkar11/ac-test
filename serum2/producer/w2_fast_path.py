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

# Transcript-cued windows for this specific tutorial (AjE11L_OwLA).
# Each entry: (control_id, description, frames_t_min, frames_t_max, prefer_positive).
# These are read from transcript analysis; do not invent values.
# "prefer_positive" flags that minus-sign OCR is unreliable at this resolution
# and the session should prioritise frames where the value is likely positive.
_TUTORIAL_CANDIDATE_WINDOWS: List[Tuple[str, str, float, float, bool]] = [
    # oscA.octave was shown as 0 at t≈24s (VLM single-source, needs OCR corroboration).
    # Zero value → no minus sign → OCR-friendly. Try t=22-28s.
    ("oscA.octave", "osc A octave shown at ~24s, value appears 0 (positive/zero)", 22.0, 28.0, True),
    # oscA.octave also visible at t≈34s as -2, but minus-sign OCR is unreliable here.
    # Secondary option only if zero-value frames don't corroborate.
    ("oscA.octave", "osc A octave at ~34s shows -2, but minus sign OCR unreliable", 32.0, 36.0, False),
    # env1.decay at t≈24s: VLM=1.0s but OCR fragmented to 1005. Try tighter ROI.
    ("env1.decay", "env1 decay row visible at ~24s; OCR fragmented '1.0 s' as '1005'", 22.0, 28.0, True),
    # LFO1 rate: core of a wobble bass — look in the 40-100s range where LFO is configured.
    ("lfo1.rate", "LFO1 rate likely configured during wobble section ~40-100s", 38.0, 100.0, True),
    # filter1.cutoff: sweep target for the wobble — visible when filter is adjusted.
    ("filter1.cutoff", "filter cutoff likely visible ~40-120s during wobble setup", 38.0, 120.0, True),
    # env2.decay: if a second envelope is shown (modulation depth), likely ~60-150s.
    ("env2.decay", "env2 decay possibly visible if second envelope used ~60-150s", 60.0, 150.0, True),
]


def temporal_candidates(
    manifest: dict,
    control_id: str,
    contract_covered: Optional[Set[str]] = None,
) -> List[dict]:
    """Return a list of manifest frame dicts suitable for temporal corroboration.

    Selects up to 3 distinct timestamps from transcript-cued windows for ``control_id``.
    Returns [] if ``control_id`` is not contract-covered or has no cued window.
    Never returns duplicate frame_ids.
    """
    if contract_covered is None:
        contract_covered = contract_covered_controls()
    if control_id not in contract_covered:
        return []

    windows = [w for w in _TUTORIAL_CANDIDATE_WINDOWS if w[0] == control_id]
    if not windows:
        return []

    seen_ids: Set[str] = set()
    result: List[dict] = []
    for _, _desc, t_min, t_max, _prefer_pos in windows:
        frames_in_window = select_frames_by_timestamp(manifest, t_min, t_max)
        # Prefer every-other frame to maximise temporal separation within the window.
        for i, fr in enumerate(frames_in_window):
            if len(result) >= 3:
                break
            fid = fr["frame_id"]
            if fid in seen_ids:
                continue
            seen_ids.add(fid)
            result.append(fr)
        if len(result) >= 3:
            break

    return result[:3]


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
