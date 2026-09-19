"""B1.1 + B1.2: Canonical Representation and Derivation Engine.

Transform concept construction from hand-written tables to data-driven derivation
from Atlas, contracts, and generic language, per BRAIN_B1_PLAN.md.

Architecture principle: All concepts are derived from frozen data layers.
Never invent a concept. Return "derived" or "missing" with audit trail.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from serum2.reference.serum_atlas import normalize_control, get_control, Resolution
from serum2.producer.contract_registry import ContractRegistry, Contract
from serum2.compiler.targets import SEMANTIC_TARGETS
from serum2.compiler.mcp_intent import MCP_HOST_MAP


class Provenance(Enum):
    """Where a concept representation came from."""
    CONTRACT = "contract"           # CAUSAL_VERIFIED contract exists
    LEGACY_SEMANTIC_TARGET = "legacy_semantic_target"  # existing Brain semantic mapping
    MCP_HOST_MAP = "mcp_host_map"  # MCP-backed concept
    GENERIC_LANGUAGE = "generic_language"  # derivable from English direction words
    MISSING = "missing"             # no derivation path found


@dataclass
class ValueDomain:
    """Describes the valid values for a concept."""
    type: str                       # "numeric", "enum", "toggle", "range", "time", "frequency"
    unit: Optional[str] = None
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    enum_values: Optional[List[str]] = None
    description: str = ""


@dataclass
class ConceptRepresentation:
    """Unified representation of a production concept.

    Replaces scattered hand-written tables with a single, auditable structure.
    All data fields are derivable from frozen layers (Atlas, contracts, generic language).
    """

    canonical_target: str           # e.g., "env1.decay", "filter1.cutoff"

    # Data source references
    atlas_entry: Optional[Any] = None  # AtlasControl (if resolved)
    capability_contract: Optional[Contract] = None  # if CAUSAL_VERIFIED exists
    semantic_target_name: Optional[str] = None  # Brain-side target name from SEMANTIC_TARGETS

    # Semantic properties
    operation_type: str = "unknown"  # "numeric", "enum", "toggle", "range", "time", "frequency"
    value_domain: Optional[ValueDomain] = None
    generic_language_keywords: List[str] = field(default_factory=list)  # ["shorter", "longer", etc.]

    # Authority and confidence
    provenance: Provenance = Provenance.MISSING
    confidence: float = 0.0         # 0.0–1.0; reflects data quality

    # Audit trail
    derivation_chain: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate that representation is coherent."""
        if self.provenance == Provenance.MISSING:
            if self.capability_contract or self.semantic_target_name:
                raise ValueError(f"Missing provenance but contract or target exists for {self.canonical_target}")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"Confidence must be 0.0–1.0, got {self.confidence}")

    def is_derivable(self) -> bool:
        """Can this concept be used for reasoning?"""
        return self.provenance != Provenance.MISSING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/audit."""
        return {
            "canonical_target": self.canonical_target,
            "operation_type": self.operation_type,
            "provenance": self.provenance.value,
            "confidence": self.confidence,
            "derivation_chain": self.derivation_chain,
            "value_domain": self.value_domain.__dict__ if self.value_domain else None,
        }


class ConceptDerivationEngine:
    """B1.2: Derive concepts from frozen data layers without hand-written tables.

    Query order (first match wins):
    1. Capability contract (CAUSAL_VERIFIED)
    2. Existing semantic target mapping (Brain vocabulary)
    3. MCP host map
    4. Generic language patterns
    5. Return "missing" with explanation
    """

    def __init__(
        self,
        contract_registry: ContractRegistry,
        semantic_targets: Optional[Dict[str, Any]] = None,
        mcp_host_map: Optional[Dict[str, Any]] = None,
        generic_keywords: Optional[Dict[str, List[str]]] = None,
    ):
        self._contracts = contract_registry
        self._targets = semantic_targets or SEMANTIC_TARGETS
        self._mcp_map = mcp_host_map or MCP_HOST_MAP

        # Generic language patterns (frozen; do NOT extend here)
        self._generic_keywords = generic_keywords or {
            "decrease": ["off", "less", "lower", "down", "reduce", "decrease", "shorter", "shorten",
                        "quieter", "smaller", "tighter"],
            "increase": ["more", "up", "raise", "increase", "longer", "louder", "higher", "bigger",
                        "larger", "extend", "boost"],
            "toggle": ["on", "off", "enable", "disable"],
        }

    def derive(self, canonical_target: str, context: Optional[Dict[str, Any]] = None) -> ConceptRepresentation:
        """Derive a concept representation from frozen data layers.

        Args:
            canonical_target: Atlas-canonical control ID (e.g., "env1.decay")
            context: optional context (used for generic language interpretation)

        Returns:
            ConceptRepresentation with provenance and audit trail
        """
        chain = [f"derive({canonical_target})"]

        # Step 1: Resolve Atlas entry
        atlas_r = normalize_control(canonical_target)
        if atlas_r.status not in ("EXACT", "ALIAS"):
            chain.append(f"atlas.resolve: {atlas_r.status}")
            return ConceptRepresentation(
                canonical_target=canonical_target,
                provenance=Provenance.MISSING,
                confidence=0.0,
                derivation_chain=chain + ["UNRESOLVED_REFERENCE"],
            )

        canonical_id = atlas_r.canonical_id
        chain.append(f"atlas.resolve: {atlas_r.status} → {canonical_id}")

        # Step 2: Try to find a contract
        contract, contract_key = self._find_contract(canonical_id)
        if contract and contract.usable_for(required_causal=True):
            chain.append(f"contract_registry: found CAUSAL_VERIFIED {contract_key}")
            rep = ConceptRepresentation(
                canonical_target=canonical_id,
                atlas_entry=normalize_control(canonical_id),
                capability_contract=contract,
                operation_type=self._operation_type_from_contract(contract),
                value_domain=self._value_domain_from_contract(contract),
                semantic_target_name=self._semantic_target_for_canonical(canonical_id),
                provenance=Provenance.CONTRACT,
                confidence=0.95,
                derivation_chain=chain,
            )
            rep.generic_language_keywords = self._generic_keywords_for_operation(rep.operation_type)
            return rep

        # Step 3: Check existing semantic targets
        semantic_target = self._semantic_target_for_canonical(canonical_id)
        if semantic_target and semantic_target in self._targets:
            chain.append(f"semantic_targets: found {semantic_target}")
            rep = ConceptRepresentation(
                canonical_target=canonical_id,
                atlas_entry=normalize_control(canonical_id),
                semantic_target_name=semantic_target,
                operation_type="numeric",  # default; may be overridden
                provenance=Provenance.LEGACY_SEMANTIC_TARGET,
                confidence=0.85,
                derivation_chain=chain,
            )
            rep.generic_language_keywords = self._generic_keywords_for_operation(rep.operation_type)
            return rep

        # Step 4: Check MCP host map
        if canonical_id in self._mcp_map:
            chain.append(f"mcp_host_map: found {canonical_id}")
            rep = ConceptRepresentation(
                canonical_target=canonical_id,
                atlas_entry=normalize_control(canonical_id),
                operation_type="toggle",  # most MCP operations are toggles/setters
                provenance=Provenance.MCP_HOST_MAP,
                confidence=0.80,
                derivation_chain=chain,
            )
            rep.generic_language_keywords = self._generic_keywords_for_operation(rep.operation_type)
            return rep

        # Step 5: Try generic language (for controls that don't need contracts)
        generic_path = self._try_generic_language(canonical_id, context)
        if generic_path:
            chain.append(f"generic_language: {generic_path}")
            rep = ConceptRepresentation(
                canonical_target=canonical_id,
                atlas_entry=normalize_control(canonical_id),
                operation_type="numeric",
                provenance=Provenance.GENERIC_LANGUAGE,
                confidence=0.60,
                derivation_chain=chain,
            )
            rep.generic_language_keywords = self._generic_keywords["increase"] + self._generic_keywords["decrease"]
            return rep

        # No derivation path
        chain.append("NO_DERIVATION_PATH")
        return ConceptRepresentation(
            canonical_target=canonical_id,
            atlas_entry=normalize_control(canonical_id),
            provenance=Provenance.MISSING,
            confidence=0.0,
            derivation_chain=chain,
        )

    # ---- Helpers ----

    def _find_contract(self, canonical_target: str) -> Tuple[Optional[Contract], Optional[str]]:
        """Find a CAUSAL_VERIFIED contract for this target."""
        # Try to infer contract key from canonical target
        # e.g., "env1.decay" → "envelope_field_decay"
        normalized = canonical_target.lower().replace(".", "_")

        # Known mappings (frozen set, not extensible)
        contract_hints = {
            "env1_decay": "envelope_field_decay",
            "env1_sustain": "envelope_field_sustain",
            "env1_attack": "envelope_field_attack",
            "env1_hold": "envelope_field_hold",
            "env1_release": "envelope_field_release",
            "env2_decay": "envelope_field_decay",
            "env2_sustain": "envelope_field_sustain",
            "env3_decay": "envelope_field_decay",
            "env3_sustain": "envelope_field_sustain",
            "env4_decay": "envelope_field_decay",
            "env4_sustain": "envelope_field_sustain",
            "filter1_type": "filter_field_type",
            "filter1_cutoff": "filter_field_cutoff",
            "filter1_resonance": "filter_field_resonance",
            "lfo1_rate": "lfo_field_rate",
            "lfo1_smooth": "lfo_field_smooth",
        }

        key = contract_hints.get(normalized)
        if key:
            contract = self._contracts.contracts.get(key)
            if contract and contract.usable_for(required_causal=True):
                return contract, key

        return None, None

    def _semantic_target_for_canonical(self, canonical_target: str) -> Optional[str]:
        """Find a Brain-side semantic target name for this canonical control."""
        # Index by normalized name
        norm = canonical_target.lower().replace(".", "_")
        for target_name in self._targets:
            if target_name.lower().replace(".", "_") == norm:
                return target_name
        return None

    def _operation_type_from_contract(self, contract: Contract) -> str:
        """Infer operation type from contract."""
        # Check contract metadata for operation hints
        if hasattr(contract, "operation_type"):
            return contract.operation_type
        if hasattr(contract, "enum_values") and contract.enum_values:
            return "enum"
        return "numeric"

    def _value_domain_from_contract(self, contract: Contract) -> Optional[ValueDomain]:
        """Extract value domain from contract."""
        if not contract:
            return None

        domain_type = "numeric"
        unit = None
        min_val = None
        max_val = None
        enum_vals = None

        if hasattr(contract, "enum_values") and contract.enum_values:
            domain_type = "enum"
            enum_vals = contract.enum_values
        elif hasattr(contract, "value_type"):
            if "time" in contract.value_type.lower():
                domain_type = "time"
                unit = "ms"
            elif "frequency" in contract.value_type.lower():
                domain_type = "frequency"
                unit = "hz"

        if hasattr(contract, "min_value"):
            min_val = contract.min_value
        if hasattr(contract, "max_value"):
            max_val = contract.max_value

        return ValueDomain(
            type=domain_type,
            unit=unit,
            min_value=min_val,
            max_value=max_val,
            enum_values=enum_vals,
        )

    def _generic_keywords_for_operation(self, op_type: str) -> List[str]:
        """Return applicable generic keywords for this operation type."""
        if op_type in ("numeric", "range", "time", "frequency"):
            return self._generic_keywords["increase"] + self._generic_keywords["decrease"]
        elif op_type == "toggle":
            return self._generic_keywords["toggle"]
        elif op_type == "enum":
            return []  # Enum selection requires explicit values
        else:
            return []

    def _try_generic_language(self, canonical_target: str, context: Optional[Dict[str, Any]]) -> Optional[str]:
        """Check if generic language patterns apply to this target."""
        # Very conservative: only apply to controls where we have strong signal
        conservative_numeric = {
            "lfo1_rate", "lfo1_smooth", "lfo2_rate", "lfo2_smooth",
            "oscA_level", "oscB_level", "oscC_level", "noise_level",
            "filter1_cutoff", "filter1_resonance",
            "filter2_cutoff", "filter2_resonance",
        }

        norm = canonical_target.lower().replace(".", "_")
        if norm in conservative_numeric:
            return f"generic_numeric_for_{norm}"

        return None
