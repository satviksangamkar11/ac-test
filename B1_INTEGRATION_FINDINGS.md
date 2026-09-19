# B1 integration attempt — findings (2026-09-19)

Attempted: wire B1 into `ProducerBrain._resolve_concept()` and remove `contract_hints`. Reverted; nothing landed.

## What went wrong in the attempt
1. Passing the whole sentence to `normalize_control()` almost never resolves, so the natural-language path returned no concept.
   Regressions: `test_natural_language_that_names_release_or_attack_still_works`, and unresolved refs mislabelled
   `REFUSED_NO_BRAIN_CONCEPT` (wrong layer) in `test_refusal_unresolved_reference`.
2. Field-suffix matching of contract keys (`envelope_field_decay` <- `env*.decay`) is a name heuristic and gives every
   envelope slot the Env1 contract. Not acceptable.

## Correct data-driven join (already exists)
Atlas canonical id -> `SEMANTIC_TARGETS[registry name].capability_key` -> `ContractRegistry.contracts[key]`.
`TargetResolver._resolve_one` already does this. `ConceptDerivationEngine._find_contract` should reuse it, not a dict.

## Decision needed (user)
The legacy natural-language path (`_INTENT_TO_CONCEPT`) maps e.g. "sustain longer" -> `note-release`, and a test pins it.
Replacing it with Atlas-alias-derived resolution changes that behaviour ("sustain" is ambiguous across ENV1-4 -> refusal).
Architecture says legacy behaviour must stay explicit, so this needs an explicit ruling before removal.
