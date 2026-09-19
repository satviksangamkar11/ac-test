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
from serum2.producer.contract_registry import ContractRegistry
from serum2.evidence.capability_contract import CapabilityContract
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
    capability_contract: Optional[CapabilityContract] = None  # if CAUSAL_VERIFIED exists
    semantic_target_name: Optional[str] = None  # Brain-side target name from SEMANTIC_TARGETS
    capability_key: Optional[str] = None  # from TargetResolver (the single target->capability join)

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
            "capability_key": self.capability_key,
            "provenance": self.provenance.value,
            "confidence": self.confidence,
            "derivation_chain": self.derivation_chain,
            "value_domain": self.value_domain.__dict__ if self.value_domain else None,
        }


class ConceptDerivationEngine:
    """B1.2: derive a ConceptRepresentation from a RESOLVED target.

    TargetResolver is the single canonical target -> capability join (Atlas id -> registry target ->
    capability_key). This engine CONSUMES that result; it owns no target, contract or keyword table and
    never re-discovers a contract by name/suffix (which would let env2.decay borrow env1's contract).

    Provenance, in order:
      CONTRACT              the resolved capability_key names a CAUSAL_VERIFIED contract
      LEGACY_SEMANTIC_TARGET  registered Brain target, no usable contract
      MCP_HOST_MAP          registered only on the MCP host surface
      MISSING               the resolver refused (no Atlas identity / ambiguous / no Brain concept)
    """

    # Generic English direction vocabulary (language, not controls); descriptive metadata only.
    _GENERIC_KEYWORDS = {
        "decrease": ["off", "less", "lower", "down", "reduce", "decrease", "shorter", "shorten",
                     "quieter", "smaller", "tighter"],
        "increase": ["more", "up", "raise", "increase", "longer", "louder", "higher", "bigger",
                     "larger", "extend", "boost"],
        "toggle": ["on", "off", "enable", "disable"],
    }

    def __init__(self, contract_registry: ContractRegistry, semantic_targets=None, mcp_host_map=None,
                 target_resolver=None):
        self._contracts = contract_registry
        self._targets = semantic_targets if semantic_targets is not None else SEMANTIC_TARGETS
        self._mcp_map = mcp_host_map if mcp_host_map is not None else MCP_HOST_MAP
        if target_resolver is None:
            from serum2.knowledge.step_6_6_capability_resolution import UNIVERSAL_TO_SEMANTIC, SemanticTargetMapping
            from serum2.producer.target_resolution import TargetResolver
            target_resolver = TargetResolver(contract_registry, self._targets, self._mcp_map,
                                             UNIVERSAL_TO_SEMANTIC, {}, SemanticTargetMapping)
        self._resolver = target_resolver

    def derive(self, canonical_target: str, context: Optional[Dict[str, Any]] = None) -> ConceptRepresentation:
        """Convenience: resolve a canonical/explicit surface through the resolver, then derive."""
        return self.derive_from_resolution(self._resolver.resolve("", canonical_target), canonical_target)

    def derive_from_resolution(self, res, surface: str = "") -> ConceptRepresentation:
        chain = ["derive_from_resolution(%s)" % (surface or getattr(res, "surface", ""))]
        if res is None:
            return ConceptRepresentation(canonical_target=surface, provenance=Provenance.MISSING,
                                         derivation_chain=chain + ["no explicit target to derive from"])
        if res.refusal is not None:
            chain.append("target_resolver: %s (%s)" % (res.refusal.code, res.refusal.layer))
            return ConceptRepresentation(canonical_target=res.canonical_id or surface,
                                         provenance=Provenance.MISSING, derivation_chain=chain)
        cid = res.canonical_id
        chain.append("target_resolver: %s -> registry target %s, capability_key %s"
                     % (cid, res.registry_target, res.capability_key))
        contract = self._contracts.contracts.get(res.capability_key) if res.capability_key else None
        common = dict(canonical_target=cid, atlas_entry=normalize_control(cid),
                      semantic_target_name=res.registry_target, capability_key=res.capability_key,
                      derivation_chain=chain)
        if contract is not None and contract.usable_for(required_causal=True):
            chain.append("contract_registry[%s]: %s" % (res.capability_key, contract.status))
            rep = ConceptRepresentation(capability_contract=contract,
                                        operation_type=self._operation_type(contract),
                                        value_domain=ValueDomain(type=self._operation_type(contract)),
                                        provenance=Provenance.CONTRACT, confidence=0.95, **common)
        elif res.registry_target in self._targets:
            chain.append("registered Brain target without a CAUSAL_VERIFIED contract")
            rep = ConceptRepresentation(provenance=Provenance.LEGACY_SEMANTIC_TARGET, confidence=0.7, **common)
        elif res.registry_target in self._mcp_map:
            chain.append("registered on the MCP host surface only")
            rep = ConceptRepresentation(provenance=Provenance.MCP_HOST_MAP, confidence=0.7, **common)
        else:
            chain.append("resolved but not registered anywhere")
            return ConceptRepresentation(canonical_target=cid, provenance=Provenance.MISSING, derivation_chain=chain)
        rep.generic_language_keywords = self._keywords(rep.operation_type)
        return rep

    @staticmethod
    def _operation_type(contract: CapabilityContract) -> str:
        return {"mutate_numeric_value": "numeric", "mutate_enum_value": "enum",
                "mutate_structured_value": "structured"}.get(contract.allowed_operation, "unknown")

    def _keywords(self, op_type: str) -> List[str]:
        if op_type == "numeric":
            return self._GENERIC_KEYWORDS["increase"] + self._GENERIC_KEYWORDS["decrease"]
        if op_type == "toggle":
            return self._GENERIC_KEYWORDS["toggle"]
        return []
