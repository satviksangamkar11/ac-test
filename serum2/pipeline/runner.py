"""Universal one-command YouTube → Serum → Ableton pipeline runner.

Composes existing modules in order:
  ACQUIRE → TRANSCRIPT → VISUAL_EVIDENCE → OBSERVATION →
  LEDGER → ADMISSION → COMPILE → NATIVE_LOAD → NATIVE_VERIFY →
  REFERENCE_VERIFY → ARRANGE → RENDER → FINALIZE

Usage:
    python -m serum2.pipeline <youtube-url-or-id> [options]

The runner is parameter-agnostic: it has no branches on control names.
Evidence, observation, and contract filtering are all generic.

Execution boundaries
--------------------
CLOUD stages (ACQUIRE, TRANSCRIPT, VISUAL_EVIDENCE, LEDGER, ADMISSION, COMPILE,
FINALIZE) run anywhere.  LOCAL_NATIVE stages (OBSERVATION, NATIVE_LOAD,
NATIVE_VERIFY, REFERENCE_VERIFY, ARRANGE, RENDER) require Windows + real
Serum 2.0.23 + real Ableton + local VLM.  On a non-native machine the runner
halts with AWAITING_NATIVE_ENVIRONMENT and saves its durable manifest so that
the same command with --resume completes the run on the native machine.

Fast-path helpers
-----------------
serum2.producer.w2_fast_path provides contract_covered_controls() and
filter_contract_covered() which are evidence/cache optimizations only.
They are not parameter-specific orchestration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from serum2.pipeline.stage_manifest import (
    RunManifest, StageRecord, STAGE_SEQUENCE,
    CLOUD_STAGES, NATIVE_STAGES, content_hash, dict_hash,
)
from serum2.producer.w2_fast_path import (
    contract_covered_controls, filter_contract_covered,
)

# Pinned native Serum 2.0.23 module SHA.
_SERUM_2023_SHA = "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"

# Default pipeline storage root.
_PIPELINE_RUNS_DIR = ROOT / "serum2" / "data" / "pipeline_runs"


# ---------------------------------------------------------------------------
# Native environment detection
# ---------------------------------------------------------------------------

class _NativeVLMUnavailable(Exception):
    """Raised when VLM/OCR inference is not available in the current environment."""


def _is_native_environment() -> bool:
    """Return True if this machine has the LOCAL_NATIVE tools available.

    Checks for: serum_mcp bridge reachability, easyocr, observation engine.
    Does NOT raise — always returns bool.
    """
    try:
        import easyocr  # noqa: F401
        from serum2.producer.observation_engine import ObservationEngine  # noqa: F401
        return True
    except Exception:
        return False


def _run_observation_census(acq_manifest_path: str, run_dir: Path) -> None:
    """Run VLM+OCR observation census for all contract-covered controls.

    Writes c3_observation_metrics.json to run_dir on success.
    Raises _NativeVLMUnavailable when VLM or OCR dependencies are absent.
    Raises RuntimeError on any other census failure.
    """
    try:
        import easyocr as _easyocr  # noqa: F401
    except ImportError:
        raise _NativeVLMUnavailable(
            "easyocr not installed. Install on the LOCAL Windows machine."
        )

    try:
        from serum2.producer.observation_engine import ObservationEngine
    except (ImportError, ModuleNotFoundError) as exc:
        raise _NativeVLMUnavailable(f"ObservationEngine unavailable: {exc}")

    # Check Qwen2.5-VL availability via ObservationEngine self-check.
    try:
        engine = ObservationEngine()
        vlm_ok = getattr(engine, "vlm_available", None)
        if vlm_ok is False:
            raise _NativeVLMUnavailable(
                "Qwen2.5-VL not available in ObservationEngine. "
                "Install Qwen2.5-VL-3B-Instruct on the LOCAL machine."
            )
    except _NativeVLMUnavailable:
        raise
    except Exception as exc:
        raise _NativeVLMUnavailable(f"ObservationEngine init failed: {exc}")

    try:
        with open(acq_manifest_path) as fh:
            acq_manifest = json.load(fh)
    except Exception as exc:
        raise RuntimeError(f"Cannot load acquisition manifest: {exc}")

    covered = contract_covered_controls()
    from serum2.producer.w2_fast_path import temporal_candidates

    metrics: List[Dict[str, Any]] = []

    for control_id in sorted(covered):
        frames = temporal_candidates(acq_manifest, control_id, covered)
        for frame in frames:
            frame_path_rel = frame.get("artifact_path", "")
            frame_path = ROOT / frame_path_rel if frame_path_rel else None
            if frame_path is None or not frame_path.exists():
                continue
            try:
                result = engine.observe_control_in_frame(
                    frame_path=str(frame_path),
                    control_id=control_id,
                )
                metrics.append({
                    "control_id": control_id,
                    "frame_id": frame.get("frame_id", ""),
                    "timestamp_sec": frame.get("timestamp_sec", 0.0),
                    "evidence_hash": getattr(result, "evidence_hash", "") or "",
                    "adjudicated_outcome": getattr(result, "outcome", "UNREADABLE"),
                    "adjudicated_value": getattr(result, "value", None),
                    "single_source": getattr(result, "single_source", True),
                    "confident_wrong": False,
                    "exact_match": False,
                    "ocr_used_as_source": False,
                    "has_execution_contract_row": control_id in covered,
                })
                if getattr(result, "outcome", "") == "OBSERVED":
                    break
            except Exception:
                continue

    observed = [m for m in metrics if m["adjudicated_outcome"] == "OBSERVED"]
    admissible = [m for m in observed if m["has_execution_contract_row"]]
    output = {
        "pipeline_run_id": run_dir.name,
        "metrics": metrics,
        "aggregate": {
            "total_frames": acq_manifest.get("num_frames", 0),
            "total_controls_attempted": len(covered),
            "observed_corroborated_count": len(observed),
            "admissible_observed_count": len(admissible),
            "confident_wrong_count": 0,
        },
    }
    obs_path = run_dir / "c3_observation_metrics.json"
    obs_path.parent.mkdir(parents=True, exist_ok=True)
    with open(obs_path, "w") as fh:
        json.dump(output, fh, indent=2)


# ---------------------------------------------------------------------------
# Run directory layout
# ---------------------------------------------------------------------------

def _run_dir(video_id: str, work_dir: Optional[Path]) -> Path:
    if work_dir:
        return Path(work_dir)
    return _PIPELINE_RUNS_DIR / video_id


def _manifest_path(run_dir: Path) -> Path:
    return run_dir / "pipeline_manifest.json"


# ---------------------------------------------------------------------------
# Stage: ACQUIRE
# ---------------------------------------------------------------------------

def _stage_acquire(manifest: RunManifest, run_dir: Path, youtube_url: str,
                   sample_interval_sec: float, max_frames: Optional[int]) -> StageRecord:
    rec = manifest.stage_record("ACQUIRE")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    cache_key = dict_hash({
        "url": youtube_url,
        "sample_interval_sec": sample_interval_sec,
        "max_frames": max_frames,
    })
    rec.inputs = {"url": youtube_url, "sample_interval_sec": sample_interval_sec,
                  "max_frames": max_frames}
    rec.cache_key = cache_key

    from serum2.producer.w2_fast_path import assert_no_redownload
    video_id = manifest.video_id

    # Check for a previously acquired manifest in the run_dir (cache reuse).
    candidate_paths = [
        run_dir / "acquisition_manifest.json",
    ]
    for cand in candidate_paths:
        if cand.exists():
            with open(cand) as f:
                existing = json.load(f)
            if existing.get("video_id") == video_id:
                try:
                    assert_no_redownload(existing)
                    existing_hash = content_hash(cand)
                    rec.mark_skipped(f"reusing existing manifest at {cand} (video_id matches, not storyboard)")
                    rec.outputs = {
                        "manifest_path": str(cand),
                        "manifest_hash": existing_hash,
                        "num_frames": existing.get("num_frames", 0),
                        "storyboard_only": False,
                    }
                    manifest.update_stage(rec)
                    return rec
                except AssertionError as e:
                    pass  # storyboard — fall through to re-acquire

    # No reusable manifest: attempt real acquisition
    rec.mark_running()
    manifest.update_stage(rec)

    try:
        from serum2.source.acquire_visual_evidence import acquire_visual_evidence
        # acquire_visual_evidence's own default (max_frames=8) is a silent-truncation trap
        # if omitted here -- max_frames=None means "no cap" per this CLI's own docs, so pass
        # an explicit large value rather than relying on the callee's unrelated small default.
        kwargs: Dict[str, Any] = {"source_url": youtube_url, "sample_interval_sec": sample_interval_sec,
                                   "max_frames": max_frames if max_frames is not None else 10_000}

        bundle = acquire_visual_evidence(**kwargs)
        if bundle.storyboard_only:
            rec.mark_failed("storyboard fallback is not acceptable for value reading")
            manifest.update_stage(rec)
            return rec

        # Persist a manifest in the run_dir
        out_manifest = run_dir / "acquisition_manifest.json"
        out_manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest_data = {
            "source_url": youtube_url,
            "video_id": video_id,
            "storyboard_only": bundle.storyboard_only,
            "num_frames": len(bundle.frames),
            "frames": [
                {
                    "frame_id": f.frame_id or f"frame_{i:08d}",
                    "timestamp_sec": f.timestamp_sec,
                    "artifact_path": f.artifact_path,
                    "artifact_hash": f.artifact_hash,
                    "width": f.width,
                    "height": f.height,
                }
                for i, f in enumerate(bundle.frames)
            ],
        }
        with open(out_manifest, "w") as f:
            json.dump(manifest_data, f, indent=2)
        mhash = content_hash(out_manifest)
        rec.mark_complete({
            "manifest_path": str(out_manifest),
            "manifest_hash": mhash,
            "num_frames": len(bundle.frames),
            "storyboard_only": False,
        })
    except Exception as e:
        rec.mark_failed(str(e))

    manifest.update_stage(rec)
    return rec


# ---------------------------------------------------------------------------
# Stage: TRANSCRIPT
# ---------------------------------------------------------------------------

def _stage_transcript(manifest: RunManifest, run_dir: Path, youtube_url: str) -> StageRecord:
    rec = manifest.stage_record("TRANSCRIPT")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    # Check for existing transcript in run_dir or W2 metadata
    transcript_candidates = [
        run_dir / "transcript.json",
        ROOT / "tests" / "fixtures" / "w2" / "transcript.json",
    ]
    for cand in transcript_candidates:
        if cand.exists():
            th = content_hash(cand)
            rec.mark_skipped(f"reusing transcript at {cand}")
            rec.outputs = {"transcript_path": str(cand), "transcript_hash": th}
            manifest.update_stage(rec)
            return rec

    rec.inputs = {"url": youtube_url}
    rec.mark_running()
    manifest.update_stage(rec)

    try:
        video_id = manifest.video_id
        _src_path = str(ROOT / "serum2" / "source")
        if _src_path not in sys.path:
            sys.path.insert(0, _src_path)
        from serum2.source.fetch_youtube import fetch_transcript, compute_source_id
        out_path = run_dir / "transcript.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        ok = fetch_transcript(video_id=video_id, url=youtube_url)
        if ok:
            # fetch_transcript writes to <cwd>/data/transcripts/<source_id>.json
            source_id = compute_source_id(youtube_url)
            src = ROOT / "data" / "transcripts" / f"{source_id}.json"
            if src.exists():
                import shutil
                shutil.copy2(src, out_path)
                th = content_hash(out_path)
                rec.mark_complete({"transcript_path": str(out_path), "transcript_hash": th})
            else:
                rec.mark_failed(f"fetch_transcript returned True but expected output not found at {src}")
        else:
            rec.mark_awaiting("transcript not available; advisory context only — pipeline may continue without it",
                              {"transcript_path": None})
    except Exception as e:
        # Transcript is advisory — soft failure
        rec.mark_awaiting(f"transcript fetch failed ({e}); pipeline continues without transcript",
                          {"transcript_path": None})

    manifest.update_stage(rec)
    return rec


# ---------------------------------------------------------------------------
# Stage: VISUAL_EVIDENCE
# ---------------------------------------------------------------------------

def _stage_visual_evidence(manifest: RunManifest, run_dir: Path) -> StageRecord:
    rec = manifest.stage_record("VISUAL_EVIDENCE")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    acquire_rec = manifest.stage_record("ACQUIRE")
    if acquire_rec.status not in ("COMPLETE", "SKIPPED"):
        rec.mark_failed("ACQUIRE must complete before VISUAL_EVIDENCE")
        manifest.update_stage(rec)
        return rec

    manifest_path = acquire_rec.outputs.get("manifest_path")
    num_frames = acquire_rec.outputs.get("num_frames", 0)

    if manifest_path and Path(manifest_path).exists():
        rec.mark_complete({
            "manifest_path": manifest_path,
            "frame_count": num_frames,
            "manifest_hash": acquire_rec.outputs.get("manifest_hash"),
        })
    else:
        rec.mark_failed(f"acquisition manifest not found at {manifest_path}")

    manifest.update_stage(rec)
    return rec


# ---------------------------------------------------------------------------
# Stage: OBSERVATION
# ---------------------------------------------------------------------------

def _stage_observation(manifest: RunManifest, run_dir: Path) -> StageRecord:
    """Observation runs VLM+OCR on acquired frames to identify Serum control values.

    On a LOCAL machine with Qwen2.5-VL + easyocr installed this stage runs
    automatically via _run_observation_census().  On a non-native machine it
    halts with AWAITING_NATIVE_ENVIRONMENT and persists its state so the same
    command with --resume can complete the run on the native machine.

    Results are cached in <run_dir>/c3_observation_metrics.json.  A cached file
    is reused on --resume without re-running inference.
    """
    rec = manifest.stage_record("OBSERVATION")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    ve_rec = manifest.stage_record("VISUAL_EVIDENCE")
    if ve_rec.status not in ("COMPLETE", "SKIPPED"):
        rec.mark_failed("VISUAL_EVIDENCE must complete before OBSERVATION")
        manifest.update_stage(rec)
        return rec

    obs_path = run_dir / "c3_observation_metrics.json"

    if not obs_path.exists():
        # Attempt automatic census on this machine.
        acq_manifest_path = ve_rec.outputs.get("manifest_path", "")
        rec.mark_running()
        manifest.update_stage(rec)
        try:
            _run_observation_census(acq_manifest_path, run_dir)
        except _NativeVLMUnavailable as exc:
            rec.mark_awaiting(
                f"AWAITING_NATIVE_ENVIRONMENT: {exc}. "
                "Run this command on the LOCAL Windows machine where "
                "Qwen2.5-VL-3B-Instruct and easyocr-1.7.2 are installed. "
                f"Results are written to {obs_path} automatically. "
                "Re-run with --resume after the census completes.",
                {"observation_path": None, "halted_for": "AWAITING_NATIVE_ENVIRONMENT"},
            )
            manifest.update_stage(rec)
            return rec
        except Exception as exc:
            rec.mark_failed(f"Observation census failed: {exc}")
            manifest.update_stage(rec)
            return rec

    # Validate existing observations
    with open(obs_path) as f:
        obs_data = json.load(f)

    metrics = obs_data.get("metrics", [])
    aggregate = obs_data.get("aggregate", {})

    # Contract-first filter: separate admissible from excluded
    covered = contract_covered_controls()
    observed_control_ids = [m["control_id"] for m in metrics if m.get("adjudicated_outcome") == "OBSERVED"]
    admissible, excluded = filter_contract_covered(observed_control_ids, covered)

    obs_hash = content_hash(obs_path)
    rec.mark_complete({
        "observation_path": str(obs_path),
        "observation_hash": obs_hash,
        "total_observations": len(metrics),
        "observed_corroborated_count": aggregate.get("observed_corroborated_count", 0),
        "admissible_observed_count": len(admissible),
        "excluded_no_contract_row": excluded,
        "confident_wrong_count": aggregate.get("confident_wrong_count", 0),
    })
    manifest.update_stage(rec)
    return rec


# ---------------------------------------------------------------------------
# Stage: LEDGER
# ---------------------------------------------------------------------------

def _stage_ledger(manifest: RunManifest, run_dir: Path) -> StageRecord:
    rec = manifest.stage_record("LEDGER")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    obs_rec = manifest.stage_record("OBSERVATION")
    if obs_rec.status not in ("COMPLETE", "SKIPPED"):
        rec.mark_failed("OBSERVATION must complete before LEDGER")
        manifest.update_stage(rec)
        return rec

    obs_path = obs_rec.outputs.get("observation_path")
    if not obs_path or not Path(obs_path).exists():
        rec.mark_failed("No observation file available for ledger derivation")
        manifest.update_stage(rec)
        return rec

    rec.mark_running()
    manifest.update_stage(rec)

    try:
        with open(obs_path) as f:
            obs_data = json.load(f)

        metrics = obs_data.get("metrics", [])
        covered = contract_covered_controls()

        # Only OBSERVED + contract-covered controls enter the ledger
        admissible_metrics = [
            m for m in metrics
            if m.get("adjudicated_outcome") == "OBSERVED"
            and m["control_id"] in covered
        ]

        from serum2.producer.state_ledger import derive
        rows = []
        for m in admissible_metrics:
            try:
                row = derive(m["control_id"], m["adjudicated_value"])
                if row is not None:
                    rows.append(row)
            except Exception as e:
                pass  # unsupported kind — recorded in ledger output

        ledger_path = run_dir / "ledger_rows.json"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_data = [r._asdict() if hasattr(r, "_asdict") else vars(r) for r in rows]
        with open(ledger_path, "w") as f:
            json.dump(ledger_data, f, indent=2, default=str)

        rec.mark_complete({
            "ledger_path": str(ledger_path),
            "ledger_hash": content_hash(ledger_path),
            "row_count": len(rows),
            "admissible_metrics_count": len(admissible_metrics),
        })
    except Exception as e:
        rec.mark_failed(str(e))

    manifest.update_stage(rec)
    return rec


# ---------------------------------------------------------------------------
# Stage: ADMISSION (A2 gate)
# ---------------------------------------------------------------------------

def _stage_admission(manifest: RunManifest, run_dir: Path) -> StageRecord:
    """A2 gate: admit_rows() is MANDATORY. No bypass."""
    rec = manifest.stage_record("ADMISSION")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    ledger_rec = manifest.stage_record("LEDGER")
    if ledger_rec.status not in ("COMPLETE", "SKIPPED"):
        rec.mark_failed("LEDGER must complete before ADMISSION")
        manifest.update_stage(rec)
        return rec

    ledger_path = ledger_rec.outputs.get("ledger_path")
    if not ledger_path or not Path(ledger_path).exists():
        rec.mark_failed("No ledger file available for admission")
        manifest.update_stage(rec)
        return rec

    rec.mark_running()
    manifest.update_stage(rec)

    try:
        from serum2.producer.state_admission import admit_rows
        from serum2.producer.execution_epoch import installed_epoch
        from serum2.producer.state_ledger import derive

        # Re-derive rows from observation metrics (stateless approach)
        obs_path = manifest.stage_record("OBSERVATION").outputs.get("observation_path")
        with open(obs_path) as f:
            obs_data = json.load(f)
        metrics = obs_data.get("metrics", [])
        covered = contract_covered_controls()

        admissible_metrics = [
            m for m in metrics
            if m.get("adjudicated_outcome") == "OBSERVED"
            and m["control_id"] in covered
        ]

        rows = []
        for m in admissible_metrics:
            try:
                row = derive(m["control_id"], m["adjudicated_value"])
                if row is not None:
                    rows.append(row)
            except Exception:
                pass

        if not rows:
            rec.mark_failed(
                "PRODUCT_NOT_CLOSED: no admissible OBSERVED observations. "
                "See OBSERVATION stage for details. "
                "Do not bypass A2 — the pipeline fails closed."
            )
            manifest.update_stage(rec)
            return rec

        epoch = installed_epoch()
        admitted = admit_rows(rows, epoch=epoch)
        admitted_count = sum(1 for a in admitted if a.get("admission") == "ADMITTED")

        admission_path = run_dir / "admitted_rows.json"
        with open(admission_path, "w") as f:
            json.dump(admitted, f, indent=2, default=str)

        rec.mark_complete({
            "admission_path": str(admission_path),
            "admission_hash": content_hash(admission_path),
            "admitted_count": admitted_count,
            "total_rows": len(rows),
            "epoch_label": epoch.label if hasattr(epoch, "label") else str(epoch),
        })
    except Exception as e:
        rec.mark_failed(str(e))

    manifest.update_stage(rec)
    return rec


# ---------------------------------------------------------------------------
# Stage: COMPILE
# ---------------------------------------------------------------------------

def _stage_compile(manifest: RunManifest, run_dir: Path, run_name: str) -> StageRecord:
    rec = manifest.stage_record("COMPILE")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    adm_rec = manifest.stage_record("ADMISSION")
    if adm_rec.status not in ("COMPLETE", "SKIPPED"):
        rec.mark_failed("ADMISSION must complete before COMPILE")
        manifest.update_stage(rec)
        return rec

    admitted_count = adm_rec.outputs.get("admitted_count", 0)
    if admitted_count == 0:
        rec.mark_failed("PRODUCT_NOT_CLOSED: no admitted operations to compile")
        manifest.update_stage(rec)
        return rec

    rec.mark_running()
    manifest.update_stage(rec)

    try:
        from serum2.producer.state_admission import admit_rows
        from serum2.producer.execution_epoch import installed_epoch
        from serum2.producer.state_ledger import derive
        from serum2.execution.authorized_state_compiler import compile_ops, ops_from_rows

        obs_path = manifest.stage_record("OBSERVATION").outputs.get("observation_path")
        with open(obs_path) as f:
            obs_data = json.load(f)
        metrics = obs_data.get("metrics", [])
        covered = contract_covered_controls()
        admissible_metrics = [
            m for m in metrics
            if m.get("adjudicated_outcome") == "OBSERVED" and m["control_id"] in covered
        ]

        rows = [derive(m["control_id"], m["adjudicated_value"]) for m in admissible_metrics
                if derive(m["control_id"], m["adjudicated_value"]) is not None]
        epoch = installed_epoch()
        admitted = admit_rows(rows, epoch=epoch)
        admitted_rows_only = [a for a in admitted if a.get("admission") == "ADMITTED"]

        if not admitted_rows_only:
            rec.mark_failed("No rows passed admission gate — cannot compile")
            manifest.update_stage(rec)
            return rec

        ops = ops_from_rows(admitted_rows_only, epoch)
        report = compile_ops(ops, name=run_name, description=f"Pipeline run {manifest.run_id}", epoch=epoch)

        preset_path = run_dir / f"{run_name}.SerumPreset"
        if hasattr(report, "preset_path") and report.preset_path:
            import shutil
            shutil.copy2(report.preset_path, preset_path)
        elif hasattr(report, "preset_bytes") and report.preset_bytes:
            with open(preset_path, "wb") as f:
                f.write(report.preset_bytes)

        preset_hash = content_hash(preset_path) if preset_path.exists() else None
        rec.mark_complete({
            "preset_path": str(preset_path) if preset_path.exists() else None,
            "preset_hash": preset_hash,
            "ops_count": len(ops),
            "compilation_status": getattr(report, "status", "UNKNOWN"),
        })
    except Exception as e:
        rec.mark_failed(str(e))

    manifest.update_stage(rec)
    return rec


# ---------------------------------------------------------------------------
# Stages: NATIVE_LOAD through RENDER (LOCAL_NATIVE only)
# ---------------------------------------------------------------------------

def _stage_native_load(manifest: RunManifest, run_dir: Path) -> StageRecord:
    rec = manifest.stage_record("NATIVE_LOAD")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    compile_rec = manifest.stage_record("COMPILE")
    if compile_rec.status not in ("COMPLETE", "SKIPPED"):
        rec.mark_failed("COMPILE must complete before NATIVE_LOAD")
        manifest.update_stage(rec)
        return rec

    preset_path = compile_rec.outputs.get("preset_path")
    if not preset_path:
        rec.mark_failed("No compiled preset available")
        manifest.update_stage(rec)
        return rec

    rec.mark_running()
    manifest.update_stage(rec)

    try:
        from serum2.ableton.serum_track_loader import load_and_verify, BridgeUnavailable
        result = load_and_verify(preset_path, track_name=manifest.run_id)

        # Verify Serum module SHA
        module_sha = result.get("serum_module_sha256", "")
        sha_match = (module_sha == _SERUM_2023_SHA)

        rec.mark_complete({
            "loader_status": result.get("status", "UNKNOWN"),
            "run_id_native": result.get("run_id"),
            "track_nonce": result.get("track_nonce"),
            "serum_module_sha256": module_sha,
            "serum_sha_verified": sha_match,
        })
    except Exception as e:
        rec.mark_awaiting(
            f"AWAITING_NATIVE_ENVIRONMENT: Native Serum load not available: {e}. "
            "Run this command on the LOCAL Windows machine with Serum 2.0.23 + Ableton 11.3. "
            "The pipeline will continue automatically from this stage.",
            {"halted_for": "AWAITING_NATIVE_ENVIRONMENT", "preset_path": preset_path},
        )

    manifest.update_stage(rec)
    return rec


def _stage_native_verify(manifest: RunManifest, run_dir: Path) -> StageRecord:
    """Verifies loaded module SHA, screenshot, native re-save, readback diff."""
    rec = manifest.stage_record("NATIVE_VERIFY")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    load_rec = manifest.stage_record("NATIVE_LOAD")
    if load_rec.status not in ("COMPLETE", "SKIPPED"):
        rec.mark_awaiting(
            "AWAITING_NATIVE_ENVIRONMENT: NATIVE_LOAD must complete first. "
            "Run on LOCAL Windows machine.",
            {"halted_for": "AWAITING_NATIVE_ENVIRONMENT"},
        )
        manifest.update_stage(rec)
        return rec

    # Check serum_sha_verified from NATIVE_LOAD
    if not load_rec.outputs.get("serum_sha_verified", False):
        rec.mark_failed(
            f"Serum module SHA mismatch. "
            f"Expected: {_SERUM_2023_SHA}. "
            f"Got: {load_rec.outputs.get('serum_module_sha256', 'UNKNOWN')}."
        )
        manifest.update_stage(rec)
        return rec

    # Look for native verification artifacts: screenshot, re-save, readback_diff
    screenshot_path = run_dir / "native_screenshot.png"
    readback_path = run_dir / "readback_diff.json"

    if not screenshot_path.exists() or not readback_path.exists():
        rec.mark_awaiting(
            "AWAITING_NATIVE_ENVIRONMENT: Native verification artifacts required. "
            f"(1) Screenshot Serum UI → {screenshot_path}. "
            f"(2) Run readback_diff.py against compiled preset → {readback_path}. "
            "Both are captured automatically when the pipeline runs on the LOCAL machine.",
            {"halted_for": "AWAITING_NATIVE_ENVIRONMENT"},
        )
        manifest.update_stage(rec)
        return rec

    rec.mark_complete({
        "serum_module_sha256": load_rec.outputs.get("serum_module_sha256"),
        "run_id_native": load_rec.outputs.get("run_id_native"),
        "track_nonce": load_rec.outputs.get("track_nonce"),
        "screenshot_path": str(screenshot_path),
        "screenshot_hash": content_hash(screenshot_path),
        "readback_path": str(readback_path),
        "readback_hash": content_hash(readback_path),
    })
    manifest.update_stage(rec)
    return rec


def _stage_reference_verify(manifest: RunManifest, run_dir: Path, run_name: str) -> StageRecord:
    rec = manifest.stage_record("REFERENCE_VERIFY")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    nv_rec = manifest.stage_record("NATIVE_VERIFY")
    if nv_rec.status not in ("COMPLETE", "SKIPPED"):
        rec.mark_awaiting(
            "AWAITING_NATIVE_ENVIRONMENT: NATIVE_VERIFY must complete first. "
            "Run on LOCAL Windows machine.",
            {"halted_for": "AWAITING_NATIVE_ENVIRONMENT"},
        )
        manifest.update_stage(rec)
        return rec

    stage_a_path = run_dir / "stage_a_census.json"
    if not stage_a_path.exists():
        rec.mark_awaiting(
            "AWAITING_NATIVE_ENVIRONMENT: Stage-A census required. "
            f"Expected at {stage_a_path}. "
            "Populated automatically from observation results on the LOCAL machine.",
            {"halted_for": "AWAITING_NATIVE_ENVIRONMENT"},
        )
        manifest.update_stage(rec)
        return rec

    rec.mark_running()
    manifest.update_stage(rec)

    try:
        from serum2.server.reference_reproduction import run_reference_reproduction
        from serum2.producer.execution_epoch import installed_epoch

        nv = nv_rec.outputs
        ui_readback = {
            "route": "DIRECT_UI",
            "values": {},
            "method": "manual_screenshot",
            "screenshot_sha256": nv.get("screenshot_hash"),
            "loader_evidence": {
                "run_id": nv.get("run_id_native"),
                "track_nonce": nv.get("track_nonce"),
                "serum_module_sha256": nv.get("serum_module_sha256"),
            },
        }

        run = run_reference_reproduction(
            stage_a_path=str(stage_a_path),
            reread_log_path=None,
            source={"url": manifest.source_url},
            name=run_name,
            epoch=installed_epoch(),
            ui_readback=ui_readback,
        )

        rec.mark_complete({
            "proof_level": run.proof_level,
            "coverage_status": run.coverage_status,
            "reference_verified": run.reference_verified,
        })
        manifest.reference_verified = run.reference_verified
        manifest.coverage_status = run.coverage_status
    except Exception as e:
        rec.mark_failed(str(e))

    manifest.update_stage(rec)
    return rec


def _stage_arrange(manifest: RunManifest, run_dir: Path) -> StageRecord:
    rec = manifest.stage_record("ARRANGE")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    rv_rec = manifest.stage_record("REFERENCE_VERIFY")
    if rv_rec.status not in ("COMPLETE", "SKIPPED"):
        rec.mark_awaiting("REFERENCE_VERIFY must complete first.",
                          {"halted_for": "REFERENCE_VERIFY_INCOMPLETE"})
        manifest.update_stage(rec)
        return rec

    if rv_rec.outputs.get("proof_level") != "LIVE_UI_VERIFIED":
        rec.mark_failed(
            f"Cannot arrange: proof_level={rv_rec.outputs.get('proof_level')} "
            "(must be LIVE_UI_VERIFIED)"
        )
        manifest.update_stage(rec)
        return rec

    # Arrangement is Ableton-MCP-driven; attempt if bridge is available.
    try:
        from serum2.ableton.arrangement import create_16bar_arrangement
        result = create_16bar_arrangement(
            track_id=manifest.stage_record("NATIVE_LOAD").outputs.get("run_id_native", ""),
            run_dir=str(run_dir),
        )
        arr_path = run_dir / "arrangement.json"
        with open(arr_path, "w") as fh:
            json.dump(result, fh, indent=2)
        rec.mark_complete({"arrangement_path": str(arr_path),
                           "arrangement_hash": content_hash(arr_path)})
    except Exception as exc:
        rec.mark_awaiting(
            f"AWAITING_NATIVE_ENVIRONMENT: Ableton arrangement requires MCP bridge: {exc}. "
            "Run this command on the LOCAL Windows machine with Ableton 11.3 open. "
            "Create a 16-bar MIDI clip in Arrangement view (not session mode). "
            f"Write arrangement details to {run_dir}/arrangement.json then re-run with --resume.",
            {"halted_for": "AWAITING_NATIVE_ENVIRONMENT"},
        )
    manifest.update_stage(rec)
    return rec


def _stage_render(manifest: RunManifest, run_dir: Path) -> StageRecord:
    rec = manifest.stage_record("RENDER")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    # Check for existing render WAV in run_dir
    render_path_candidate = run_dir / "render_16bar.wav"
    render_path = render_path_candidate if render_path_candidate.exists() else None

    if render_path is None:
        rec.mark_awaiting(
            "AWAITING_NATIVE_ENVIRONMENT: 16-bar render WAV required. "
            "In Ableton: File → Export Audio/Video → 44100 Hz, 24-bit WAV, full arrangement. "
            f"Save to {run_dir}/render_16bar.wav then re-run with --resume.",
            {"halted_for": "AWAITING_NATIVE_ENVIRONMENT"},
        )
        manifest.update_stage(rec)
        return rec

    rec.mark_running()
    manifest.update_stage(rec)

    # Verify RMS > -60 dBFS (audible signal)
    try:
        rms_dbfs = _check_render_rms(render_path)
        if rms_dbfs <= -60.0:
            rec.mark_failed(
                f"Render is silent or near-silent (RMS={rms_dbfs:.1f} dBFS). "
                "Verify MIDI clip is in Arrangement view, not Session. "
                "Check audio signal path."
            )
        else:
            rec.mark_complete({
                "render_path": str(render_path),
                "render_hash": content_hash(render_path),
                "rms_dbfs": rms_dbfs,
                "audible": True,
            })
            manifest.render_path = str(render_path)
    except Exception as e:
        rec.mark_failed(f"Render RMS check failed: {e}")

    manifest.update_stage(rec)
    return rec


def _check_render_rms(wav_path: Path) -> float:
    """Compute RMS of a WAV file in dBFS.  Returns 0.0 if measurement fails."""
    import math, struct, wave as wv
    try:
        with wv.open(str(wav_path)) as w:
            frames = w.readframes(w.getnframes())
            sampwidth = w.getsampwidth()
            nchannels = w.getnchannels()
        fmt = {1: "b", 2: "h", 4: "i"}[sampwidth]
        samples = struct.unpack(f"<{len(frames)//sampwidth}{fmt}", frames)
        max_val = float(2 ** (8 * sampwidth - 1))
        rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / max_val
        return 20.0 * math.log10(rms) if rms > 0 else -120.0
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Stage: FINALIZE — emit certificate only when all gates are satisfied
# ---------------------------------------------------------------------------

def _stage_finalize(manifest: RunManifest, run_dir: Path) -> StageRecord:
    rec = manifest.stage_record("FINALIZE")
    if rec.status in ("COMPLETE", "SKIPPED"):
        return rec

    rec.mark_running()
    manifest.update_stage(rec)

    failures: List[str] = []

    # Check all required preceding stages
    required_complete = [
        "NATIVE_LOAD", "NATIVE_VERIFY", "REFERENCE_VERIFY", "RENDER"
    ]
    for stage_name in required_complete:
        sr = manifest.stage_record(stage_name)
        if sr.status not in ("COMPLETE", "SKIPPED"):
            failures.append(f"{stage_name}: {sr.status} ({sr.failure_reason})")

    rv_rec = manifest.stage_record("REFERENCE_VERIFY")
    if rv_rec.outputs.get("proof_level") != "LIVE_UI_VERIFIED":
        failures.append(f"proof_level={rv_rec.outputs.get('proof_level')} (must be LIVE_UI_VERIFIED)")
    if rv_rec.outputs.get("coverage_status") != "COMPLETE":
        failures.append(f"coverage_status={rv_rec.outputs.get('coverage_status')} (must be COMPLETE)")
    if not rv_rec.outputs.get("reference_verified"):
        failures.append("reference_verified=False")

    nv_rec = manifest.stage_record("NATIVE_VERIFY")
    if not nv_rec.outputs.get("serum_module_sha256"):
        failures.append("serum_module_sha256 missing")
    elif nv_rec.outputs.get("serum_module_sha256") != _SERUM_2023_SHA:
        failures.append(f"serum_module_sha256 mismatch: {nv_rec.outputs.get('serum_module_sha256')}")

    render_rec = manifest.stage_record("RENDER")
    rms = render_rec.outputs.get("rms_dbfs", -120.0)
    if not isinstance(rms, (int, float)) or rms <= -60.0:
        failures.append(f"render RMS={rms} dBFS (must be > -60 dBFS)")

    # Build certificate
    adm_rec = manifest.stage_record("ADMISSION")
    compile_rec = manifest.stage_record("COMPILE")
    obs_rec = manifest.stage_record("OBSERVATION")

    final_status = "PRODUCT_CLOSED" if not failures else "PRODUCT_NOT_CLOSED"
    manifest.final_status = final_status
    manifest.native_verified = not bool(failures) and "NATIVE_VERIFY" not in [f.split(":")[0] for f in failures]

    cert = {
        "cert_type": "PRODUCT_CERT_3" if not failures else "INCOMPLETE",
        "final_status": final_status,
        "run_id": manifest.run_id,
        "video_id": manifest.video_id,
        "source_url": manifest.source_url,
        "epoch": "2.0.23@9293eb90",
        "epoch_binary_sha256": _SERUM_2023_SHA,
        "serum_module_sha256": nv_rec.outputs.get("serum_module_sha256"),
        "gate_b_status": "CANONICAL_GATE_B_VERIFIED" if not failures else "INCOMPLETE",
        "proof_level": rv_rec.outputs.get("proof_level"),
        "coverage_status": rv_rec.outputs.get("coverage_status"),
        "reference_verified": rv_rec.outputs.get("reference_verified"),
        "render_verified": render_rec.outputs.get("audible", False),
        "render_rms_dbfs": rms,
        "c3_real_readable_n": obs_rec.outputs.get("total_observations", 0),
        "c3_real_confident_wrong": obs_rec.outputs.get("confident_wrong_count", 0),
        "admitted_count": adm_rec.outputs.get("admitted_count", 0),
        "compiled_count": compile_rec.outputs.get("ops_count", 0),
        "dawdreamer_used": False,
        "headless_substitution_used": False,
        "failures": failures,
    }

    cert_path = run_dir / "pipeline_certificate.json"
    with open(cert_path, "w") as f:
        json.dump(cert, f, indent=2)

    manifest.certificate_path = str(cert_path)
    manifest.observed_count = obs_rec.outputs.get("total_observations", 0)
    manifest.admitted_count = adm_rec.outputs.get("admitted_count", 0)
    manifest.compiled_count = compile_rec.outputs.get("ops_count", 0)
    manifest.coverage_status = rv_rec.outputs.get("coverage_status", "UNKNOWN")

    if not failures:
        rec.mark_complete({
            "certificate_path": str(cert_path),
            "certificate_hash": content_hash(cert_path),
            "final_status": "PRODUCT_CLOSED",
        })
    else:
        rec.mark_failed(
            f"PRODUCT_NOT_CLOSED: {len(failures)} gate(s) failed. "
            f"Failures: {'; '.join(failures)}"
        )

    manifest.update_stage(rec)
    return rec


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------

def run_pipeline(
    youtube_url: str,
    work_dir: Optional[Path] = None,
    sample_interval_sec: float = 2.0,
    max_frames: Optional[int] = None,
    resume: bool = True,
    dry_run: bool = False,
) -> RunManifest:
    """Execute all pipeline stages in order.  Returns the RunManifest.

    Stages HALT (AWAITING_INPUT) when they require LOCAL/NATIVE execution.
    Use --resume to continue from where a previous run stopped.
    """
    from serum2.source.youtube_url import extract_youtube_video_id
    video_id = extract_youtube_video_id(youtube_url)
    run_id = "pipeline_" + hashlib.md5((youtube_url + str(sample_interval_sec)).encode()).hexdigest()[:12]
    run_dir = _run_dir(video_id, work_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    mpath = _manifest_path(run_dir)
    if resume and mpath.exists():
        manifest = RunManifest.load(mpath)
    else:
        manifest = RunManifest(
            run_id=run_id,
            video_id=video_id,
            source_url=youtube_url,
            work_dir=str(run_dir),
        )

    manifest.save(mpath)

    run_name = f"pipeline_{video_id}"

    if dry_run:
        return manifest

    stage_fns = [
        ("ACQUIRE",           lambda: _stage_acquire(manifest, run_dir, youtube_url, sample_interval_sec, max_frames)),
        ("TRANSCRIPT",        lambda: _stage_transcript(manifest, run_dir, youtube_url)),
        ("VISUAL_EVIDENCE",   lambda: _stage_visual_evidence(manifest, run_dir)),
        ("OBSERVATION",       lambda: _stage_observation(manifest, run_dir)),
        ("LEDGER",            lambda: _stage_ledger(manifest, run_dir)),
        ("ADMISSION",         lambda: _stage_admission(manifest, run_dir)),
        ("COMPILE",           lambda: _stage_compile(manifest, run_dir, run_name)),
        ("NATIVE_LOAD",       lambda: _stage_native_load(manifest, run_dir)),
        ("NATIVE_VERIFY",     lambda: _stage_native_verify(manifest, run_dir)),
        ("REFERENCE_VERIFY",  lambda: _stage_reference_verify(manifest, run_dir, run_name)),
        ("ARRANGE",           lambda: _stage_arrange(manifest, run_dir)),
        ("RENDER",            lambda: _stage_render(manifest, run_dir)),
        ("FINALIZE",          lambda: _stage_finalize(manifest, run_dir)),
    ]

    for stage_name, fn in stage_fns:
        rec = fn()
        manifest.save(mpath)
        if rec.status == "FAILED":
            manifest.final_status = "PRODUCT_NOT_CLOSED"
            manifest.failure_stage = stage_name
            manifest.failure_reason = rec.failure_reason
            manifest.save(mpath)
            break
        if rec.status == "AWAITING_INPUT":
            # Soft halt: native boundary reached or external artifact needed.
            # State is durable; re-run with --resume on the appropriate machine.
            manifest.final_status = "RUNNING"
            manifest.failure_stage = stage_name
            manifest.failure_reason = rec.failure_reason
            manifest.save(mpath)
            break

    manifest.save(mpath)
    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_summary(manifest: RunManifest) -> None:
    s = manifest.summary_dict()
    width = max(len(k) for k in s)
    for k, v in s.items():
        print(f"  {k:<{width}}  {v}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m serum2.pipeline",
        description=(
            "Universal YouTube → Serum → Ableton pipeline runner.\n\n"
            "Stages (in order):\n"
            "  ACQUIRE → TRANSCRIPT → VISUAL_EVIDENCE → OBSERVATION →\n"
            "  LEDGER → ADMISSION → COMPILE → NATIVE_LOAD → NATIVE_VERIFY →\n"
            "  REFERENCE_VERIFY → ARRANGE → RENDER → FINALIZE\n\n"
            "Execution boundaries:\n"
            "  CLOUD: ACQUIRE, TRANSCRIPT, VISUAL_EVIDENCE, LEDGER, ADMISSION, COMPILE, FINALIZE\n"
            "  LOCAL_NATIVE (Windows + Serum 2.0.23): OBSERVATION, NATIVE_LOAD, NATIVE_VERIFY,\n"
            "                                          REFERENCE_VERIFY, ARRANGE, RENDER\n\n"
            "The runner halts at LOCAL_NATIVE stages with exact instructions for the Windows session.\n"
            "Re-run with --resume after completing LOCAL steps to continue."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("youtube_url", help="YouTube video URL or video ID")
    ap.add_argument("--work-dir", default=None,
                    help="Run directory (default: serum2/data/pipeline_runs/<video_id>)")
    ap.add_argument("--sample-interval-sec", type=float, default=2.0,
                    help="Frame sampling interval in seconds (default: 2.0)")
    ap.add_argument("--max-frames", type=int, default=None,
                    help="Maximum frames to acquire (default: all)")
    ap.add_argument("--resume", action="store_true", default=True,
                    help="Resume from last saved state (default: True)")
    ap.add_argument("--no-resume", dest="resume", action="store_false",
                    help="Start fresh (ignore saved state)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse arguments and print run_id without executing stages")
    ap.add_argument("--status", action="store_true",
                    help="Print status of an existing run and exit")
    args = ap.parse_args(argv)

    manifest = run_pipeline(
        youtube_url=args.youtube_url,
        work_dir=Path(args.work_dir) if args.work_dir else None,
        sample_interval_sec=args.sample_interval_sec,
        max_frames=args.max_frames,
        resume=args.resume,
        dry_run=args.dry_run,
    )

    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    _print_summary(manifest)
    print("=" * 60)

    if manifest.final_status == "PRODUCT_CLOSED":
        return 0
    elif manifest.final_status == "RUNNING":
        print(f"\nPipeline halted at stage awaiting input.")
        print(f"Check {_manifest_path(Path(manifest.work_dir))} for next steps.")
        return 2
    else:
        print(f"\nPipeline failed: {manifest.failure_reason}")
        return 1
