"""Universal full-frame observation pipeline.

Architecture (10 stages):
  1. INGEST      — load all manifest frames, verify existence, record hash
  2. PIXEL       — cheap local PIL/numpy: temporal diff, text density, dedup
  3. TEMPORAL    — group near-identical runs; select representative frames
  4. OCR         — local EasyOCR on candidate regions (zero remote calls)
  5. VLM         — local Qwen census (evidence-first, no parameter hints)
  6. IDENTITY    — atlas normalization of VLM-reported control labels
  7. ADJUDICATE  — existing adjudicated_observe() / GAP-A/B/C unchanged
  8. CONTRACT    — post-observation filter via contract_covered_controls()
  9. LEDGER      — only OBSERVED + contract-covered enter
 10. STOP        — auditable accounting preserved; full census always returned

Optimization reduces redundant computation.
It does not reduce evidence coverage.

The observer does not know which tutorial parameter is expected.
Parameter identity is derived from evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

# Pixel-analysis thresholds (generic, no control names)
_PIXEL_CHANGE_THRESHOLD = 0.015    # mean abs diff to mark a frame as active (from densify_windows.py)
_NEAR_DUPLICATE_THRESHOLD = 0.003  # diff below this → near-duplicate run
_SERUM_PANEL_CROP = (700, 0, 1920, 1080)  # right-side crop for diff in a 1920×1080 frame

# VLM/OCR source labels (for evidence accounting)
_SRC_VLM = "qwen2.5-vl-3b-instruct"
_SRC_OCR = "easyocr-1.7.2"

# Algorithm version — bump to invalidate stale cached observation runs
OBSERVER_VERSION = "universal-v1"


@dataclass
class FrameRecord:
    """One manifest frame, fully accounted for from Stage 1 onwards."""
    frame_id: str
    timestamp_sec: float
    artifact_hash: str
    image_path: str
    exists: bool
    change_score: float = 0.0
    text_density_score: float = 0.0
    is_duplicate: bool = False
    is_active: bool = False
    pixel_status: str = "PENDING"  # PENDING|OK|DUPLICATE|NO_IMAGE|FAILED
    group_index: int = -1


@dataclass
class TemporalGroup:
    """A run of consecutive near-identical frames sharing one stable UI state."""
    group_index: int
    frame_ids: List[str]
    representative_frame_id: str
    representative_path: str
    start_ts: float
    end_ts: float
    mean_change_score: float


@dataclass
class RawFinding:
    """One VLM or OCR finding before identity resolution."""
    frame_id: str
    group_index: int
    claimed_panel: str   # e.g. "ENV1", "OSC A"
    claimed_label: str   # e.g. "DEC", "OCT"
    raw_value: str
    source_type: str     # "vlm" or "ocr"
    vlm_confidence: float = 0.0
    ocr_confidence: float = 0.0
    evidence_hash: str = ""


@dataclass
class ResolvedFinding:
    """RawFinding with atlas-resolved control identity."""
    raw: RawFinding
    resolved_control_id: Optional[str]
    resolution_status: str  # EXACT|ALIAS|AMBIGUOUS|UNRESOLVED


@dataclass
class ObservationCensus:
    """Complete result of one universal observation run."""
    frame_records: List[FrameRecord] = field(default_factory=list)
    temporal_groups: List[TemporalGroup] = field(default_factory=list)
    raw_findings: List[RawFinding] = field(default_factory=list)
    resolved_findings: List[ResolvedFinding] = field(default_factory=list)

    # Per-control adjudication: control_id → PolicyCandidate
    adjudicated: Dict[str, Any] = field(default_factory=dict)
    admissible: List[str] = field(default_factory=list)
    excluded: List[str] = field(default_factory=list)

    # Required census metrics
    total_frames: int = 0
    frames_pixel_processed: int = 0
    frames_failed: int = 0
    n_temporal_groups: int = 0
    candidate_regions: int = 0
    ocr_attempts: int = 0
    vlm_attempts: int = 0
    identity_attempts: int = 0
    observed: int = 0
    ambiguous: int = 0
    unreadable: int = 0
    identity_unresolved: int = 0
    admissible_observed: int = 0
    duplicate_evidence_rejected: int = 0

    # Token accounting — these must be 0 for the initial observation sweep
    remote_llm_calls: int = 0
    remote_ocr_calls: int = 0
    local_vlm_calls: int = 0

    observer_version: str = OBSERVER_VERSION

    def to_metrics_json(self) -> dict:
        """Emit the c3_observation_metrics.json schema consumed by runner.py."""
        from serum2.producer.observation_policy import OUTCOME_OBSERVED
        metrics = []
        for cid, adj in self.adjudicated.items():
            outcome = getattr(adj, "outcome", "UNREADABLE")
            value = getattr(adj, "value", None)
            scalar_value = _flatten_value(value)
            unit = _value_unit(value)
            evidence_hash = getattr(adj, "evidence_hash", "") or ""
            single_source = getattr(adj, "single_source", True)
            metrics.append({
                "control_id": cid,
                "frame_id": "",
                "timestamp_sec": 0.0,
                "evidence_hash": evidence_hash,
                "adjudicated_outcome": outcome,
                "adjudicated_value": scalar_value,
                # NUMERIC strategy's normalized_value is (num, unit); _flatten_value() above
                # keeps only num for a plain scalar reading. The unit is preserved here
                # (never silently dropped) so a downstream Row can be built with its real
                # unit -- state_ledger.derive()'s unit conversion needs it to be correct.
                "adjudicated_unit": unit,
                "adjudicated_confidence": getattr(adj, "confidence", 0.0),
                "adjudicated_detail": getattr(adj, "detail", ""),
                "adjudicated_evidence_hash": evidence_hash,
                "single_source": single_source,
                "confident_wrong": False,
                "exact_match": False,
                "ocr_used_as_source": False,
                "has_execution_contract_row": cid in self.admissible or cid in self.excluded,
            })
        return {
            "observer_version": self.observer_version,
            "metrics": metrics,
            "aggregate": {
                "total_frames": self.total_frames,
                "frames_pixel_processed": self.frames_pixel_processed,
                "frames_failed": self.frames_failed,
                "temporal_groups": self.n_temporal_groups,
                "candidate_regions": self.candidate_regions,
                "ocr_attempts": self.ocr_attempts,
                "vlm_attempts": self.vlm_attempts,
                "identity_attempts": self.identity_attempts,
                "observed": self.observed,
                "ambiguous": self.ambiguous,
                "unreadable": self.unreadable,
                "identity_unresolved": self.identity_unresolved,
                "admissible_observed": self.admissible_observed,
                "duplicate_evidence_rejected": self.duplicate_evidence_rejected,
                "remote_llm_calls": self.remote_llm_calls,
                "remote_ocr_calls": self.remote_ocr_calls,
                "local_vlm_calls": self.local_vlm_calls,
                # Legacy field names for runner.py compatibility
                "total_controls_attempted": len(self.adjudicated),
                "observed_corroborated_count": self.observed,
                "confident_wrong_count": 0,
            },
        }


def _flatten_value(value: Any) -> Any:
    """Flatten (num, unit) tuples produced by NUMERIC strategy to numeric scalar."""
    if isinstance(value, tuple) and len(value) == 2:
        return value[0]
    return value


def _value_unit(value: Any) -> Optional[str]:
    """The unit half of a NUMERIC strategy's (num, unit) normalized_value, or None for
    every other strategy (whose adjudicated_value is already a plain scalar/string)."""
    if isinstance(value, tuple) and len(value) == 2:
        return value[1]
    return None


class FrameObservationCensus:
    """Orchestrates the 10-stage universal full-frame observation pipeline."""

    def __init__(self, engine: Any = None) -> None:
        self._ocr_reader = None  # lazy singleton
        # `engine` is the test-injection point (a fake with a canned observe_control_in_frame/
        # observe_frame_all_controls, avoiding the real ~7GB local Qwen model in CI); None
        # means run() lazy-loads the real ObservationEngine.
        self._engine = engine

    # ------------------------------------------------------------------
    # Stage 1: INGEST — all frames, no exceptions
    # ------------------------------------------------------------------

    def _ingest_frames(self, manifest: dict) -> List[FrameRecord]:
        records: List[FrameRecord] = []
        for fr in manifest.get("frames", []):
            rel_path = fr.get("artifact_path", "")
            abs_path = str(REPO_ROOT / rel_path) if rel_path else ""
            records.append(FrameRecord(
                frame_id=fr.get("frame_id", f"frame_{len(records):08d}"),
                timestamp_sec=float(fr.get("timestamp_sec", 0.0)),
                artifact_hash=fr.get("artifact_hash", fr.get("sha256", "")),
                image_path=abs_path,
                exists=bool(abs_path and Path(abs_path).exists()),
            ))
        return records

    # ------------------------------------------------------------------
    # Stage 2: PIXEL ANALYSIS — local, zero tokens
    # ------------------------------------------------------------------

    def _pixel_analysis(self, records: List[FrameRecord]) -> None:
        """Temporal diff + text-density estimation.

        No VLM. No OCR. No remote calls. No control names.
        PIL + numpy only. Updates FrameRecord fields in-place.
        """
        try:
            import numpy as np
            from PIL import Image
            _have_pil = True
        except ImportError:
            _have_pil = False

        seen_hashes: set = set()
        prev_arr: Optional[Any] = None
        cx0, cy0, cx1, cy1 = _SERUM_PANEL_CROP

        for rec in records:
            # Duplicate detection by artifact hash (zero computation)
            if rec.artifact_hash and rec.artifact_hash in seen_hashes:
                rec.is_duplicate = True
                rec.pixel_status = "DUPLICATE"
                continue
            if rec.artifact_hash:
                seen_hashes.add(rec.artifact_hash)

            if not rec.exists:
                rec.pixel_status = "NO_IMAGE"
                prev_arr = None  # break diff chain across a gap
                continue

            if not _have_pil:
                # PIL absent: accept as active (worst case: too many VLM calls)
                rec.pixel_status = "OK"
                rec.is_active = True
                continue

            try:
                import numpy as np
                from PIL import Image
                im = Image.open(rec.image_path)
                w, h = im.size

                panel = im.crop((
                    min(cx0, w), min(cy0, h),
                    min(cx1, w), min(cy1, h),
                ))
                arr = np.array(panel.convert("RGB"), dtype=np.float32) / 255.0

                # Temporal diff
                if prev_arr is not None and prev_arr.shape == arr.shape:
                    diff = float(np.mean(np.abs(arr - prev_arr)))
                    rec.change_score = diff
                    rec.is_active = diff > _PIXEL_CHANGE_THRESHOLD
                else:
                    rec.change_score = 0.0
                    rec.is_active = True  # first frame or gap: conservative
                prev_arr = arr

                # Approximate text density via Sobel-like edge magnitude
                gray = np.mean(arr, axis=2)
                dx = np.abs(gray[:, 1:] - gray[:, :-1])
                dy = np.abs(gray[1:, :] - gray[:-1, :])
                rec.text_density_score = float((np.mean(dx) + np.mean(dy)) / 2.0)
                rec.pixel_status = "OK"

            except Exception:
                rec.pixel_status = "FAILED"
                prev_arr = None

    # ------------------------------------------------------------------
    # Stage 3: TEMPORAL GROUPING
    # ------------------------------------------------------------------

    def _form_temporal_groups(self, records: List[FrameRecord]) -> List[TemporalGroup]:
        """Group consecutive near-identical frames; pick one representative per group.

        Groups are broken by: missing frames, duplicates after an active frame,
        and any frame whose change_score > _PIXEL_CHANGE_THRESHOLD.
        This is pure temporal compression — no frame is deleted from accounting.
        """
        groups: List[TemporalGroup] = []
        current: List[FrameRecord] = []

        def _flush(recs: List[FrameRecord]) -> None:
            if not recs:
                return
            groups.append(self._make_group(recs, len(groups)))

        for rec in records:
            if rec.pixel_status in ("NO_IMAGE", "FAILED"):
                _flush(current)
                current = []
                continue

            if rec.is_duplicate:
                if current:
                    current.append(rec)
                continue

            if rec.is_active and current:
                _flush(current)
                current = [rec]
            else:
                current.append(rec)

        _flush(current)

        # Tag each frame with its group
        fid_to_group: Dict[str, int] = {}
        for g in groups:
            for fid in g.frame_ids:
                fid_to_group[fid] = g.group_index
        for rec in records:
            if rec.frame_id in fid_to_group:
                rec.group_index = fid_to_group[rec.frame_id]

        return groups

    def _make_group(self, frames: List[FrameRecord], idx: int) -> TemporalGroup:
        # Best representative: highest text density (most legible UI)
        rep = max(
            frames,
            key=lambda r: (r.exists, r.text_density_score, -r.change_score),
        )
        mean_cs = sum(r.change_score for r in frames) / len(frames)
        return TemporalGroup(
            group_index=idx,
            frame_ids=[r.frame_id for r in frames],
            representative_frame_id=rep.frame_id,
            representative_path=rep.image_path if rep.exists else "",
            start_ts=frames[0].timestamp_sec,
            end_ts=frames[-1].timestamp_sec,
            mean_change_score=mean_cs,
        )

    # ------------------------------------------------------------------
    # Stage 4: LOCAL OCR
    # ------------------------------------------------------------------

    def _run_ocr(
        self, frame_path: str, group_index: int, frame_id: str
    ) -> List[RawFinding]:
        """Run EasyOCR on the Serum panel region. Generic numeric fragments only."""
        try:
            import easyocr
            from PIL import Image
        except ImportError:
            return []

        try:
            if self._ocr_reader is None:
                self._ocr_reader = easyocr.Reader(["en"], gpu=True)

            im = Image.open(frame_path)
            cx0, cy0, cx1, cy1 = _SERUM_PANEL_CROP
            panel = im.crop((cx0, cy0, min(cx1, im.width), min(cy1, im.height)))

            import io
            buf = io.BytesIO()
            panel.convert("RGB").save(buf, format="PNG")
            roi_hash = hashlib.sha256(buf.getvalue()).hexdigest()

            detections = self._ocr_reader.readtext(
                panel,
                detail=1,
                allowlist="0123456789.-+eEsSmMhHzZkKdD%:",
                mag_ratio=1.5,
                text_threshold=0.5,
            )
            findings: List[RawFinding] = []
            for _bbox, text, conf in detections:
                if not re.search(r"\d", text):
                    continue
                findings.append(RawFinding(
                    frame_id=frame_id,
                    group_index=group_index,
                    claimed_panel="",   # OCR fragments carry no panel context
                    claimed_label="",   # no label context from OCR alone
                    raw_value=text,
                    source_type="ocr",
                    ocr_confidence=float(conf),
                    evidence_hash=roi_hash,
                ))
            return findings
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Stage 5: LOCAL VLM — evidence-first, no target parameter hint
    # ------------------------------------------------------------------

    def _run_vlm(
        self, engine: Any, frame_path: str, frame_id: str, group_index: int
    ) -> List[RawFinding]:
        """Ask the VLM what Serum controls are visible. No control_id given."""
        try:
            raw_list = engine.observe_frame_all_controls(frame_path)
        except Exception:
            return []

        findings: List[RawFinding] = []
        for item in raw_list:
            findings.append(RawFinding(
                frame_id=frame_id,
                group_index=group_index,
                claimed_panel=item.get("panel", ""),
                claimed_label=item.get("label", ""),
                raw_value=item.get("value", ""),
                source_type="vlm",
                vlm_confidence=float(item.get("confidence", 0.0)),
                evidence_hash=item.get("evidence_hash", ""),
            ))
        return findings

    # ------------------------------------------------------------------
    # Stage 6: IDENTITY RESOLUTION
    # ------------------------------------------------------------------

    def _resolve_identities(self, raw_findings: List[RawFinding]) -> List[ResolvedFinding]:
        """Map (claimed_panel, claimed_label) to canonical control_id via atlas.

        OCR-only fragments (no label context) remain UNRESOLVED.
        VLM findings with sufficient panel+label context resolve via atlas.
        """
        from serum2.reference.serum_atlas import normalize_control, EXACT, ALIAS, AMBIGUOUS, UNRESOLVED

        resolved: List[ResolvedFinding] = []
        for f in raw_findings:
            if f.source_type == "ocr":
                # OCR fragments carry no label context; identity cannot be resolved
                resolved.append(ResolvedFinding(raw=f, resolved_control_id=None, resolution_status="UNRESOLVED"))
                continue

            combined = f"{f.claimed_panel} {f.claimed_label}".strip()
            ctx = f.claimed_panel.lower().replace(" ", "")
            r = normalize_control(combined, context=ctx)

            if r.status in (EXACT, ALIAS):
                resolved.append(ResolvedFinding(raw=f, resolved_control_id=r.canonical_id, resolution_status=r.status))
            elif r.status == AMBIGUOUS:
                resolved.append(ResolvedFinding(raw=f, resolved_control_id=None, resolution_status="AMBIGUOUS"))
            else:
                resolved.append(ResolvedFinding(raw=f, resolved_control_id=None, resolution_status="UNRESOLVED"))
        return resolved

    # ------------------------------------------------------------------
    # Stage 7: ADJUDICATION — GAP A/B/C unchanged
    # ------------------------------------------------------------------

    def _adjudicate(
        self, resolved: List[ResolvedFinding], groups: List[TemporalGroup], engine: Any,
        *, numeric_tol: float = 1e-3,
    ) -> Dict[str, Any]:
        """Group by resolved_control_id; read the real VALUE via a targeted ROI, then
        adjudicate across distinct temporal groups via the existing policy.

        Stage 5's full-frame VLM census (_run_vlm/observe_frame_all_controls) is a candidate-
        DISCOVERY signal only: "this control_id appears to be visible in this temporal group,
        per its claimed panel+label". Its own claimed VALUE text is discarded here and never
        used as evidence -- that is exactly the full-frame free-text reading Qwen's own
        documented findings (qwen_ui_findings.txt) show inventing numeric values. The real
        value for each (control_id, group) the full-frame census flagged as present is read
        fresh via ObservationEngine.observe_control_in_frame() -- the proven, audited
        locate -> crop -> transcribe -> explicit-UNREADABLE ROI mechanism (never recreated
        here, only invoked) -- against that group's own representative frame. One real read
        per (control_id, group) pair, not per raw finding, since group membership (not the
        full-frame guess) is the only thing being reused from Stage 5/6.

        Corroboration requires two genuinely distinct temporal groups (different
        group_index) to agree, exactly as before -- unchanged from GAP B.
        """
        from serum2.producer.observation_policy import (
            ObservationCandidate as PolicyCandidate,
            OUTCOME_CANDIDATE, adjudicate,
        )
        from serum2.producer.expected_inventory import resolve_observation_type

        group_by_index: Dict[int, TemporalGroup] = {g.group_index: g for g in groups}

        # Group by control_id
        by_control: Dict[str, List[ResolvedFinding]] = {}
        for rf in resolved:
            if rf.resolved_control_id is not None:
                by_control.setdefault(rf.resolved_control_id, []).append(rf)

        results: Dict[str, Any] = {}

        for control_id, rfs in by_control.items():
            # Which ObservationEngine strategy actually applies to THIS control, from the
            # same Atlas-derived mapping expected_inventory.py uses -- never hardcoded to
            # NUMERIC. A toggle (ENABLE_STATE), an enum (SELECTOR), or a route (ROUTE) would
            # previously be force-fed through numeric parsing and silently fail to observe at
            # all; an Atlas-unresolvable control_id is explicit UNREADABLE, never guessed.
            _obs_kind, strategy = resolve_observation_type(control_id)
            if strategy is None:
                from serum2.producer.observation_policy import ObservationCandidate as PC
                results[control_id] = PC(
                    outcome="UNREADABLE", control_id=control_id,
                    detail="control_id not resolvable in Atlas; no observation strategy",
                )
                continue

            # Distinct temporal groups the full-frame census claimed to see this control in --
            # a discovery signal only, spending one real targeted ROI read per group, never
            # per raw finding (repeated claims within the same group are not independent).
            candidate_group_indices = sorted({rf.raw.group_index for rf in rfs})

            policy_candidates: List[PolicyCandidate] = []
            for gi in candidate_group_indices:
                group = group_by_index.get(gi)
                if group is None or not group.representative_path:
                    continue
                if engine is None:
                    continue  # no local VLM/OCR available on this machine; contributes nothing
                try:
                    roi_result = engine.observe_control_in_frame(group.representative_path, control_id)
                except Exception:
                    continue
                if getattr(roi_result, "value", None) is None:
                    continue  # UNREADABLE/IDENTITY_UNRESOLVED at this group -- no fabricated candidate
                policy_candidates.append(PolicyCandidate(
                    outcome=OUTCOME_CANDIDATE,
                    value=roi_result.value,
                    confidence=getattr(roi_result, "confidence", 0.0),
                    source=getattr(roi_result, "source", "") or "roi_extraction",
                    control_id=control_id,
                    evidence_hash=getattr(roi_result, "evidence_hash", None),
                ))

            if not policy_candidates:
                from serum2.producer.observation_policy import ObservationCandidate as PC
                results[control_id] = PC(outcome="UNREADABLE", control_id=control_id)
                continue

            results[control_id] = adjudicate(
                policy_candidates,
                numeric_tol=numeric_tol,
                requested_control_id=control_id,
            )

        return results

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        manifest: dict,
        *,
        run_dir: Optional[Path] = None,
        contract: Optional[dict] = None,
    ) -> ObservationCensus:
        """Run all 10 stages. Returns ObservationCensus with full accounting.

        Stages 4-5 require PIL + EasyOCR + Qwen (LOCAL machine only).
        If unavailable, those stages are skipped and the census still
        records all frames through Stage 3 (pixel accounting is always done).
        """
        from serum2.producer.w2_fast_path import (
            contract_covered_controls as _cc, filter_contract_covered,
        )
        from serum2.producer.observation_policy import (
            OUTCOME_OBSERVED, OUTCOME_AMBIGUOUS, OUTCOME_UNREADABLE,
            OUTCOME_IDENTITY_UNRESOLVED,
        )

        census = ObservationCensus()

        # Stage 1: Ingest — ALL frames
        records = self._ingest_frames(manifest)
        census.total_frames = len(records)
        census.frame_records = records

        # Stage 2: Pixel analysis — zero token, zero remote calls
        self._pixel_analysis(records)
        census.frames_pixel_processed = sum(
            1 for r in records if r.pixel_status in ("OK", "DUPLICATE")
        )
        census.frames_failed = sum(
            1 for r in records if r.pixel_status in ("NO_IMAGE", "FAILED")
        )

        # Stage 3: Temporal grouping
        groups = self._form_temporal_groups(records)
        census.temporal_groups = groups
        census.n_temporal_groups = len(groups)

        # Stages 4-5 only for groups with real images
        active_groups = [
            g for g in groups if g.representative_path and Path(g.representative_path).exists()
        ]

        # Attempt to load ObservationEngine (needs qwen/torch on LOCAL only), unless a caller
        # already injected one (real singleton reuse, or a test fake).
        engine = self._engine
        if engine is None:
            try:
                from serum2.producer.observation_engine import ObservationEngine
                engine = ObservationEngine()
                self._engine = engine
            except Exception:
                pass

        for g in active_groups:
            census.candidate_regions += 1

            # Stage 4: Local OCR (generic, no parameter names)
            ocr_findings = self._run_ocr(
                g.representative_path, g.group_index, g.representative_frame_id
            )
            if ocr_findings:
                census.ocr_attempts += 1
                census.raw_findings.extend(ocr_findings)

            # Stage 5: Local VLM census (evidence-first)
            if engine is not None:
                vlm_findings = self._run_vlm(
                    engine, g.representative_path, g.representative_frame_id, g.group_index
                )
                if vlm_findings:
                    census.vlm_attempts += 1
                    census.local_vlm_calls += 1
                    census.raw_findings.extend(vlm_findings)

        # Stage 6: Identity resolution
        resolved = self._resolve_identities(census.raw_findings)
        census.resolved_findings = resolved
        census.identity_attempts = sum(1 for r in resolved if r.raw.source_type == "vlm")

        # Stage 7: Adjudication (GAP-A/B/C corroboration policy UNTOUCHED; per-value evidence
        # now comes from a real targeted ROI read via engine.observe_control_in_frame(), not
        # the full-frame census's own claimed value -- see _adjudicate()'s docstring)
        adjudicated = self._adjudicate(resolved, groups, engine)
        census.adjudicated = adjudicated

        for cid, result in adjudicated.items():
            outcome = getattr(result, "outcome", "UNREADABLE")
            if outcome == OUTCOME_OBSERVED:
                census.observed += 1
            elif outcome == OUTCOME_AMBIGUOUS:
                census.ambiguous += 1
            elif outcome == OUTCOME_UNREADABLE:
                census.unreadable += 1
            elif outcome == OUTCOME_IDENTITY_UNRESOLVED:
                census.identity_unresolved += 1

        # Approximate duplicate evidence rejection count
        total_resolvable = sum(1 for r in resolved if r.resolved_control_id is not None)
        census.duplicate_evidence_rejected = max(0, total_resolvable - len(adjudicated))

        # Stage 8: Contract filter — post-observation only
        if contract is None:
            try:
                from serum2.producer.w2_fast_path import load_contract
                contract = load_contract()
            except Exception:
                contract = None

        covered = _cc(contract) if contract is not None else set()
        observed_ids = [
            cid for cid, r in adjudicated.items()
            if getattr(r, "outcome", "") == OUTCOME_OBSERVED
        ]
        admissible, excluded = filter_contract_covered(observed_ids, covered)
        census.admissible = admissible
        census.excluded = excluded
        census.admissible_observed = len(admissible)

        # Stages 9 (ledger) and 10 (stop) are handled by runner.py
        # from census.to_metrics_json() — always fully auditable
        return census
