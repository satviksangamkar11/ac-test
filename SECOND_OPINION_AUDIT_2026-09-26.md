# Independent Second-Opinion Audit: Serum 2.0.23 / YouTube → SerumPreset

**Date:** 2026-09-26  
**Auditor:** Claude Code (adversarial source-level audit; no prior agent conclusions trusted)  
**Branch audited:** `claude/final-mcp-execution-contract-2mew5v` @ `2f7acb3`  
**Method:** Read all 251 non-main commit descriptions and all 58 remote branch tips; ran four probe scripts in a detached worktree of `2f7acb3` simulating the real Windows 2.0.23 epoch by monkeypatching `installed_epoch()`.

> **IMPORTANT:** As of this report, none of the fixes described in §6/§7 have been implemented.
> Findings F1–F16 are verified against the current codebase.
> The "Verification" section of the execution plan lists *acceptance criteria* for upcoming work, not achieved results.

---

## §1. Branch Topology

Verified with `merge-base --is-ancestor`.

- **Integration tip:** `claude/final-mcp-execution-contract-2mew5v` (`2f7acb3`, +253 commits vs `main`). Contains every product, Qwen, fix, closure, sweep-v3, video-capture, and phase branch.
- **Four branch tips carry work NOT integrated:**
  - `claude/quirky-franklin-a9x2d3` (`b5508df`, `20a1052`). Has a **different, incompatible** `final_execution_contract_v1.json` at the **same path**: schema `{summary, controls}` vs `{rows, producer_lookup, …}`. Also has `serum2/producer/final_execution_contract.py` making the final contract the **primary authority** for `allowed_operation`/`body_path`/`domain`. This is the opposite of `2f7acb3`'s "evidence gate on top of CapabilityContract" design. The two diverged at `98cdfa5` and will conflict on merge. **Rejected: keep as history only.**
  - `feature/serum-track-loader` (`e7da4b5`): the 20/20 qualification evidence JSONs and the nonce-rollback fix. The loader code was cherry-picked into the tip; the evidence was not. **Merge the evidence only.**
  - `claude/sleepy-turing-epm90g` (`a3264b1`): `serum_preset_drop.py`, a third OLE-drop implementation. Not integrated.
  - `claude/sharp-galileo-if30mw` (`7b7bcd1`): cloud-to-local Ableton bridge via Cloudflare tunnel. Not integrated.
- `main` (`82bd4be`) is a stale snapshot. Branches `finish-line-b-live-serum` and `finish-line-b-execution-2026-09-27` are the same commit. Branches `docs-audit-vendor-serum-mcp` and `reference-repro-qUNIEASFZSs` are also the same commit.

---

## §2. Findings Verified by Running Code (highest severity first)

**F1: The canonical reference path can use only 10 contracts on real Serum 2.0.23.**
- On the real 2.0.23 epoch, `ContractRegistry` loads 231 contracts. **221 of them are "pathless"**: `promote_verified_evidence()` (`serum2/qualification/evidence_promotion.py:309`) writes `scope` without `mutation_target_path`.
- `contract_scope.coverage_of()` keys only on `mutation_target_path`, so `find_contract()` can never match them.
- Result: `env1.attack` → `NO_CAPABILITY`; `oscA.enabled` → `EPOCH_MISMATCH`.
- The only admittable targets are the 10 Pass-1 contracts: osc2/3 enable/octave and env2-4 decay/release.

**F2: "310 executable" at runtime is really 221.**
- The loader re-validates each evidence file against the *un-augmented* Atlas. 89 files are rejected as `MISSING_DOMAIN`, because the builder used in-memory domain augmentation that the runtime never sees (commit `e5148d3`).
- `reference_engine.BINDING_EVIDENCE_DIR` points at `parameter_characterization/binding_evidence`, whose 9 files are the wrong shape. 0 of 9 load.

**F3: The ledger crashes on common controls.**
- `state_ledger._coerce()` handles only the `osc/env/lfo/filter` field kinds and `fx`.
- Any Stage-A observation of a `macro` field (16 bindings) raises `KeyError 'macro'`.
- Any `singleton_field` (53 bindings: global/arp/voice) raises `KeyError 'fx_type'`.
- One such observation aborts the whole run.

**F4: ProducerBrain plans the qualification test value, not the requested value.**
- `_build_serum_preset_plan` uses `scope["mutation_value_used"]`. That is the value the qualification experiment wrote (`capability_contract.py:334`).
- Verified: "Env1.Attack to 1.5 ms", "…900 ms", and "…0" all plan `{'kParamAttack': 0.8}`.

**F5: The env1.attack "runtime-consumption proof" works only across epochs.**
- The test and `live_proof_env1_attack.py` use `ProducerBrain()` with `epoch=None`.
- That combines a **2.0.21-proven** CapabilityContract (sha `7978c9be`, `HOST_PARAMETER` binding) with **2.0.23** final-contract evidence. `execution_spec()` serves it unfiltered when `epoch=None`.
- With the real 2.0.23 epoch, ProducerBrain returns `REFUSED_NO_CONTRACT` for `env1.attack`, so the final-contract gate is never even reached.
- The "admitted with epoch" proof (`test_producer_brain_epoch_evidence.py`) calls `admit()` directly, not `execute()`.

**F6: The live-proof script runs three different values.**
- The user asked for 1.5 ms. The authority contract says 0.8. The script writes the final contract's `test_value` of 5.0.
- In effect it re-runs a characterization experiment and labels it production proof.
- It uses DawDreamer `LiveBackend`, not Ableton or the native loader. It writes a `.SerumPreset` afterwards but never loads it.

**F7: Reference verification can be satisfied trivially.**
- Verified end to end: 300 acquired frames, **1 frame analysed** with 1 control (`env2.decay`), plus a **hand-typed** `{"route":"DIRECT_UI","values":{…}}` dict.
- Result: `LIVE_UI_VERIFIED`, `coverage=COMPLETE`, **`reference_verified=True`**.
- Three causes:
  - `stage_a_is_filled` uses `any()`.
  - Coverage is measured against what the census *wrote*, not against frames or controls actually present.
  - `ui_readback` is a self-declared dict, with no binding to the loaded plugin instance, the loader result, or a screenshot hash.

**F8: The UI comparison is sensitive to string format.**
- A video value of "300" with unit "ms" vs a UI reading of "300 ms" → MISMATCH, because `_ui_equal` compares units from `_numeric(x, None)`.
- This gives false negatives on real readbacks.

**F9: The orchestrator can never reach LIVE_UI_VERIFIED.**
- It returns `status: COMPLETE` even when the bridge is unavailable.
- It never feeds a UI readback back into `run_reference_reproduction`.
- Stage 2 raises `refusing to serialize` whenever 0 operations are admitted, which F1 makes the normal case.

**F10: There are two execution authorities / verification models.**
- The ProducerBrain Serum-preset route checks the final contract, but only when `atlas_id` is set. The natural-language path passes `atlas_id=None` and gets no gate at all.
- The `ABLETON_MCP` route ("Filter 1 cutoff 800 Hz" → `MCP_PLAN_READY`) never consults it.
- `reference_reproduction` / `state_admission` / `authorized_state_compiler` **never call `execution_spec()`**. Their gate is `EXECUTION_ELIGIBLE_BINDINGS`, which rejects `HOST_PARAMETER`, yet ProducerBrain plans on exactly such a contract (F5).

**F11: The 330-control evidence cannot be reproduced from this repo.**
- `bulk_causal/serum_backend.py` does `sys.path.insert(0, "D:/ableton claude")` and imports `bridge, codec, processor_state, vst3_state` from an unversioned older repo. Those modules were deleted here in commit `2547dd2`.
- It also monkeypatches `PROCESSOR_VERSION = 9.0`.
- The "live v3 sweep" is **headless DawDreamer**, not Ableton, not the MCP protocol, and not the native loader. The final contract and its report say "live MCP execution" and never mention DawDreamer.

**F12: Frame acquisition is neither exhaustive nor fail-safe.**
`acquire_visual_evidence`:
- samples by `ts` seek, one ffmpeg process per frame, starting at t=1.0, with no source frame index;
- silently `continue`s past failed extractions;
- truncates at **300 s** when duration is unknown;
- falls back silently to low-res storyboard sprites;
- **returns any cached `manifest.json` regardless of the requested `max_frames`/`interval`**, so an earlier 45 s × 8 run is reused as "exhaustive".
- The only real product run (WeRr68RBm8c) has 22 frames for about 415 s.

**F13: Legacy cloud fallback is still reachable.**
ProducerBrain with `source_url` and no `transcript_segments` falls back to `VisualReasoner` (Anthropic API, 45 s × 8 frames). The only trace is an `advisory_rationale` string. Visual is skipped entirely when the transcript is judged sufficient, so transcript-first becomes transcript-only there.

**F14: The boolean operand fix is not retroactive.**
The pickled legacy `oscillator_field_OSC-ENABLE` is still `mutate_numeric_value` with value 0.0. The fix (commit `2aacf73`) applies only to newly built contracts.

**F15: 2.0.21 residue is live, not just in docs.**
- The Atlas says `SERUM_VERSION="2.0.21"`, and its "2.0.21 snapshot" is really serum-mcp's static schema.
- `production_pipeline.py:684` instructs "must be 2.0.21".
- The defaults in `reference_state_reconstructor`/`phase4_2_verified_state_adapter` are "2.0.21".
- `youtube_to_serum/main.py` and the README say "2.0.21", "exhaustive", and "local model analyzes each frame".
- `IMPLEMENTATION_STATUS.md` and the root README are the only honest-ish status docs, and their test counts are stale.

**F16: The test suite doesn't catch any of the above.**
- Full suite at `2f7acb3` (cloud, with pillow/pydantic/cbor2 installed): **1223 passed, 25 failed, 22 errors**. The failures and errors are environment-bound (Windows Serum binary, serum-mcp availability).
- F1–F7 all coexist with a mostly green suite. The integration tests run on `epoch=None` or call `admit()` directly, so they never exercise the real 2.0.23 end-to-end path.

---

## §3. Items Verified as OK or Resolved

- **Duplicate `youtube_to_serum/serum2`:** removed in `b86547a`. Only a stray `pathmerge.py` remains, with no `__init__`, so imports resolve to the root `serum2`. Divergence risk is low; delete the stub.
- **Genuine `.SerumPreset`:** the production paths use `serum_mcp.generate_preset` / `pack_file`. `serum2/codec.py` is a second encoder, but only the bulk harness uses it. The legacy `authorized_preset_compiler.py` (P6 fixed-FX constants) is test-only.
- **Loader:** `create_serum_track` checks the SHA of the `Serum2.vst3` **mapped into Live's process**. It reports only `LOADED_VISUAL` and never claims VERIFIED. It rolls back by nonce.
- **Unreadable handling:** an unreadable last reading is never replaced by an older value (`STALE_RISK_LAST_KNOWN_NOT_USED`). Transient tooltip route amounts → UNREADABLE (Q19 is OK).
- **Qwen:** there is a strict exact-match scorer (commit `80e5183`), but it covers only **5 hand-picked crops**. It is not a value-accuracy benchmark, and Qwen/observation_engine is not wired into any product path.

---

## §4. The 20 Conformance Exceptions: None Reclassified, Root Cause for Each

| Class | Controls | Evidence | Status |
|---|---|---|---|
| Domain too wide | arp.transpose.range | wrote 16, stored 8 | Unqualified; executable within ±8 after re-qualification |
| Unit/scale schema mismatch | fx.compressor.attack, ratio, release | raw persists; display mapping ≠ serum-mcp schema | Unqualified; fixable with measured mapping |
| Vocabulary mismatch | global.fx_bus1/2_destination | raw persists; raw 1.0 = DIRECT, 2.0 = BUS 1 | Unqualified; fixable with value alias table |
| Display off-by-one | mixer.noise.pan, mixer.sub.pan, oscNoise.pan (alias) | raw persists; screen and host show −19 L for −20 | Mapping unknown; raw write OK |
| Display curve unknown | oscA.warp_amount | raw persists, monotonic; Sync display curve unresolved | Can't invert video % → raw |
| Write dropped | macro1-8.name | post=None | MCP writes the wrong or unrepresented path; needs GUI save+diff |
| Not a preset field | global.use_ultra_on_render | app preference, not persisted | Genuinely non-executable |
| No UI in 2.0.23 | global.voice_priority | raw persists 'Low'; no control found | Executable raw, unverifiable |

---

## §5. Answers to Q1–Q20

- **Q1 (more than one execution authority?):** Yes. There are two independent models (F10), plus a third, divergent authority design on `quirky-franklin`.
- **Q2 (can the final-contract gate be bypassed?):** Yes: the whole reference path, the NL path with `atlas_id=None`, and the `ABLETON_MCP` route.
- **Q3 (can capability/admission be bypassed?):** Not in the reference path; the compiler re-validates. In the ProducerBrain path, admission authority is real, but the value it carries is the test value (F4).
- **Q4 (can 2.0.21 evidence reach a 2.0.23 runtime?):** Yes, with `epoch=None` (F5), which `CREATE` falls back to whenever `installed_epoch()` throws.
- **Q5 (can an incomplete Stage-A enter the ledger?):** Yes; demonstrated (F7).
- **Q6 (can a hallucinated VLM value be compiled?):** Yes. Any in-domain value marked `OBSERVED` compiles; one reading suffices; there is no confidence or corroboration requirement.
- **Q7 (can transcript inference create a value?):** In the reference path, no. In the ProducerBrain path the transcript drives intent, but the value comes from the contract's test value, which is arguably worse.
- **Q8 (does any PASS ignore value correctness?):** The Qwen scorer is fixed, but at n=5. The `0c94f58` heuristic scripts remain in the repo root and would mislead if reused.
- **Q9 (is HOST_CONFIRMED overstated?):** Yes, partially. `HOST_CONFIRMED` means a **DawDreamer** host-text change, and the "live" wording overstates it. It is not Direct UI.
- **Q10 (can raw persistence be mistaken for native behavior?):** Yes. `RAW_ONLY` and restoration evidence come from DawDreamer re-saved state, and `DIRECT_UI_FINDING` shows DawDreamer echo ≠ native load behavior.
- **Q11 (can a fake/synthetic preset reach production?):** No, not in production paths.
- **Q12 (does `epoch=None` disable a critical check?):** Yes, `execution_spec()` epoch filtering (F5).
- **Q13 (are 330-control conclusions built on stale 2.0.21 artifacts?):** The sweep itself is 2.0.23-stamped. Its domains and Atlas identity come from the "2.0.21" serum-mcp schema, and several of those domains are proven wrong.
- **Q14 (are the 20 exceptions truly impossible?):** Only 1–2 are (see §4); the rest are unqualified.
- **Q15 (does the product branch hold a divergent core copy?):** No longer.
- **Q16 (can the two paths disagree?):** Yes: on value, epoch, eligible binding types, and gate.
- **Q17 (is every source frame analysed?):** No (F12).
- **Q18 (can tooltip-only values be captured?):** Not automatically. There are dense 10 fps windows for one video only, and the tooltip-derived route amounts are forced `UNREADABLE`.
- **Q19 (can unreadable observations retain an older value?):** No.
- **Q20 (can a terminal conclusion be mistaken for executable?):** Yes. "330 terminal" became "310 executable" in reports, but the runtime has 221 loaded and 10 reachable.

The 16-bar Ableton gate is untouched since R1 (`a91f48c`): the only real render was digital silence, and arrangement clips don't trigger. It is unresolved.

---

## How to Reproduce These Findings

Requirements:
```bash
pip install pydantic cbor2 zstandard pillow numpy
export SERUM_PRESETS_PATH=/tmp/serum_fake_presets
mkdir -p $SERUM_PRESETS_PATH
```

Run from a worktree of `2f7acb3` (before any of the fixes land):
```bash
git worktree add /tmp/audit-tip 2f7acb3
cd /tmp/audit-tip
python audit/probes/probe1.py   # F4/F5: qualification-value substitution + epoch=None leak
python audit/probes/probe2.py   # F1/F2/F3: pathless contracts, MISSING_DOMAIN, macro crash
python audit/probes/probe3.py   # F7: 1-of-300-frame census → reference_verified=True
python audit/probes/probe4.py   # F4/F5: value substitution under 2.0.23 epoch simulation
```

Each probe script is self-contained and prints pass/fail evidence for its claims.
