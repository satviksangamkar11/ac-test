"""Durable stage manifest for the universal pipeline runner.

Each stage records: status, run_id, inputs, outputs, hashes, timestamps,
failure reason, and execution boundary (CLOUD vs LOCAL_NATIVE).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ordered stage sequence — must not be reordered without updating all callers.
STAGE_SEQUENCE: List[str] = [
    "ACQUIRE",
    "TRANSCRIPT",
    "VISUAL_EVIDENCE",
    "OBSERVATION",
    "LEDGER",
    "ADMISSION",
    "COMPILE",
    "NATIVE_LOAD",
    "NATIVE_VERIFY",
    "REFERENCE_VERIFY",
    "ARRANGE",
    "RENDER",
    "FINALIZE",
]

# CLOUD: can run without Serum/Ableton.
# LOCAL_NATIVE: requires Windows + real Serum 2.0.23 + real Ableton.
# ANY: either boundary is fine; typically runs wherever the pipeline runs.
STAGE_BOUNDARY: Dict[str, str] = {
    "ACQUIRE":          "ANY",
    "TRANSCRIPT":       "ANY",
    "VISUAL_EVIDENCE":  "ANY",
    "OBSERVATION":      "LOCAL_NATIVE",   # requires local VLM (Qwen2.5-VL)
    "LEDGER":           "ANY",
    "ADMISSION":        "ANY",
    "COMPILE":          "ANY",
    "NATIVE_LOAD":      "LOCAL_NATIVE",
    "NATIVE_VERIFY":    "LOCAL_NATIVE",
    "REFERENCE_VERIFY": "LOCAL_NATIVE",
    "ARRANGE":          "LOCAL_NATIVE",
    "RENDER":           "LOCAL_NATIVE",
    "FINALIZE":         "ANY",
}

# Stages that cannot claim LIVE_UI_VERIFIED.  All CLOUD stages produce
# PREPARED_ARTIFACT level; only LOCAL_NATIVE stages produce native proof.
CLOUD_STAGES = {k for k, v in STAGE_BOUNDARY.items() if v == "ANY"}
NATIVE_STAGES = {k for k, v in STAGE_BOUNDARY.items() if v == "LOCAL_NATIVE"}


# ---------------------------------------------------------------------------
# Stage record
# ---------------------------------------------------------------------------

@dataclass
class StageRecord:
    stage: str
    status: str = "PENDING"            # PENDING | RUNNING | COMPLETE | FAILED | AWAITING_INPUT | SKIPPED
    run_id: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    execution_boundary: str = "ANY"
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None
    cache_key: Optional[str] = None    # hex digest; if outputs match, stage is SKIPPED

    def mark_running(self) -> None:
        self.status = "RUNNING"
        self.started_at = _utcnow()

    def mark_complete(self, outputs: Dict[str, Any]) -> None:
        self.status = "COMPLETE"
        self.outputs = outputs
        self.finished_at = _utcnow()

    def mark_failed(self, reason: str) -> None:
        self.status = "FAILED"
        self.failure_reason = reason
        self.finished_at = _utcnow()

    def mark_awaiting(self, reason: str, outputs_so_far: Dict[str, Any] = None) -> None:
        self.status = "AWAITING_INPUT"
        self.failure_reason = reason
        self.outputs = outputs_so_far or {}
        self.finished_at = _utcnow()

    def mark_skipped(self, reason: str = "cache hit") -> None:
        self.status = "SKIPPED"
        self.failure_reason = reason
        self.finished_at = _utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StageRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Run manifest (the durable file on disk)
# ---------------------------------------------------------------------------

@dataclass
class RunManifest:
    run_id: str
    video_id: str
    source_url: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    work_dir: str = ""
    stages: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    final_status: str = "RUNNING"   # RUNNING | PRODUCT_CLOSED | PRODUCT_NOT_CLOSED
    failure_stage: Optional[str] = None
    failure_reason: Optional[str] = None

    # Summary fields (filled by FINALIZE)
    observed_count: int = 0
    admitted_count: int = 0
    compiled_count: int = 0
    native_verified: bool = False
    reference_verified: bool = False
    coverage_status: str = "UNKNOWN"
    render_path: Optional[str] = None
    certificate_path: Optional[str] = None

    def stage_record(self, stage_name: str) -> StageRecord:
        if stage_name not in self.stages:
            self.stages[stage_name] = StageRecord(
                stage=stage_name,
                run_id=self.run_id,
                execution_boundary=STAGE_BOUNDARY.get(stage_name, "ANY"),
            ).to_dict()
        return StageRecord.from_dict(self.stages[stage_name])

    def update_stage(self, record: StageRecord) -> None:
        self.stages[record.stage] = record.to_dict()
        self.updated_at = _utcnow()

    def save(self, manifest_path: Path) -> None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, manifest_path: Path) -> "RunManifest":
        with open(manifest_path) as f:
            d = json.load(f)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def is_stage_complete(self, stage_name: str) -> bool:
        rec = self.stage_record(stage_name)
        return rec.status in ("COMPLETE", "SKIPPED")

    def current_stage(self) -> Optional[str]:
        """Return the first stage that is not COMPLETE or SKIPPED."""
        for s in STAGE_SEQUENCE:
            if not self.is_stage_complete(s):
                return s
        return None

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "RUN_ID": self.run_id,
            "VIDEO_ID": self.video_id,
            "OBSERVED_COUNT": self.observed_count,
            "ADMITTED_COUNT": self.admitted_count,
            "COMPILED_COUNT": self.compiled_count,
            "NATIVE_VERIFIED": self.native_verified,
            "REFERENCE_VERIFIED": self.reference_verified,
            "COVERAGE_STATUS": self.coverage_status,
            "RENDER_PATH": self.render_path,
            "CERTIFICATE_PATH": self.certificate_path,
            "FINAL_STATUS": self.final_status,
        }


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def content_hash(path: Path) -> Optional[str]:
    """SHA-256 of a file, or None if missing."""
    if not path.exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def dict_hash(d: Dict[str, Any]) -> str:
    """Deterministic SHA-256 of a dict (sorted keys, JSON-serialised)."""
    return hashlib.sha256(
        json.dumps(d, sort_keys=True, default=str).encode()
    ).hexdigest()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


