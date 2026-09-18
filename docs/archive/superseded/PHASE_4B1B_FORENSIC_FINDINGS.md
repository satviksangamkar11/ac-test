# PHASE 4B.1B — FORENSIC ANALYSIS: V8/VC2! STATE TRANSPORT

**Analysis date:** 2026-09-18  
**Repository:** D:\ableton claude final best

---

## 1. V8 STATE PIPELINE

**Complete infrastructure exists:**

```
capture_v8_skeleton() [serum2/bridge.py:15]
  -> Fresh Serum instance via DawDreamer
  -> save_state() -> binary state blob
  -> unwrap_vc2() -> XferJson bytes
  -> decode() -> (meta8, body8)
  
build_v8_state(preset_path, skeleton) [serum2/bridge.py:36]
  -> load_preset_file() -> (meta5, body5)
  -> Overlay v5 onto v8 skeleton
  -> Returns (meta8', body8', transplanted_modules)

state_hash(meta8, body8) [serum2/bridge.py:60]
  -> SHA256 of encoded state (first 16 chars)
  -> Proves mutation actually changed bytes

write_state_file(path, meta8, body8) [serum2/bridge.py:53]
  -> codec.encode() -> XferJson bytes
  -> vst3_state.wrap_vc2() -> VC2! blob
  -> Write to disk as .bin file
```

**Status: COMPLETE** — All pipeline steps exist and are functional.

---

## 2. EXISTING TRANSPORT MECHANISMS

### A. VC2! Format Universal Claim

From vst3_state.py line 19-20:
```
"matching the structure of Serum's own save_state() output exactly
(verified byte-for-byte on 2.0.21)"
```

**This is significant:** The VC2! state is NOT a DawDreamer-specific format.
It is Serum's NATIVE VST3 state format.

**Key implication:** Any VST3 host (including Ableton) should theoretically be able to accept this blob.

### B. Codec Support for Both v5 and v8

codec.py line 6-8:
```
- .SerumPreset files      (meta.version == 5.0, no "component" field)
- VST3 processor state    (meta.version == 8.0 on Serum 2.0.21, meta.component == "processor")
Both share this exact container; only the JSON meta and CBOR body schemas differ.
```

**Implication:** The same XferJson container format serves both:
- v5: .SerumPreset (Serum's own preset format)
- v8: VST3 processor state (Serum's native plugin state)

---

## 3. SERUMPRESET TRANSPORT PATH

**Question:** Can we convert mutated V8 state back into a .SerumPreset?

**Available functions:**
- codec.load_preset_file(path) — reads .SerumPreset
- codec.dump_preset_file(path, meta, body, mode=2) — writes .SerumPreset
- codec.encode(meta, body) — encodes to XferJson bytes

**Can it work?**

Yes, theoretically:
```
1. Start with original .SerumPreset
2. Convert to V8 via build_v8_state()
3. Mutate V8 body via pathmerge
4. Create v5 meta from v8 meta (downgrade version field)
5. codec.dump_preset_file() -> write mutated .SerumPreset
```

**But this requires:**
- Downgrading meta.version from 8.0 to 5.0
- Removing meta.component field
- Ensuring all v5 body fields are present

**Status: POSSIBLE but UNPROVEN** — Code exists but roundtrip has never been tested.

---

## 4. ABLETON MCP STATE TRANSPORT

**Current MCP tool surface:**

| Tool | State loading? | Notes |
|------|---|---|
| load_instrument_or_effect() | NO | Loads device definition (URI), not state |
| set_device_parameter() | NO | Sets wrapper parameters only ("Device On") |
| write_automation() | NO | Sets automation, not plugin state |
| [Any preset loading tool] | NO | Does not exist |
| [Any state loading tool] | NO | Does not exist |

**Documented by Phase 4B.1 control gate investigation.**

**Status: NOT_AVAILABLE** — No MCP tool for plugin state injection.

---

## 5. UI / HOST AUTOMATION

**Searched repository for existing UI automation:**

Candidates checked:
- Playwright — not found
- pywinauto — not found
- AutoHotkey — not found
- accessibility APIs — not found
- Ableton Live Python API — deprecated (Python 2.7)
- Serum UI scripting — not exposed

**Status: NOT_AVAILABLE** — No existing automation mechanism in repository.

---

## 6. Q7/Q9 REUSABILITY

**Question:** Did previous Q7/Q9 work establish a processor-state injection path?

**Search result:**
- No Q7/Q9 documentation found in current canonical repository
- PHASE_4B0_EXECUTION_REPORT.md mentions exclusion of Q7/Q9 work
- No evidence of previous Ableton↔VST3 state bridge

**Note from EXCLUDED_SOURCE_MANIFEST.json:**
Q7/Q9 work is explicitly NOT in this canonical repository.

**Status: NOT_AVAILABLE_FOR_INSPECTION** — Previous work is excluded.

---

## 7. EXACT REMAINING GAP

**The infrastructure is complete except for the final delivery:**

```
DawDreamer Mutation Layer:
  [WORKS] capture_v8_skeleton() -> (meta8, body8)
  [WORKS] build_v8_state(preset, skeleton) -> (meta8', body8')
  [WORKS] state_hash(meta8', body8') -> verification
  [WORKS] codec.encode() -> XferJson bytes
  [WORKS] vst3_state.wrap_vc2() -> VC2! blob
  [WORKS] write to disk -> state.bin

                          [GAP]

Ableton-Hosted Serum:
  [MISSING] load_plugin_state(track, device, state.bin)
  [MISSING] Ableton MCP tool for plugin state injection
  [MISSING] VST3 host API exposure through MCP
  [MISSING] Serum preset loading through MCP
  [MISSING] UI automation for preset browser
```

**The VC2! blob is correctly formatted and Serum understands it,**
**but there is NO MECHANISM to PRESENT the blob to the running instance**
**from outside the plugin's own user interface.**

---

## 8. CONCLUSION

**The V8/VC2! state infrastructure is ISOLATED from Ableton-hosted Serum.**

The pipeline works end-to-end EXCEPT at the critical junction:
getting the state from disk into the running plugin instance inside Ableton.

### Three theoretical paths:

**PATH A: Ableton MCP state tool** (most direct)
- Required: `load_plugin_state(track_index, device_index, state_file_path)` MCP tool
- Status: DOES NOT EXIST
- Would work if implemented

**PATH B: Serum preset roundtrip** (requires downgrade)
- Convert V8 state -> v5 .SerumPreset
- Requires: MCP tool to load preset into device
- Status: PRESET LOADING TOOL DOES NOT EXIST
- Would work if tool existed and preset roundtrip is sound

**PATH C: .SerumPreset file system**
- Write mutated .SerumPreset to Serum's default preset directory
- Serum user clicks "Load" in UI
- Manual operation, not automation

### Recommended next step:

**Do not proceed with Phase 4B.2 (16-bar production)** until one of these paths is resolved:

1. Implement/acquire `load_plugin_state()` MCP tool, OR
2. Implement Serum preset loading through MCP + verify v8-to-v5 roundtrip, OR
3. Escalate to Ableton/xFer Records for API access

**Current state:**
- DawDreamer Serum mutations: PROVEN
- Ableton MCP rendering: PROVEN
- State transport into Ableton-hosted Serum: BLOCKED
