"""Production run state machine.

ProductionState tracks which stage the pipeline is at.
ProductionRun is the persisted record for one produce_from_youtube() call.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

RUNS_DIR = Path(__file__).parent.parent / "data" / "episodes"


class ProductionState(Enum):
    # Auto-advancing (pure Python)
    RECEIVED         = "RECEIVED"
    TRANSCRIBED      = "TRANSCRIBED"
    KNOWLEDGE_BUILT  = "KNOWLEDGE_BUILT"
    INTENT_CREATED   = "INTENT_CREATED"
    ADMITTED         = "ADMITTED"
    # Agent-driven (requires Claude tool calls + advance_production())
    PRESET_GENERATED     = "PRESET_GENERATED"
    SERUM_UI_CONFIGURED  = "SERUM_UI_CONFIGURED"
    SERUM_VERIFIED       = "SERUM_VERIFIED"
    ABLETON_CONFIGURED   = "ABLETON_CONFIGURED"
    # Reserved, intentionally not part of the enforced sequence in
    # production_pipeline._EXPECTED_PREDECESSOR: track/clip/MIDI/arrangement
    # are batched into ONE ABLETON_CONFIGURED transition per AbletonMCP's own
    # guidance ("use batch_commands ... one round-trip, one undo step").
    # Splitting these out would mean 3 separate Claude tool round-trips for
    # what is correctly one atomic Ableton edit.
    MIDI_CREATED         = "MIDI_CREATED"
    ARRANGEMENT_VERIFIED = "ARRANGEMENT_VERIFIED"
    RENDERED             = "RENDERED"
    # Auto-advancing
    MEASURED             = "MEASURED"
    EVIDENCE_FINALIZED   = "EVIDENCE_FINALIZED"
    COMPLETED            = "COMPLETED"
    # Terminal failure
    FAILED               = "FAILED"


@dataclass
class ProductionRun:
    run_id: str
    youtube_url: str
    state: str = ProductionState.RECEIVED.value
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Stage artifacts (auto stages)
    source_id: Optional[str] = None
    transcript_snippet: Optional[str] = None
    knowledge_record_count: int = 0
    intent: Optional[Dict[str, Any]] = None
    admission: Optional[Dict[str, Any]] = None

    # Agent-driven evidence
    preset_path: Optional[str] = None
    preset_sha256: Optional[str] = None
    serum_ui_evidence: Optional[Dict[str, Any]] = None
    ableton_evidence: Optional[Dict[str, Any]] = None
    render_path: Optional[str] = None
    measurements: Optional[Dict[str, Any]] = None

    # Final
    episode_id: Optional[str] = None
    error: Optional[str] = None
    next_action: Optional[Dict[str, Any]] = None

    def advance(self, new_state: ProductionState, **updates) -> None:
        self.state = new_state.value
        self.updated_at = datetime.now(timezone.utc).isoformat()
        for k, v in updates.items():
            setattr(self, k, v)

    def fail(self, error: str) -> None:
        self.state = ProductionState.FAILED.value
        self.error = error
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.next_action = None

    def save(self) -> None:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        (RUNS_DIR / f"{self.run_id}.json").write_text(
            json.dumps(asdict(self), indent=2)
        )

    @classmethod
    def load(cls, run_id: str) -> ProductionRun:
        p = RUNS_DIR / f"{run_id}.json"
        if not p.exists():
            raise FileNotFoundError(f"No production run: {run_id}")
        return cls(**json.loads(p.read_text()))

    @classmethod
    def load_all(cls) -> List[ProductionRun]:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        runs = []
        for p in sorted(RUNS_DIR.glob("prod_*.json"), reverse=True):
            try:
                runs.append(cls(**json.loads(p.read_text())))
            except Exception:
                pass
        return runs
