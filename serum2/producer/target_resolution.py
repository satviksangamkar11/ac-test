"""Ordered explicit-target resolution and the structured refusal record.

Implements architecture sections 7.1, 17, 18 and 19 (docs/VLP1_Fully_Revised_Architecture.md).

Pure logic over EXISTING data -- it owns no target, keyword or alias tables:

  surface form
      -> Atlas resolution (reference layer)      EXACT / ALIAS / AMBIGUOUS / UNRESOLVED
      -> canonical id
      -> Brain concept, derived from the existing target registries
         (compiler.targets.SEMANTIC_TARGETS + compiler.mcp_intent.MCP_HOST_MAP)
      -> [Capability Resolution and Admission stay where they are, in the Brain]

Reference coverage, Brain vocabulary and capability coverage are independent axes (section 6.1):
an Atlas entry is not a Brain concept, and a Brain concept is not a qualified capability. This
module answers only the first two questions; it never decides executability.

A refusal terminates the request. No step substitutes another target.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from serum2.producer.target_names import normalize_target_name, find_surface_tokens

# refusal codes (section 7.1) and the layer that emits them
REFUSED_UNRESOLVED_REFERENCE = "REFUSED_UNRESOLVED_REFERENCE"
REFUSED_AMBIGUOUS_REFERENCE = "REFUSED_AMBIGUOUS_REFERENCE"
REFUSED_NO_BRAIN_CONCEPT = "REFUSED_NO_BRAIN_CONCEPT"
REFUSED_NO_CAPABILITY = "REFUSED_NO_CAPABILITY"
REFUSED_ADMISSION = "REFUSED_ADMISSION"
REFUSED_UNCLASSIFIED = "REFUSED_UNCLASSIFIED"   # a legacy refusal status this taxonomy does not yet classify

LAYER_REFERENCE = "REFERENCE_RESOLUTION"
LAYER_BRAIN = "PRODUCER_BRAIN"
LAYER_CAPABILITY = "CAPABILITY_RESOLUTION"
LAYER_ADMISSION = "ADMISSION"
LAYER_UNKNOWN = "UNKNOWN"

# Legacy Brain execution_status -> canonical (code, layer). Bookkeeping over statuses that already
# exist; it selects nothing and resolves nothing. execution_status itself is kept unchanged.
LEGACY_STATUS_TO_REFUSAL: Dict[str, Tuple[str, str]] = {
    "REFUSED_UNKNOWN_CONCEPT": (REFUSED_UNRESOLVED_REFERENCE, LAYER_REFERENCE),
    "REFUSED_NO_MAPPING": (REFUSED_NO_CAPABILITY, LAYER_CAPABILITY),
    "REFUSED_NO_CONTRACT": (REFUSED_NO_CAPABILITY, LAYER_CAPABILITY),
    "REFUSED_NO_EVIDENCE": (REFUSED_NO_CAPABILITY, LAYER_CAPABILITY),
    "REFUSED_RESOLUTION_FAILED": (REFUSED_NO_CAPABILITY, LAYER_CAPABILITY),
    "REFUSED_ADMISSION": (REFUSED_ADMISSION, LAYER_ADMISSION),
    "REFUSED_AUTHORITY": (REFUSED_ADMISSION, LAYER_ADMISSION),
}


@dataclass(frozen=True)
class Refusal:
    code: str
    layer: str
    canonical_target: Optional[str]
    reason: str
    candidates: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "layer": self.layer, "canonical_target": self.canonical_target,
                "reason": self.reason, "candidates": list(self.candidates)}


@dataclass(frozen=True)
class TargetResolution:
    surface: str
    refusal: Optional[Refusal] = None
    canonical_id: Optional[str] = None      # Atlas canonical id
    registry_target: Optional[str] = None   # Brain-side target name from the existing registries
    capability_key: Optional[str] = None    # from SEMANTIC_TARGETS, if registered there
    concept: Optional[str] = None           # Brain concept (legacy concept if one exists, else derived)
    mapping: Any = None                     # SemanticTargetMapping for a DERIVED concept with a usable contract


class TargetResolver:
    def __init__(
        self,
        contract_registry,
        semantic_targets: Dict[str, Any],
        mcp_host_map: Dict[str, Any],
        legacy_mappings: Dict[str, Any],
        mcp_bridge: Dict[str, str],
        mapping_factory: Callable[..., Any],
        atlas_resolve: Optional[Callable[[str], Any]] = None,
    ):
        if atlas_resolve is None:
            from serum2.reference.serum_atlas import normalize_control
            atlas_resolve = normalize_control
        self._atlas = atlas_resolve
        self._contracts = contract_registry
        self._targets = semantic_targets
        self._factory = mapping_factory
        # registry index: comparable key -> registry target names (existing vocabulary, inverted)
        self._by_key: Dict[str, List[str]] = {}
        for name in list(semantic_targets) + list(mcp_host_map):
            names = self._by_key.setdefault(normalize_target_name(name), [])
            if name not in names:
                names.append(name)
        # existing concept tables, inverted (never extended here)
        self._legacy_concept_by_cap = {m.semantic_target: c for c, m in legacy_mappings.items()}
        self._mcp_concept_by_target = {t: c for c, t in mcp_bridge.items()}

    # -- helpers -----------------------------------------------------------------------------
    def surfaces(self, text: str, semantic_target: Optional[str]) -> List[str]:
        """Explicit surface forms named by the request: dotted tokens in the text plus semantic_target."""
        out = list(find_surface_tokens(text))
        if semantic_target and semantic_target not in out:
            out.append(semantic_target)
        return out

    def _resolve_one(self, surface: str) -> TargetResolution:
        r = self._atlas(surface)
        if r.status == "AMBIGUOUS":
            return TargetResolution(surface, Refusal(
                REFUSED_AMBIGUOUS_REFERENCE, LAYER_REFERENCE, None,
                "Reference resolution of %r is ambiguous between %s; not selecting one." % (surface, list(r.candidates)),
                tuple(r.candidates)))
        if r.status not in ("EXACT", "ALIAS"):
            return TargetResolution(surface, Refusal(
                REFUSED_UNRESOLVED_REFERENCE, LAYER_REFERENCE, None,
                "No canonical identity for %r in the reference Atlas." % surface))
        cid = r.canonical_id
        names = self._by_key.get(normalize_target_name(cid), [])
        if len(names) != 1:
            why = ("no Brain-side target is registered for it" if not names
                   else "several Brain-side targets %s match it" % names)
            return TargetResolution(surface, Refusal(
                REFUSED_NO_BRAIN_CONCEPT, LAYER_BRAIN, cid,
                "Canonical target %r resolved, but no Brain concept exists (%s)." % (cid, why)), canonical_id=cid)
        target = names[0]
        ref = self._targets.get(target)
        cap = getattr(ref, "capability_key", None)
        concept = self._legacy_concept_by_cap.get(cap) or self._mcp_concept_by_target.get(target)
        mapping = None
        if concept is None:
            concept = "canonical:" + normalize_target_name(target)
            contract = self._contracts.contracts.get(cap) if cap else None
            if contract is not None and contract.usable_for(required_causal=True):
                mapping = self._factory(
                    universal_concept=concept, semantic_target=cap, confidence=1.0,
                    rationale="derived from SEMANTIC_TARGETS + a CAUSAL_VERIFIED contract; not a hand-written mapping")
        return TargetResolution(surface, None, cid, target, cap, concept, mapping)

    # -- public --------------------------------------------------------------------------------
    def resolve(self, text: str, semantic_target: Optional[str]) -> Optional[TargetResolution]:
        """None when the request names no explicit target (natural-language path). Otherwise a
        TargetResolution, carrying a Refusal if any ordered step failed."""
        forms = self.surfaces(text, semantic_target)
        if not forms:
            return None
        results = [self._resolve_one(f) for f in forms]
        for r in results:
            if r.refusal is not None:
                return r
        ids = {r.canonical_id for r in results}
        if len(ids) > 1:
            return TargetResolution(forms[0], Refusal(
                REFUSED_AMBIGUOUS_REFERENCE, LAYER_REFERENCE, None,
                "The request names more than one canonical target %s; refusing rather than picking one." % sorted(ids),
                tuple(sorted(ids))))
        return results[0]
