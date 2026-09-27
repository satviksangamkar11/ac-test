# W1 Windows Runbook

**Purpose:** Gate B (first native Serum verification) + VLM ground-truth capture + R1 silence diagnosis.  
**Requires:** Windows machine with Serum 2.0.23 VST3, Ableton 11.3, serum-mcp running, `SERUM_PRESETS_PATH` set.

---

## Gate B vocabulary

Two separate paths reach Gate B. They are NOT equivalent and must NOT be collapsed:

| Path | Terminal vocabulary | When to use |
|---|---|---|
| ProducerBrain intent path | `execution_status == "EXECUTED"` + `decision == "ACCEPTED"` | User says "set Env2.Decay to 5.0 s" |
| ReferenceReproductionRun path | `run.proof_level == "LIVE_UI_VERIFIED"` | Video stage-A reconstruction |

`proof_level` is a property of `ReferenceReproductionRun` only — it does NOT exist on `ProducerResult`.
`execution_status == "EXECUTED"` is a field of `ProducerResult` only — it does NOT exist on `ReferenceReproductionRun`.

The machine-checkable Gate B certificate (`serum2.producer.gate_b_certificate`) uses the ProducerBrain path vocabulary.
`CANONICAL_GATE_B_VERIFIED` requires: `execution_status == "EXECUTED"` AND `decision == "ACCEPTED"` AND `admitted == True`
AND `serum_preset_execution.ui_readback.loader_evidence.serum_module_sha256 == epoch.binary_sha256`.

---

## Prerequisites

1. Serum 2.0.23 installed: `C:\ProgramData\Steinberg\VST3\Serum2.vst3`
2. Ableton 11.3 open with the serum-mcp bridge active on port 8765
3. `SERUM_PRESETS_PATH` environment variable set to the Serum presets folder
4. Repo checked out at `claude/gallant-cerf-u953wn`, Gate A changes committed

Verify epoch before starting:

```python
from serum2.producer.execution_epoch import installed_epoch
e = installed_epoch()
assert e.binary_sha256 == "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3", e
print("Epoch OK:", e.label)
```

---

## Step 1 — Gate B: env2.decay canonical path (ProducerBrain intent path)

`env2.decay` is a Pass-1 contract reachable under EPOCH_2_0_23 via the ProducerBrain intent path.
This run produces Cert 2 using `finalize_serum_preset_execution()`.

**Note on operand:** The plan carries `qualification_test_value` (e.g. 0.5 s — the value the binding
test used). This is EVIDENCE METADATA. The production operand is the user's requested value (e.g. 5.0 s)
extracted from the intent. Never use `qualification_test_value` as the operand when building the preset.

### 1a. Get the admitted plan

```python
from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest

brain = ProducerBrain(epoch=EPOCH_2_0_23,
                      binding_evidence_dir="serum2/qualification/binding_evidence",
                      promoted_evidence_dir="parameter_characterization/binding_evidence_mcp_exec_v1")
result = brain.execute(ProducerRequest(
    user_intent="set Env2.Decay to 5.0 seconds",
    semantic_target="Env2.Decay"))
assert result.execution_status == "ADVISORY_ONLY", result.execution_status
assert result.admitted is True, result.admission_reason

plan = result._serum_preset_plan
print("target path:", plan["mutation_target_path"])
print("qualification_test_value (METADATA ONLY):", plan["qualification_test_value"])
# PRODUCTION OPERAND = 5.0 (from user intent) — NOT qualification_test_value
```

### 1b. Build and write the preset with the REQUESTED value (5.0 s)

```python
# Use the production operand (5.0 s) from the user intent — NOT plan["qualification_test_value"]
# Build the preset at plan["mutation_target_path"] with value = 5.0
# (use serum_mcp generate_preset or equivalent)
# Save to a .SerumPreset file and compute its SHA-256:
import hashlib
preset_path = "tests/fixtures/gate_b/env2_decay_5s.SerumPreset"
preset_sha256 = hashlib.sha256(open(preset_path, "rb").read()).hexdigest()
```

### 1c. Load preset into Serum via serum-mcp

```python
from serum2.server.serum_loader import create_serum_track
load_result = create_serum_track(preset_path, epoch=EPOCH_2_0_23)
assert load_result.load_status in ("LOADED_VISUAL", "LOADED_CONFIRMED"), load_result
assert load_result.loaded_module_sha256 == EPOCH_2_0_23.binary_sha256, (
    "Module SHA mismatch: %s != %s" % (load_result.loaded_module_sha256, EPOCH_2_0_23.binary_sha256))
print("Loaded. Track nonce:", load_result.track_nonce)
print("Module SHA:", load_result.loaded_module_sha256)
```

### 1d. Take the bound screenshot + UI readback

With the preset loaded in Serum's DIRECT UI inside Ableton:
1. Switch to the ENV2 panel
2. Screenshot (Win+Shift+S) the full Serum plugin window → save to `tests/fixtures/gate_b/env2_decay_readback.png`
3. Hover over the Decay knob to expose tooltip value → record in the readback dict:

```python
import hashlib
screenshot_path = "tests/fixtures/gate_b/env2_decay_readback.png"
screenshot_sha256 = hashlib.sha256(open(screenshot_path, "rb").read()).hexdigest()

ui_readback = {
    "route": "DIRECT_UI",
    "values": {
        "env2.decay": "5.00 s",   # exact value read from Serum UI tooltip
    },
    "method": "manual_screenshot",
    "screenshot_sha256": screenshot_sha256,
    "loader_evidence": {
        "run_id": load_result.run_id,
        "track_nonce": load_result.track_nonce,
        "serum_module_sha256": load_result.loaded_module_sha256,
    },
}
# readback_verified = True iff the UI value matches the requested 5.0 s
readback_verified = True  # confirm manually: UI shows 5.00 s
```

### 1e. Finalize and get Gate B certificate

```python
brain.finalize_serum_preset_execution(
    result,
    preset_path=preset_path,
    preset_sha256=preset_sha256,
    ui_readback=ui_readback,
    readback_verified=readback_verified,
)
assert result.execution_status == "EXECUTED", result.execution_status
assert result.decision == "ACCEPTED", result.decision

from serum2.producer.gate_b_certificate import gate_b_certificate, gate_b_verified
cert = gate_b_certificate(result, epoch=EPOCH_2_0_23)
assert gate_b_verified(cert), (
    "Gate B not verified: %r" % cert["gate_b_status"])
assert cert["gate_b_status"] == "CANONICAL_GATE_B_VERIFIED"
print("Gate B status:", cert["gate_b_status"])
print("DawDreamer used:", cert["dawdreamer_used"])        # must be False
print("Headless used:", cert["headless_substitution_used"])  # must be False
```

### 1f. Save Cert 2 to fixture

```python
import json
with open("tests/fixtures/gate_b/cert2.json", "w") as f:
    json.dump(cert, f, indent=2)
print("Cert 2 saved:", cert["gate_b_status"])
```

Also save: native re-save (Serum → File → Save As → `tests/fixtures/gate_b/env2_decay_native_resave.fxp`).

Commit `tests/fixtures/gate_b/` (screenshots, preset, cert2.json) for offline CI replay.

---

## Step 2 — VLM ground-truth capture

This produces labelled crops for the C2 benchmark (later used by C3 Qwen evaluation).

### 2a. Load `CAL_*` / `BULK_*` presets

These presets have known, unique values per control. Load them one by one into real Serum 2.0.23:

```python
import os
from pathlib import Path
presets_dir = Path(os.environ["SERUM_PRESETS_PATH"]) / "calibration"
for preset_path in sorted(presets_dir.glob("CAL_*.fxp")):
    result = create_serum_track(str(preset_path), epoch=EPOCH_2_0_23)
    assert result.load_status in ("LOADED_VISUAL", "LOADED_CONFIRMED")
    # Screenshot every visible panel (OSC, ENV1-6, LFO, FILTER, FX, MATRIX, ARP, GLOBAL)
    # Save labelled JSON: {control_id: {"value": <displayed>, "unit": <unit>, "crop_sha256": <sha>}}
```

### 2b. Screenshot format

For each panel page:
1. Navigate to the panel (OSC, ENV1, etc.)
2. Hover each knob/slider to expose the tooltip value
3. Screenshot the full plugin window
4. Record in `parameter_characterization/vlm_ground_truth/<preset_name>_<panel>.json`:

```json
{
  "env2.decay":    {"value": "650",   "unit": "ms",  "crop_sha256": "..."},
  "env2.sustain":  {"value": "0",     "unit": "dB",  "crop_sha256": "..."},
  "env2.release":  {"value": "200",   "unit": "ms",  "crop_sha256": "..."}
}
```

### 2c. Commit ground-truth crops

```
git add parameter_characterization/vlm_ground_truth/
git commit -m "W1: VLM ground-truth labelled crops from CAL_ presets on Serum 2.0.23"
```

---

## Step 3 — R1 Silence Diagnosis

The 16-bar render produces digital silence (established at a91f48c). Diagnose root cause.

### 3a. Create a stock instrument track

```python
# In Ableton: New MIDI track → add Serum 2 VST3 → load "Massive Bass" or any factory preset
# Do NOT use the reference preset from Step 1 — use a factory preset with guaranteed audio
```

### 3b. Create a 4-bar MIDI clip

In Arrangement view:
- Draw MIDI notes (C3, velocity 100, 1 bar each) in bars 1-4
- Verify the track plays audio in real time (listen in Session view first)

### 3c. Render and check

```python
import subprocess
result = subprocess.run(
    ["python", "-m", "serum2.server.render_track", "--bars", "4", "--output", "/tmp/test_render.wav"],
    capture_output=True, text=True
)
print(result.stdout, result.stderr)
# Then check audio level:
import soundfile as sf
data, sr = sf.read("/tmp/test_render.wav")
print("Peak level:", data.max())  # must be > 0.001
```

### 3d. Diagnose if silent

Known candidates (from audit §F16):
- Arrangement clip does not trigger in `create_serum_track` render path (uses Session mode)
- MIDI routing is Session → no signal in Arrangement render
- Fix: switch render to use Arrangement clips, not Session clips

Document findings in `tests/fixtures/gate_b/r1_silence_diagnosis.md`.

---

## Step 4 — Commit Windows Evidence

```bash
git add tests/fixtures/gate_b/
git add parameter_characterization/vlm_ground_truth/
git commit -m "W1: Gate B Cert 2 evidence + VLM ground-truth crops + R1 diagnosis"
git push origin claude/gallant-cerf-u953wn
```

---

## Acceptance Criteria (Gate B / Cert 2)

ProducerBrain intent path (canonical):
- [ ] `result.execution_status == "EXECUTED"` (from `finalize_serum_preset_execution`)
- [ ] `result.decision == "ACCEPTED"`
- [ ] `result.admitted == True`
- [ ] `cert["gate_b_status"] == "CANONICAL_GATE_B_VERIFIED"` (from `gate_b_certificate()`)
- [ ] `cert["loaded_module_sha256"] == EPOCH_2_0_23.binary_sha256`
- [ ] `cert["dawdreamer_used"] == False`
- [ ] `cert["headless_substitution_used"] == False`
- [ ] `cert["qualification_test_value"] != requested production value` (operand boundary)
- [ ] `cert2.json` committed to `tests/fixtures/gate_b/`
- [ ] No DawDreamer anywhere in the chain (verify: `grep -r DawDreamer tests/fixtures/gate_b/`)
- [ ] R1 diagnosis documented

**Do not use `proof_level == "LIVE_UI_VERIFIED"` to check the ProducerBrain path.**  
`proof_level` is a property of `ReferenceReproductionRun` (video reconstruction path) — it does
not exist on `ProducerResult`. The canonical ProducerBrain path uses `execution_status == "EXECUTED"`
and `decision == "ACCEPTED"`.

The next step after W1 is C3 (local VLM benchmark against the captured ground truth).
