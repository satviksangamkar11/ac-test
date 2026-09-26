# Residual controls — exact steps, no guessing

3 items left that no preset can carry: they need you to change something in Serum's GUI, save, and read the
raw value back from the file. A script does the reading for you — you never need to know or guess a raw key
name.

For every step below: start from Serum's own **Init** preset (the factory blank patch, not one of ours),
make ONE change, save the result as a NEW file in `BULKCAUSAL_VERIFY/` with the filename given, then run:

```
python readback_diff.py <path to Init.SerumPreset> <path to the file you just saved>
```

`Init.SerumPreset` is Serum's own factory default — use whatever file/menu entry Serum itself calls "Init"
or "Default". If you're not sure which file that is on disk, ask before proceeding rather than guessing.

The script prints every raw key that changed and its new value. Copy that output into
`RESIDUAL_results.json` (format at the bottom) exactly as printed — don't interpret it.

## 1. `arp.transpose.shape` — 3 remaining labels

15 of 18 labels are already resolved offline (see `residual_arp_transpose_shape_v1.json`) — you do NOT need
to touch these 15. Only these 3 need a save/readback, because they don't exist in the schema's known
vocabulary at all:

- **Up**
- **Pinky Up**
- **Pinky UD**

Steps, once per label:
1. Load Init.
2. Open the ARP panel → TRANSPOSE tab (the same tab session-1 used to read the 18 labels).
3. Set the transpose SHAPE dropdown to the label (e.g. "Up").
4. Save as `BULKCAUSAL_VERIFY/RESIDUAL_ARP_TRANSPOSE_UP.SerumPreset` (name it after the label: `_PINKY_UP`,
   `_PINKY_UD` for the other two).
5. Run `readback_diff.py` against Init. Expect exactly one leaf to differ, at
   `["ArpClip0", "plainParams", "kParamTransposeShape"]`. Record its new raw string value.

## 2. `global.voice_priority` — find the control, then enumerate it

We do not know where this control is on screen. Its only known trace is the schema field's own
description: "voice-stealing priority, only 'Low' observed". Likely candidates to check, in order:
- GLOBAL page, near VOICING/POLY settings.
- The VOICING strip at the bottom of the window (near MONO/POLY/LEGATO), possibly under a right-click or a
  small dropdown you haven't opened yet.
- Ableton Live's own per-track voice settings are NOT it — this is a Serum-internal control.

Once found:
1. Load Init.
2. Note every label the dropdown offers (there are probably 2-4: e.g. Low/Normal/High, or Oldest/Newest).
3. For EACH label, set it, save as `BULKCAUSAL_VERIFY/RESIDUAL_VOICE_PRIORITY_<LABEL>.SerumPreset`
   (e.g. `_LOW`, `_HIGH`), and run `readback_diff.py` against Init.
4. If you cannot find any control matching "priority" after checking GLOBAL and the voicing strip once
   each, stop and report `NOT_LOCATED` — don't keep searching page by page.

## 3. `global.use_ultra_on_render` — one toggle

1. Load Init.
2. On the GLOBAL page, find the render-quality area (near OVERSAMPLING/QUALITY). Toggle whatever looks like
   "Ultra on render" / "high quality on bounce" ON.
3. Save as `BULKCAUSAL_VERIFY/RESIDUAL_ULTRA_RENDER.SerumPreset`.
4. Run `readback_diff.py` against Init.
5. If NOTHING differs (the script prints "NO DIFFERENCE"), that itself is the finding — Serum may not
   persist this setting into the preset file at all. Record that outcome; don't retry.

## Output format

One line per attempt in `RESIDUAL_results.json`:

```json
{"item": "arp_transpose_shape_Up", "diff": [{"path": ["ArpClip0","plainParams","kParamTransposeShape"], "value": "..."}]}
{"item": "voice_priority_Low", "diff": [{"path": ["Global0","plainParams","kParamVoicePriority"], "value": "Low"}]}
{"item": "use_ultra_on_render", "diff": []}
{"item": "voice_priority_control", "result": "NOT_LOCATED"}
```

Commit `RESIDUAL_results.json` (and any saved preset files, if you want them kept) and push to
`claude/direct-ui-rescan-2026-09-26`.
