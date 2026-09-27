# W1 Windows Runbook

**Purpose:** Gate B (first native Serum verification) + VLM ground-truth capture + R1 silence diagnosis.  
**Requires:** Windows machine with Serum 2.0.23 VST3, Ableton 11.3, serum-mcp running, `SERUM_PRESETS_PATH` set.

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

## Step 1 — Gate B: env2.decay canonical path (first real native proof)

`env2.decay` is a Pass-1 contract already reachable under EPOCH_2_0_23. This run produces Cert 2.

### 1a. Run reference reproduction

```python
from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.server.reference_reproduction import run_reference_reproduction

run = run_reference_reproduction(
    "tests/fixtures/reference_reproduction/stage_a_observation.json",
    "tests/fixtures/reference_reproduction/reread_log.json",
    "tests/fixtures/reference_reproduction/stage_a_corrections.json",
    source={"video_id": "HEEGN1Xl5o4"},
    name="gate-b-env2-decay",
    epoch=EPOCH_2_0_23,
    ui_readback=None,   # file-readback only until Step 1c
    subfolder="gate_b",
)
assert run.compilation["admitted"] > 0, "no operations compiled"
print("preset:", run.preset["path"])
```

### 1b. Load preset into Serum via serum-mcp

```python
from serum2.server.serum_loader import create_serum_track
result = create_serum_track(run.preset["path"], epoch=EPOCH_2_0_23)
assert result.load_status in ("LOADED_VISUAL", "LOADED_CONFIRMED"), result
print("Loaded. Track nonce:", result.track_nonce)
print("Module SHA:", result.loaded_module_sha256)
```

Assert `result.loaded_module_sha256 == EPOCH_2_0_23.binary_sha256`.

### 1c. Take the bound screenshot + UI readback

With the preset loaded in Serum's DIRECT UI inside Ableton:
1. Switch to the ENV2 panel
2. Screenshot (Win+Shift+S) the full Serum plugin window → save to `tests/fixtures/gate_b/env2_decay_readback.png`
3. Hover over each visible knob to expose tooltip values → record in the readback dict:

```python
ui_readback = {
    "route": "DIRECT_UI",
    "values": {
        "env2.decay": "<value_from_ui>",   # e.g. "650 ms"
    },
    "method": "manual_screenshot",
    "screenshot_sha256": "<sha256_of_the_png>",
    "serum_load_result": {
        "track_nonce": result.track_nonce,
        "loaded_module_sha256": result.loaded_module_sha256,
    },
}
```

### 1d. Re-run with the bound readback

```python
run_verified = run_reference_reproduction(
    "tests/fixtures/reference_reproduction/stage_a_observation.json",
    "tests/fixtures/reference_reproduction/reread_log.json",
    "tests/fixtures/reference_reproduction/stage_a_corrections.json",
    source={"video_id": "HEEGN1Xl5o4"},
    name="gate-b-env2-decay-verified",
    epoch=EPOCH_2_0_23,
    ui_readback=ui_readback,
    subfolder="gate_b",
)
assert run_verified.proof_level == "LIVE_UI_VERIFIED", run_verified.proof_level
```

### 1e. Save Cert 2 fields to fixture

```python
import json
cert2 = {
    "serum_binary_sha256": EPOCH_2_0_23.binary_sha256,
    "preset_sha256": run_verified.preset["sha256"],
    "loaded_module_sha256": result.loaded_module_sha256,
    "proof_level": run_verified.proof_level,
    "coverage_status": run_verified.coverage_status,
    "ui_readback_binding": ui_readback["serum_load_result"],
}
with open("tests/fixtures/gate_b/cert2.json", "w") as f:
    json.dump(cert2, f, indent=2)
print("Cert 2:", cert2)
```

Commit `tests/fixtures/gate_b/` (screenshots, preset .fxp, cert2.json) for offline CI replay.

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

- [ ] `run_verified.proof_level == "LIVE_UI_VERIFIED"`
- [ ] `result.loaded_module_sha256 == EPOCH_2_0_23.binary_sha256`
- [ ] `cert2.json` committed to `tests/fixtures/gate_b/`
- [ ] No DawDreamer anywhere in the chain (verify: `grep -r DawDreamer tests/fixtures/gate_b/`)
- [ ] R1 diagnosis documented

The next step after W1 is C3 (local VLM benchmark against the captured ground truth).
