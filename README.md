# Reference-to-Serum Reproduction (VLP1)

A pipeline that watches a reference (a tutorial video or sound), works out which **Serum 2** controls were changed, and reproduces
that state in a `.SerumPreset` — with every step gated by evidence, not by naming or memory. Serum is driven only through
[serum-mcp](vendor/serum-mcp) (vendored here). Claude Code is the model runtime; there is no Anthropic SDK call in the canonical path.

> **Status (measured 2026-09-21):** `python -m pytest` → **925 passed, 3 skipped**. Current run epoch: Serum **2.0.23**.
> Only 9 operations are admitted and live-UI verified. Read [AUDIT.md](AUDIT.md) before trusting any claim in this repo:
> it lists known authority gaps (some of the "invariants" below are not yet fully enforced).

## Core rules

1. **Evidence ≠ authority.** Only a `CapabilityContract` grants execution, and only through admission.
2. **Capability ≠ admission.** A qualified control still needs an admitted operation.
3. **Reference facts ≠ logic.** No per-parameter code (`if target == "filter1.enabled"`); known data (tables, evidence JSON) is never execution logic.
4. **Memory / learned skills are advisory.** They may rank or interpret, never authorize.
5. **Brain reasons; it never executes.** Chain: Brain → Target Resolution → Capability Resolution → Admission → `AuthorizedOperation` → compiler.
6. **`HOST_PARAMETER` (VST3) is an evidence surface, not execution authority.** Execution-eligible bindings: `SERUM_PRESET_STRUCTURAL`, `BODY_STATE`, `TOPOLOGY`.
7. **Epoch isolation.** A contract proven on one Serum build (binary SHA-256) never applies to another.
8. **Proof level and coverage are separate axes.** `LIVE_UI_VERIFIED` + `COMPLETE` + no unexplained differences is the only route to `REFERENCE_REPRODUCTION_VERIFIED`.
9. **No invention.** Not visible ≠ removed; unreadable ≠ exact value; transcript ≠ executed action; audio similarity ≠ identical state. `None` means unknown.

## Pipeline

```
reference video ─► transcript + frames ─► Stage-A visual observations (from the Claude Code session)
   ─► state ledger (every observation → exactly one terminal outcome)
   ─► typed operations ─► Atlas / target resolution ─► contract lookup ─► admission
   ─► AuthorizedOperation ─► generic compiler ─► .SerumPreset (via serum-mcp)
   ─► file readback ─► direct-UI readback ─► normalized comparison
   ─► VerifiedOperationEvidence / VerifiedReferenceEpisode ─► learning (advisory)
```

## Repository map

| Path | What it is |
|---|---|
| `serum2/evidence/` | Data model: `EvidenceRecord` → `ClaimGroup` → `CapabilityContract` (+ `ExecutionBinding`) → `admit()`. Contract tiers: `CAUSAL_VERIFIED`, `STRUCTURAL_ONLY`, `NEGATIVE_EVIDENCE`, `UNSUPPORTED`, `BLOCKED_CONTRADICTED`; tiers are never upgraded. |
| `serum2/producer/` | Ledger, admission, contract registry, epoch, route classification, target resolution, Brain, skills, grounding, fusion, qualification runner. Tests live beside the code (`test_*.py`). |
| `serum2/execution/` | `authorized_state_compiler.py` (**the** compiler), `state_comparator.py` (serialize + readback + compare). `authorized_preset_compiler.py` is legacy (Prague Lead) — do not extend. |
| `serum2/server/` | `reference_reproduction.py` (run object, proof level, coverage), experience records, and the older FastMCP creation pipeline. |
| `serum2/reference/` | Serum Atlas, UI atlas, hash-pinned audit, `serum_mcp_binding_table.json` (233 **candidates**; a name match is not proof). |
| `serum2/qualification/` | Evidence artifacts and tools: `pass1/` (Serum 2.0.23 kit), `candidate_binding_qualifier.py`. |
| `serum2/knowledge/` | Advisory knowledge store and resolution steps. Live: `step_5_6`, `5_7`, `6_2`–`6_10`. Historical: `step_6_11`, `intent_bridge`, `semantic_intent_resolver`. |
| `serum2/compiler/`, `serum2/orchestration/` | Legacy natural-language / Gate-2A layers. Deprecated. |
| `serum2/source/` | YouTube transcript and frame acquisition. |
| `vendor/serum-mcp/` | Vendored serum-mcp (upstream commit in `UPSTREAM_COMMIT.txt`). |
| `docs/VLP1_Fully_Revised_Architecture.md`, `FREEZE_VLP1.md` | Frozen architecture (authoritative). |
| `tests/` | Reference-reproduction, ledger, boundaries and compiler tests with committed fixtures. |
| `experiments/*.pkl` | Pickled contract stores loaded by `ContractRegistry` (see Security). |

Most other root-level `.md`/`.json` files are historical phase reports or generated artifacts; treat them as history, not spec.
Docs that quote different test counts, or say Serum 2.0.21, predate the current epoch.

## Setup

- Windows, Python 3.14 (tested), Serum 2 **2.0.23** VST3 for live/UI work. Only `pytest` is required for the test suite; there is no dependency file yet.
- serum-mcp needs the presets folder from an environment variable and never guesses it:

```bash
export SERUM_PRESETS_PATH="/path/to/Serum 2 Presets/Presets"   # PowerShell: $env:SERUM_PRESETS_PATH = "..."
```

- The repo puts `vendor/serum-mcp/src` on `sys.path` itself (via `conftest.py` and per-module inserts). Nothing needs `D:/serum-mcp`.
- Some code still writes scratch presets under `VLP1*` subfolders of the presets directory. Point `SERUM_PRESETS_PATH` at a throwaway folder when experimenting.

## Run the tests

```bash
python -m pytest                       # this repo's tests (925 pass, 3 skip)
PYTHONPATH=vendor/serum-mcp/src python -m pytest vendor/serum-mcp/tests   # vendored serum-mcp's own tests (253)
```

The 3 skips: no learning-eligible episode on disk, no Osc B/C target in one planner test, and a compiler-integration test whose module does not exist.
Tests marked as depending on gitignored `serum2/data/` artifacts skip if those are absent; a clean clone will not reproduce full runs.

## Qualifying a control (generic, serum-mcp only)

`serum2/qualification/candidate_binding_qualifier.py` takes only a control id. It reads the candidate accessor `{list, index, field}` from the binding
table, takes a value from the Atlas domain, runs the unmodified `StructuralQualificationRunner` lifecycle (load → read → mutate → read → persist → reload → read),
derives the body path from a diff (never from a table), and checks that the whole extracted spec changed only in the targeted field.

```bash
python -m serum2.qualification.candidate_binding_qualifier filter1.enabled oscB.octave env2.decay --out ./qual_out
```

Verified: it reproduces all 10 existing Pass-1 bindings (Osc B/C enable and octave, Env 2–4 decay and release) and qualifies `filter1.enabled`
→ `VoiceFilter0.plainParams.kParamEnable` and `filter2.enabled` → `VoiceFilter1.plainParams.kParamEnable` at **file level**.

Limits, so nobody over-reads the result:
- File-level evidence only — no direct-UI readback, and it creates **no** `CapabilityContract`. A binding is not a contract.
- serum-mcp partial specs are **positional** (editing list index *N* needs entries `0..N`) and silently drop a write equal to a field's default, so the runner records `baseline_restorable`.
- Only `toggle` and `continuous` controls are handled; enum controls need reviewed value aliases.
- Candidates are pre-marked `verified=True` with a label-only capability key, and the verdict is not epoch-pinned.

## Security and known traps

- `ContractRegistry` unpickles `experiments/*.pkl` and `PASS1-*.pkl` records. Treat those files as executable code; only load ones you trust.
- `producer_brain.py` still has paths that set `admitted=True` without a contract (MCP/host paths) and default values it should not invent. See [AUDIT.md](AUDIT.md) B1–B3.
- `AuthorizedOperation` fields are trusted by the compiler; a hand-built one would pass. See AUDIT H5.
- `LIVE_UI_VERIFIED` currently depends on the honesty of the UI readback JSON you supply. See AUDIT H6.
- `serum2/producer/_finalize_mu6_episode.py` writes a hand-authored "verified" episode on import. **Do not run it.**
- `serum2/evidence/{harness,spec,epoch}.py` are not in this repo; the Pass-1 experiment scripts reach them through the older `D:\ableton claude` repo. New Pass-1 evidence cannot be generated from this repo alone.
- `ClaimDefinition.claim_definition_id` calls `digest(obj, 8)` but `canonical.digest` takes one argument — the claim → contract build path is broken here (AUDIT H1).

## Contributing rules

- Add data, not branches: new controls come from the Atlas, binding table and evidence, never from `if target == ...`.
- Never weaken compiler validation or convert `HOST_PARAMETER` into execution authority.
- A new capability needs real mutation evidence (before / after / reload) through serum-mcp before any binding or contract exists.
- Report failures as failures; do not record projected or mock evidence.
