# DECISION LOG

## 2026-09-24 — Reference reproduction product direction

- Every video frame must receive an analysis record. Compute may be optimized through batching/windows, but evidence coverage cannot be reduced by sparse sampling.
- Local perception is preferred: local ASR + local VLM + specialized OCR.
- Transcript is supporting evidence, not execution authority.
- VLM is observation-only, not execution authority.
- The Producer Brain operates over complete Reference Knowledge, including non-executable parameters.
- Non-executable parameters are retained and documented rather than dropped.
- Knowledge and execution projection are separate layers.
- Execution remains Atlas/Target -> Capability -> Admission -> Generic Compiler -> serum-mcp.
- Memory improves retrieval/reasoning but cannot grant authority.
- Evidence-derived authority loading remains explicit via binding_evidence_dir.
- No per-parameter execution exceptions; schema/Atlas/domain rules must remain generic.
- Trial artifacts must never overwrite verified artifacts.

## 2026-09-24 — Boolean operand_kind classification is generic, driven by operation family and evidence value type

- `TOGGLE_ON` / `TOGGLE_OFF` operations always classify as `operand_kind = BOOLEAN` (op_operand(), contract_scope.py). No parameter-specific exceptions; applies to every boolean toggle field.
- A capability contract's own operand-kind classification must independently agree: a contract built from a Python `bool` evidence value now classifies as `MUTATE_BOOLEAN` / `"boolean"` (previously silently folded into `MUTATE_ENUM`), so admission's operand-kind compatibility check (`state_admission.py`) compares boolean-to-boolean on both sides instead of accidentally matching on "numeric" or mismatching against "enum". This is the second half of the same generic fix — the operation-side fix alone was insufficient.
- No admission bypass and no compiler weakening were introduced to make any operation pass; the fix was made entirely in the operand-kind type-inference layer (contract typing), which both admission and the compiler consume unchanged.
- A contract whose underlying evidence never proved a `bool`/`value_domain:"bool"` value (e.g. legacy Pass-1 records storing raw floats with no declared domain) is correctly refused as INCOMPATIBLE_OPERATION against a boolean operation, even if it happened to admit before under a coincidental numeric/numeric match. This is treated as an honest, pre-existing evidence-typing gap to be re-qualified, not a regression to hide.
- Verification result: `oscA.enabled` and `filter1.enabled` traced through the full canonical chain (ledger → operation → target → capability → admission → compiler → serum-mcp → file readback → live Serum UI) and both reached `VERIFIED_EXACT` against a real, live-loaded Serum 2 plugin instance (not `describe_preset`, not file self-comparison). `oscB.enabled`/`oscC.enabled` remain correctly blocked pending Pass-1 evidence re-qualification. The trial's overall proof_level was separately capped by an unrelated `env2.sustain` UI mismatch (see PROJECT_STATE.md), confirming the boolean fix did not mask or paper over that unrelated finding.

## 2026-09-24 — Percentage conversion is not universally linear; the curve is field metadata

- Percent → raw conversion for a normalized 0..1 field is driven by the target field's declared display curve: `json_schema_extra={"display_curve": {"kind": "power", "exponent": N}}`, meaning Serum displays `raw**N * 100`.
- One generic rule: `raw = (percent/100) ** (1/N)`. Linear is `N = 1`; Serum ENV sustain is `N = 2` (measured live: raw 0.25/0.50/0.81 → 6%/25%/66%).
- No control-name branching, no field-name branching, no envelope-index branching, no hardcoded numeric answers. Which fields carry which exponent is data, backed by measured evidence.
- An undeclared or invalid curve on a `%` → 0..1 conversion is refused with an explicit reason; it is never guessed (linear or otherwise).
- Conversion stays downstream of evidence (the observed `%` is unchanged) and upstream of authorization (admission/compiler unchanged).
- Independent of the Boolean operand-kind fix; that fix is unchanged.
- Verification: trial `qUNIEASFZSs_trial3_sustain_curve` — env2.sustain reference 60% → raw 0.7746 → Serum UI 60%; all 15 compiled ops LIVE_UI_VERIFIED; coverage PARTIAL.
