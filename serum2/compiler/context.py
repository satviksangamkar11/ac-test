"""16.3: Required Context -- index-agnostic structural prerequisites a
capability's mutation path needs beyond what a base state already provides.

Derivation guard (explicit, non-negotiable): a single structural-failure probe
against a base state is only a CANDIDATE. Promotion to a RequiredContext needs
BOTH:
  - a POSITIVE witness: the capability's own CapabilityContract status is at
    least STRUCTURAL_ONLY -- i.e. some real EvidenceRecord's load (and, for
    STRUCTURAL_ONLY/CAUSAL_VERIFIED, persistence) gates actually PASSED for
    this exact mutation path, proving descent succeeded SOMEWHERE.
  - a NEGATIVE witness: descent against the CANDIDATE base state demonstrably
    fails at a specific list container, for lack of an element carrying the
    required key.
Neither alone promotes anything: a failing probe with no positive contract
is not evidence of a capability at all; a positive contract whose path
resolves cleanly against the base state needs no context.

Context is deliberately INDEX-AGNOSTIC per the explicit correction: the
requirement is "container list X contains an element with key Y", never
"index N of X is Y". Position is an execution-time resolution detail
(resolve_index), never part of the capability's own semantics -- this is
what keeps the compiler from silently depending on one witness preset's
particular layout.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from ..pathmerge import _is_index_segment, SPARSE_DEFAULT

POSITIVE_WITNESS_STATUSES = ("STRUCTURAL_ONLY", "CAUSAL_VERIFIED")


def element_key_present(element, key: str) -> bool:
    return isinstance(element, dict) and key in element and element[key] not in (None, SPARSE_DEFAULT)


@dataclass(frozen=True)
class RequiredContext:
    container_path: str      # dotted path to the LIST, e.g. "FXRack0.FX"
    element_key: str         # required dict key an element of that list must carry, e.g. "FXDistortion"
    leaf_suffix: str         # remaining path after the index+key, e.g. "plainParams.kParamDrive"

    def _container_list(self, body):
        node = body
        for part in self.container_path.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node if isinstance(node, list) else None

    def satisfied_by(self, body) -> bool:
        """Membership/type only -- position is never checked."""
        lst = self._container_list(body)
        if lst is None:
            return False
        return any(element_key_present(el, self.element_key) for el in lst)

    def resolve_index(self, body) -> Optional[int]:
        """Execution-time detail: find AN actual index satisfying this
        context in the given body. Never assumes a fixed slot -- this is
        exactly the substitutability property: two bodies with the required
        element at different positions both resolve correctly."""
        lst = self._container_list(body)
        if lst is None:
            return None
        for i, el in enumerate(lst):
            if element_key_present(el, self.element_key):
                return i
        return None

    def resolve_path(self, original_path: str, body) -> Optional[str]:
        """Rewrites original_path's index segment to whatever this body's
        actual matching index is. Returns None if unsatisfied."""
        idx = self.resolve_index(body)
        if idx is None:
            return None
        return "%s.%d.%s.%s" % (self.container_path, idx, self.element_key, self.leaf_suffix)


def _structural_probe(body, dotted_path: str) -> Optional[Tuple[str, str, str]]:
    """Walk dotted_path against body using the SAME dict/list type rules
    pathmerge itself uses for descent, but non-destructively and never
    raising. Returns (container_path, element_key, leaf_suffix) at the FIRST
    point a list lacks the needed index, or None if the path already
    resolves (or fails for a reason that isn't a list-context gap -- a
    missing dict key is routinely auto-expanded by pathmerge and is NOT a
    context gap)."""
    parts = dotted_path.split(".")
    node = body
    consumed = []
    for i, part in enumerate(parts[:-1]):
        if isinstance(node, list):
            if not _is_index_segment(part) or int(part) >= len(node):
                container_path = ".".join(consumed)
                if i + 1 >= len(parts):
                    return None  # malformed path -- nothing coherent to derive
                element_key = parts[i + 1]
                leaf_suffix = ".".join(parts[i + 2:])
                return (container_path, element_key, leaf_suffix)
            node = node[int(part)]
            consumed.append(part)
        elif isinstance(node, dict):
            child = node.get(part)
            if child is None or child == SPARSE_DEFAULT:
                return None  # dict gap: pathmerge auto-expands this, not a context problem
            node = child
            consumed.append(part)
        else:
            return None
    return None


def extract_required_context(mutation_target_path: str) -> Optional[RequiredContext]:
    """Extract RequiredContext from path structure alone, without probing a body.

    Finds the first numeric segment: everything before it becomes container_path,
    the following segment becomes element_key, and the remainder becomes leaf_suffix.
    Returns None if the path has no numeric segment (no list traversal required).

    Use this for runtime path resolution ("WHERE does this target live in a given
    body?"). Do NOT confuse with derive_required_context(), which answers "DOES
    this capability require context at all?" -- a different question that requires
    a positive contract status and a candidate base body for negative probing.

    Both functions produce RequiredContext objects from the same canonical
    dataclass; only the derivation question differs. Logic for RequiredContext
    lives exclusively in this module -- callers must import it from here, never
    re-derive it elsewhere.
    """
    parts = mutation_target_path.split(".")
    for i, part in enumerate(parts):
        if _is_index_segment(part):
            container_path = ".".join(parts[:i])
            if i + 1 >= len(parts):
                return None  # malformed path: nothing after the list index
            element_key = parts[i + 1]
            leaf_suffix = ".".join(parts[i + 2:])
            return RequiredContext(
                container_path=container_path,
                element_key=element_key,
                leaf_suffix=leaf_suffix,
            )
    return None


def derive_required_context(mutation_target_path: str, contract_status: str,
                            candidate_base_body) -> Optional[RequiredContext]:
    if contract_status not in POSITIVE_WITNESS_STATUSES:
        return None  # no positive witness -- nothing to promote
    probe = _structural_probe(candidate_base_body, mutation_target_path)
    if probe is None:
        return None  # no negative witness -- path already resolves against this base state
    container_path, element_key, leaf_suffix = probe
    return RequiredContext(container_path=container_path, element_key=element_key, leaf_suffix=leaf_suffix)


def extract_prerequisite_value(body: Dict[str, Any], field_path: str) -> Any:
    """Extract the ACTUAL value from body for a prerequisite field_path.

    Navigates the body structure using the same dict/list rules pathmerge uses.
    Returns the actual value found, or None if path does not resolve.

    Used by the compiler's dry_run() to build value-bearing prerequisite
    verification dicts that capture the ACTUAL runtime state, not just
    a boolean success flag.

    field_path examples: "Env0.plainParams.kParamDecay", "FXRack0.FX.0.FXDistortion.plainParams.kParamDrive"

    16.5.51: Prerequisites may be prefixed with 'body:' or 'host:'; strip it.
    """
    if not body:
        return None

    # Strip 'body:' or 'host:' prefix if present (added for harness compatibility)
    path = field_path
    if path.startswith("body:"):
        path = path[5:]
    elif path.startswith("host:"):
        path = path[5:]

    parts = path.split(".")
    node = body
    for part in parts:
        if isinstance(node, dict):
            if part not in node:
                return None
            node = node[part]
        elif isinstance(node, list):
            if not _is_index_segment(part):
                return None
            idx = int(part)
            if idx >= len(node):
                return None
            node = node[idx]
        else:
            return None
    return node
