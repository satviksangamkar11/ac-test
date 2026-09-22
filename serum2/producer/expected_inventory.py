"""Phase 3.2: Expected Inventory System

Hybrid approach: Atlas defines legal universe, reference episode context determines
what subset is actually expected. Keeps visibility separate from expectation.

Three distinct sets:
  1. ATLAS_UNIVERSE: all valid Serum 2.0.21 controls
  2. EPISODE_EXPECTED_SET: controls relevant to this tutorial/reference
  3. TERMINAL_OBSERVATION_SET: what evidence pipeline accounted for

Invariant: EPISODE_EXPECTED_SET == TERMINAL_OBSERVATION_SET
(every expected item must have an explicit terminal outcome)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import json


class ObservationOutcome(Enum):
    """Terminal evidence outcomes — all explicit, no silent drops."""
    OBSERVED = "OBSERVED"
    OBSERVED_BUT_UNVERIFIED = "OBSERVED_BUT_UNVERIFIED"
    SOURCE_INSUFFICIENT = "SOURCE_INSUFFICIENT"
    NOT_VISIBLE_IN_FRAME = "NOT_VISIBLE_IN_FRAME"
    OCCLUDED = "OCCLUDED"
    BLURRED = "BLURRED"
    TOOLTIP_MISSING = "TOOLTIP_MISSING"
    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNSUPPORTED_MODALITY = "UNSUPPORTED_MODALITY"
    VALIDATION_REJECTED = "VALIDATION_REJECTED"


@dataclass
class ExpectedObservation:
    """An observation obligation in the expected inventory.

    What should have been observed, why, and what kind of evidence is needed.
    Visibility is NOT part of expectation — an unreadable control is still expected.
    """
    canonical_id: str
    observation_kind: str  # TEXT, ENUM, NUMERIC, ENABLE_STATE, ROUTE, GRAPH_DERIVED, MATRIX_AMOUNT, etc.
    strategy: str  # which ObservationEngine strategy should handle it

    # Why this control is expected
    expectation_basis: Dict[str, str] = field(default_factory=dict)
    # e.g., {
    #   "transcript": "Setting Drive to 1.9",
    #   "procedure": "Overdrive configuration step 5",
    #   "module_context": "FX chain / Distortion",
    #   "reference_surface": "main FX area"
    # }

    # Conditions for observation
    applicability: bool = True  # is this control relevant in this context?
    visibility_requirement: str = "VISIBLE"  # VISIBLE, OPTIONAL, CONTEXTUAL
    evidence_requirement: str = "PREFERRED"  # REQUIRED, PREFERRED, OPTIONAL

    epoch: str = "phase-3-canonical"
    inventory_fingerprint: str = ""  # hash of inventory version

    def to_dict(self) -> Dict:
        return {
            "canonical_id": self.canonical_id,
            "observation_kind": self.observation_kind,
            "strategy": self.strategy,
            "expectation_basis": self.expectation_basis,
            "applicability": self.applicability,
            "visibility_requirement": self.visibility_requirement,
            "evidence_requirement": self.evidence_requirement,
            "epoch": self.epoch,
        }


@dataclass
class TerminalObservation:
    """What actually happened with an expected observation.

    Separates what was expected from what evidence could prove.
    """
    canonical_id: str
    outcome: ObservationOutcome

    # What the pipeline extracted (if anything)
    candidate: Optional[dict] = None  # ObservationCandidate as dict

    # Evidence quality
    evidence_hash: Optional[str] = None
    observation_status: str = "UNKNOWN"  # OBSERVED, UNOBSERVED, etc.
    evidence_status: str = "UNKNOWN"  # SUFFICIENT, INSUFFICIENT, etc.
    proof_level: str = "NOT_VERIFIED"  # NOT_VERIFIED, VERIFIED, LIVE_UI_VERIFIED

    # Provenance
    provenance: Dict[str, str] = field(default_factory=dict)
    # e.g., {
    #   "source_image": "step5_07m04s_main_delay_ping_pong.jpg",
    #   "roi_bbox": "...",
    #   "qwen_raw_output": "DRIVE=1.9",
    #   "ground_truth": "1.9",
    #   "note": "source too small to independently verify"
    # }

    def to_dict(self) -> Dict:
        return {
            "canonical_id": self.canonical_id,
            "outcome": self.outcome.value,
            "candidate": self.candidate,
            "evidence_hash": self.evidence_hash,
            "observation_status": self.observation_status,
            "evidence_status": self.evidence_status,
            "proof_level": self.proof_level,
            "provenance": self.provenance,
        }


class EpisodeContextResolver:
    """Determines what controls should be expected from reference episode context.

    Uses transcript/procedure/module context to expand Atlas subset, ensuring
    visibility gaps don't create false completeness claims.
    """

    def __init__(self, reference_id: str, atlas: Dict):
        self.reference_id = reference_id
        self.atlas = atlas  # full Atlas/UI Atlas
        self.expected_modules = set()
        self.expected_controls = set()

    def add_module_context(self, module_name: str, frame_context: str):
        """Record that a module appeared in the tutorial.

        Args:
            module_name: e.g., "OSC_A", "FILTER_1", "MATRIX", "FX_OVERDRIVE"
            frame_context: e.g., "visible in step1_01m09s", "referenced in transcript"
        """
        self.expected_modules.add(module_name)

    def add_control_context(self, canonical_id: str, basis: Dict[str, str]):
        """Record that a control is expected based on reference context.

        Args:
            canonical_id: e.g., "oscA.unison", "fx.overdrive.drive"
            basis: dict with transcript, procedure, module_context, reference_surface
        """
        self.expected_controls.add((canonical_id, json.dumps(basis, sort_keys=True)))

    def get_expected_set(self) -> Set[str]:
        """Return all expected canonical_ids for this episode."""
        return {cid for cid, _ in self.expected_controls}

    def get_expectation_basis(self, canonical_id: str) -> Optional[Dict[str, str]]:
        """Retrieve why a control is expected."""
        for cid, basis_json in self.expected_controls:
            if cid == canonical_id:
                return json.loads(basis_json)
        return None


class ExpectedInventoryBuilder:
    """Builds immutable ExpectedInventory from Atlas + episode context.

    Does NOT reduce inventory based on visible frames.
    Visibility gaps become SOURCE_INSUFFICIENT/NOT_VISIBLE outcomes, not missing expectations.
    """

    def __init__(self, atlas: Dict, episode_context: EpisodeContextResolver):
        self.atlas = atlas
        self.context = episode_context
        self.inventory: Dict[str, ExpectedObservation] = {}

    def build(self) -> Dict[str, ExpectedObservation]:
        """Build complete expected inventory.

        Returns inventory keyed by canonical_id.
        Includes all controls expected from episode context, even if unreadable.
        """
        expected_ids = self.context.get_expected_set()

        for canonical_id in expected_ids:
            basis = self.context.get_expectation_basis(canonical_id)
            if not basis:
                basis = {"note": "inferred from episode context"}

            # Look up control in Atlas to get observation_kind, strategy
            obs_kind, strategy = self._resolve_observation_type(canonical_id)

            observation = ExpectedObservation(
                canonical_id=canonical_id,
                observation_kind=obs_kind,
                strategy=strategy,
                expectation_basis=basis,
                applicability=True,
                visibility_requirement="VISIBLE",
                evidence_requirement="PREFERRED",
            )
            self.inventory[canonical_id] = observation

        return self.inventory

    def _resolve_observation_type(self, canonical_id: str) -> tuple:
        """Look up observation kind and strategy for a control ID.

        Returns: (observation_kind, strategy)
        """
        # Simplified lookup; real implementation would query Atlas
        if "drive" in canonical_id.lower():
            return ("NUMERIC", "NUMERIC")
        elif "mode" in canonical_id.lower() or "shape" in canonical_id.lower():
            return ("ENUM", "ENUM")
        elif "legato" in canonical_id.lower() or "mono" in canonical_id.lower():
            return ("ENABLE_STATE", "ENABLE_STATE")
        elif "unison" in canonical_id.lower():
            return ("NUMERIC", "NUMERIC")
        elif "route:" in canonical_id.lower():
            return ("ROUTE", "ROUTE_TEXT")
        elif "amount" in canonical_id.lower() and "matrix" in canonical_id.lower():
            return ("MATRIX_AMOUNT", "SLIDER_PIXEL")
        else:
            return ("UNKNOWN", "TEXT")


class CompletenessValidator:
    """Validates the completeness invariant.

    Ensures: EPISODE_EXPECTED_SET == TERMINAL_OBSERVATION_SET
    """

    def __init__(self, expected_inventory: Dict[str, ExpectedObservation]):
        self.expected_ids = set(expected_inventory.keys())
        self.terminal_ids = set()
        self.validation_report = {}

    def add_terminal_observation(self, terminal_obs: TerminalObservation):
        """Record a terminal observation outcome."""
        self.terminal_ids.add(terminal_obs.canonical_id)

    def validate(self) -> Dict:
        """Check completeness invariant.

        Returns:
            {
                "valid": bool,
                "missing": list of expected_ids not in terminal_ids,
                "extra": list of terminal_ids not in expected_ids,
                "report": {expected_id: status for all expected_ids}
            }
        """
        missing = self.expected_ids - self.terminal_ids
        extra = self.terminal_ids - self.expected_ids

        report = {}
        for eid in self.expected_ids:
            report[eid] = {
                "expected": True,
                "observed": eid in self.terminal_ids,
            }

        for tid in extra:
            report[tid] = {
                "expected": False,
                "observed": True,
            }

        return {
            "valid": len(missing) == 0 and len(extra) == 0,
            "missing": sorted(missing),
            "extra": sorted(extra),
            "report": report,
        }
