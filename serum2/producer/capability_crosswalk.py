"""Explicit capability_key ↔ atlas_id crosswalk.

This crosswalk is the ONLY place where the semantic capability_key naming
convention (used by SEMANTIC_TARGETS in targets.py) is mapped to the atlas_id
naming convention (used by binding evidence files).

Every entry here was reviewed by hand.  NO string heuristics, suffix matching
or pattern substitution are permitted -- that would let one control borrow
another's evidence (e.g. env2.decay accidentally taking env1.decay evidence).

When to add an entry:
  - Binding evidence was collected under an atlas_id (e.g. "env2.decay")
  - The producer route requests it under a different capability_key
    (e.g. "envelope2_field_decay" from SEMANTIC_TARGETS)
  - A human has verified that the two names refer to the same physical control

When NOT to add an entry:
  - If the two names refer to different controls (even if similar)
  - As a quick fix for any name that "almost matches"

The crosswalk must remain small and explicit.  Prefer fixing the atlas_id in
the evidence file or the capability_key in SEMANTIC_TARGETS when there is a
genuine naming error, and only use this crosswalk when both conventions are
deliberately kept for different reasons.
"""

# Maps capability_key → atlas_id.
# The contract is stored in ContractRegistry.contracts under the atlas_id;
# the crosswalk creates an alias so that lookups by capability_key also resolve.
CAPABILITY_KEY_TO_ATLAS_ID: dict = {
    # Envelope 2 decay: evidence collected as "env2.decay" (Env1.plainParams.kParamDecay);
    # SEMANTIC_TARGETS maps "Env2.Decay" → capability_key "envelope2_field_decay".
    # These are the same physical control — envelope index 2 (Serum's Env 2, 0-indexed as
    # Env1 in the body path) decay parameter.  Reviewed 2026-09-27.
    "envelope2_field_decay": "env2.decay",
    # Envelope 1 attack: evidence collected as "env1.attack" (Env0.plainParams.kParamAttack);
    # SEMANTIC_TARGETS maps "Env1.Attack" → capability_key "envelope_field_attack". These are
    # the same physical control — envelope index 1 (Serum's Env 1, 0-indexed as Env0 in the
    # body path) attack parameter. Without this entry, get_by_capability_key("envelope_field_attack")
    # returns None even though env1.attack has a real, qualified, accessor-bound contract
    # (resolver_operation_id="envelopes[0].attack") -- causing RouteSelector to fall through to
    # ABLETON_MCP (MCP_HOST_MAP has "Env1.Attack") instead of the correct DAWDREAMER_SERUM route,
    # since a Serum-internal envelope field is never on the Ableton-exposed 127-param surface.
    # Found during a real W1 native run (blocked before native load: execution_route=ableton_mcp
    # instead of dawdreamer_serum). Reviewed 2026-09-27.
    "envelope_field_attack": "env1.attack",
}
