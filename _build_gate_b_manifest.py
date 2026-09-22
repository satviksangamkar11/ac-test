import json, hashlib
from pathlib import Path

def sha256_of(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

manifest = {
    "benchmark_version": "roi-v1-gateB-audit",
    "audit_method": "Each source image and crop was independently re-opened and visually inspected by the auditing model in this session, without assuming the existing JSON/filenames/prompts were complete or correct. Findings below are direct pixel observations, cross-checked against five_roi_test_results.json (commit 80e5183).",
    "entries": []
}

entries_data = [
    dict(
        test_id=1, canonical_id="oscA.unison",
        source_path="video_screenshots/HEEGN1Xl5o4/step2_03m14s_filter_mg18_setup.jpg",
        source_size=(1280,720), bbox=[100,270,175,300],
        crop_path="t1_unison.png", crop_size=(300,120),
        observation_kind="CONTROL",
        ground_truth={"value": "7", "visual_state": "checkbox_na", "notes": "Numeric stepper readout, unison voice count"},
        prompt_text="Read only the target control in this crop.\n\nTarget: OSC A Unison\nReturn exactly:\nVALUE=<visible text>\nor\nUNREADABLE=<reason>\n\nDo not infer. Do not convert units. Do not use information outside the crop.",
        capture_audit={
            "text_captured": True, "visual_state_captured": False, "shape_captured": False,
            "missing_observable_state": [
                "OSC A waveform shape (sawtooth line rendered in the wavetable display, visible directly above this crop bbox in the source frame) is a distinct visual observable, not represented by the OCT/SEM/FIN/Unison text alone",
                "OCT=-1, SEM=0, FIN=0 text values (visible in source frame just above this bbox, not included in this crop, not scored by any of the 5 tests)",
                "OSC A wavetable name 'Default Shapes' and WT POS knob value (visible in source frame, not scored)"
            ],
            "status": "PARTIAL"
        },
        source_notes="Assigned target (Unison=7) correctly captured. Same source frame contains OSC A waveform shape and adjacent numeric fields that are outside this crop's bbox and unscored by the current 5-test benchmark."
    ),
    dict(
        test_id=2, canonical_id="matrix.row[Env2-to-Filter1Freq]",
        source_path="video_screenshots/HEEGN1Xl5o4/step3_04m35s_matrix_mod_routes.jpg",
        source_size=(1280,720), bbox=[40,222,460,240],
        crop_path="t2_matrix_row.png", crop_size=(1260,54),
        observation_kind="ROUTE",
        ground_truth={"value": {"SOURCE":"Env 2","DESTINATION":"Filter 1 Freq"}, "visual_state": "amount_slider_present_unread", "notes": "Amount magnitude deliberately excluded from this test's scope"},
        prompt_text="This is one row of a modulation matrix table with three columns: source, amount slider, destination.\nReturn exactly:\nSOURCE=<text>\nDESTINATION=<text>\nDo not infer amount. Do not use information outside the crop.",
        capture_audit={
            "text_captured": True, "visual_state_captured": False, "shape_captured": False,
            "missing_observable_state": [
                "Modulation AMOUNT value for this route: encoded ONLY as slider-fill length plus handle position, zero text or numeric representation exists anywhere in this row. Current test explicitly excluded this by design ('do not infer amount'), but no observation modality for it has been tested at all. OCR cannot recover it; would require pixel-position-to-value calibration against known slider geometry.",
                "Bipolar/unipolar toggle icon next to the slider (small circular icon, state not inspected)",
                "The other 4 rows visible in the same Matrix table (LFO1 to A Fine, LFO1 to B Fine, Env3 to Noise Level, Env4 to unset) were visually inspected earlier in this session but are not part of this 5-test benchmark at all"
            ],
            "status": "PARTIAL"
        },
        source_notes="Assigned target (Source/Destination text) correctly captured. The row's actual modulation depth, arguably the most important value in a mod-matrix row, is not captured by any current observation modality, by explicit test design, not by oversight of this particular test. That gap should be tracked, not left implicit."
    ),
    dict(
        test_id=3, canonical_id="lfo1.mode",
        source_path="video_screenshots/HEEGN1Xl5o4/step2_02m08s_lfo1_lorenz_full_pattern.jpg",
        source_size=(1280,720), bbox=[385,370,460,385],
        crop_path="t3_lorenz.png", crop_size=(450,90),
        observation_kind="SELECTOR",
        ground_truth={"value": "Chaos: Lorenz", "visual_state": "WAVEFORM_SHAPE_OBSERVED", "notes": "Enum text captured; the actual rendered attractor curve is a separate, dynamic visual element"},
        prompt_text="What text do you see in this image? Just transcribe it exactly.",
        capture_audit={
            "text_captured": True, "visual_state_captured": False, "shape_captured": False,
            "missing_observable_state": [
                "The rendered Lorenz attractor curve itself (butterfly-shaped double-loop, visible in the source frame's LFO graph area, separate from this text-label crop). This is a continuously-animated visualization of an ongoing chaotic process, not a fixed or settable parameter. My assessment, not verified against Serum's actual preset file schema, is this is likely NOT_APPLICABLE as an independent reproducible parameter beyond the enum name plus Rate/Sync (already a separate, unscoped field). Flagging as an open question rather than asserting it doesn't matter."
            ],
            "status": "PARTIAL"
        },
        source_notes="Enum text correctly captured after the working prompt was substituted. The literal curve rendering was never scored under any modality; classification of whether it is reproducible state or purely cosmetic animation is a judgment call outside this pixel-level audit's authority to close."
    ),
    dict(
        test_id=4, canonical_id="fx.overdrive.drive",
        source_path="video_screenshots/HEEGN1Xl5o4/step5_07m04s_main_delay_ping_pong.jpg",
        source_size=(1280,720), bbox=[560,130,620,150],
        crop_path="t4_drive.png", crop_size=(360,120),
        observation_kind="CONTROL",
        ground_truth={"value": "1.9", "visual_state": "knob_position_redundant_with_text", "notes": "Note: original commit incorrectly cited step5_05m51s as this value's source; corrected to step5_07m04s during the ROI experiment (see commit a1e5397 history)"},
        prompt_text="Read only the target control in this crop.\n\nTarget: Drive value\nReturn exactly:\nDRIVE=<visible text>\nor\nUNREADABLE=<reason>",
        capture_audit={
            "text_captured": True, "visual_state_captured": False, "shape_captured": False,
            "missing_observable_state": [
                "Same source frame is FX-chain-dense and largely unaudited: Hyper/Dimension (Rate=7 numeric knob, Unison toggle state, Detune/Retrig/Size/Mix knob positions, none scored)",
                "Equalizer: an actual filter-response CURVE is drawn in the EQ graph area (shelf shape), plus Freq=210/Q=60/Gain=0.0 and Freq=20000/Q=60/Gain=-24.0 numeric fields, none scored, curve shape not captured at all",
                "Delay: L/R sync times (1/4, 1/4), Feedback knob, Freq knob, and a large blue waveform/spectrum panel, none scored",
                "Distortion module header icon (collapsed, glyph state not inspected)",
                "LFO1 Chaos:Lorenz curve reappears in this frame (same instrument state as test 3), consistent but redundant, not independently scored here"
            ],
            "status": "PARTIAL"
        },
        source_notes="Assigned target (Drive=1.9) correctly captured, but this is by far the most under-sampled source frame in the benchmark: a single numeric crop out of an FX chain with 3 other modules carrying substantial unscored state, including one actual response curve."
    ),
    dict(
        test_id=5, canonical_id="voicing.legato",
        source_path="video_screenshots/HEEGN1Xl5o4/step1_01m09s_osc_a_sawtooth_setup.jpg",
        source_size=(1280,720), bbox=[735,480,825,512],
        crop_path="t5_legato.png", crop_size=(360,128),
        observation_kind="ENABLE_STATE",
        ground_truth={"value": "OFF", "visual_state": "unchecked_checkbox_glyph", "notes": "Confirmed by direct pixel inspection: empty/grey checkbox = OFF"},
        prompt_text="This crop shows a checkbox labeled LEGATO. Determine if the checkbox is checked (ON) or unchecked (OFF).\nReturn exactly:\nSTATE=ON\nor\nSTATE=OFF",
        capture_audit={
            "text_captured": False, "visual_state_captured": True, "shape_captured": "not_applicable",
            "missing_observable_state": [
                "IMPORTANT: this crop's own bbox (735,480)-(825,512) visually contains THREE additional distinct values that were never scored: (1) MONO checkbox state, also unchecked/OFF, directly above Legato; (2) POLY=8 numeric stepper (max polyphony setting), same row as MONO; (3) '0/8' voice-count readout in the Legato row. This is a LIVE/runtime meter (currently-active voices out of max), not a stable preset parameter, and should NOT be treated as reproducible ground truth the way Legato's ON/OFF state is.",
                "OSC A/B/C waveform shapes, ENV1 envelope curve, and an LFO curve are all visible elsewhere in this same 1280x720 source frame, consistent with tests 1 and 3's findings, not independently re-scored here"
            ],
            "status": "PARTIAL"
        },
        source_notes="Assigned target (Legato=OFF) correctly captured as a boolean visual-state classification, appropriately not treated as OCR. But the crop bbox was drawn loosely enough to include 3 more distinct values (Mono, Poly, voice-count meter) that the test never asked about or scored, and one of those (voice-count) is not even the same kind of thing (transient runtime state vs stored preset parameter); conflating it with the others would be a category error."
    ),
]

for e in entries_data:
    entry = {
        "benchmark_version": "roi-v1-gateB-audit",
        "source_image": {
            "path": e["source_path"], "sha256": sha256_of(e["source_path"]),
            "width": e["source_size"][0], "height": e["source_size"][1]
        },
        "roi": {
            "bbox": e["bbox"], "crop_sha256": sha256_of(e["crop_path"]),
            "crop_width": e["crop_size"][0], "crop_height": e["crop_size"][1]
        },
        "target": {"canonical_id": e["canonical_id"], "observation_kind": e["observation_kind"]},
        "ground_truth": e["ground_truth"],
        "model": {
            "name": "Qwen2.5-VL-3B-Instruct",
            "quantization": {"type": "bnb", "bits": 4, "double_quant": True, "quant_type": "nf4"},
            "max_pixels": 802816
        },
        "prompt": {"version": "five_roi_tests.py@80e5183", "text": e["prompt_text"]},
        "capture_audit": e["capture_audit"],
        "auditor_notes": e["source_notes"]
    }
    manifest["entries"].append(entry)

with open("gate_b_manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)

print("Manifest written:", len(manifest["entries"]), "entries")
for e in manifest["entries"]:
    print(f"  {e['target']['canonical_id']}: status={e['capture_audit']['status']}, missing={len(e['capture_audit']['missing_observable_state'])} items")
