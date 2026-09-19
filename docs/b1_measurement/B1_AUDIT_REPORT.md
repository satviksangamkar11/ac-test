# B1 audit report (2c0h3z41K58, frozen artifacts, nothing re-acquired)

Method: every semantic changed control of every timeline event (10 controls, 9 events) was run individually through
`ProducerBrain.execute()`, once on the pre-B1 brain (commit 1a7dbfb, B1 not wired) and once on the wired brain.
Script: `serum2/producer/measure_b1_baseline.py`. Data: `B1_BASELINE_BEFORE.json`, `B1_BASELINE_AFTER.json`.

## Result
| | before | after |
|---|---|---|
| controls / events | 10 / 9 | 10 / 9 |
| EXECUTABLE | 0 | 0 |
| REFUSED_NO_CAPABILITY | 5 | 5 |
| REFUSED_NO_BRAIN_CONCEPT | 4 | 4 |
| REFUSED_UNRESOLVED_REFERENCE | 1 | 1 |
| events with no semantic intent | 4 | 4 |

**0 of 14 rows changed.** B1 moved no event to a different terminal state. That is the expected outcome for this
change: B1 adds an auditable representation/operation/context/intent on the canonical path; it does not add
targets, capabilities or authority. It is not evidence of improved coverage.

## Which brain produced each outcome (new, machine-visible)
- B1_CANONICAL (5): env2.decay, env2.sustain, oscB.enabled, lfo1.rate, filter1.enabled -> all refused downstream
  at Capability Resolution (`envelope2_field_decay`, `envelope2_field_sustain`, `oscillator_field_OSC2-ENABLE`,
  `lfo_field_lfo1_rate`, `filter_field_ENABLE` have no CAUSAL_VERIFIED contract).
- REFUSED before B1 could run (5): oscA.warp_mode, oscB.mode, lfo1.smooth (x2) -> REFUSED_NO_BRAIN_CONCEPT;
  oscA.wt_pos_display -> REFUSED_UNRESOLVED_REFERENCE (Atlas has no entry).
- LEGACY: none of the frozen events used the natural-language table (all were explicit canonical targets).

## Newly resolved concepts audit
None moved from Brain refusal to a candidate intent, so there is nothing to audit for invention. Substitution check:
env2.decay resolves to its OWN capability key `envelope2_field_decay` and is refused for lack of a contract; it does not
borrow env1's `envelope_field_decay` (test_b1_integration.py::test_other_envelope_slots_keep_their_own_capability...).

## Defects found and fixed while integrating
- `contract_hints` (hand-written target->contract dict, which also gave env2/env3/env4 the Env1 contract): removed.
  B1 now consumes TargetResolver's Atlas id -> registry target -> capability_key join.
- `conservative_numeric` and the enum-value vocabulary table in B1 modules: removed.
- OperationInterpreter read the digit in `Env1` as a value (value=1): fixed; only standalone numbers are values.

## Still true / not done
- `_INTENT_TO_CONCEPT` remains as a LEGACY fallback (resolution_mode=LEGACY, b1_used=false); B1 does not own natural-language targets.
- `_MCP_CONCEPT_BRIDGE` (pre-existing dict in producer_brain.py) is untouched and still needs a provenance-backed home.
- `request_context.py` holds generic scope/descriptor word lists. They are advisory metadata and never select a target,
  but they are still developer-authored vocabulary.
- Regression: 255 passed, 1 skipped (`B1_REGRESSION_RESULTS.txt`).
- `vlp1-b1-verified` NOT created; awaiting your call given the caveats above.
