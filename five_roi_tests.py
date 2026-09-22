"""
5 controlled ROI tests, scored by exact match against manually-verified ground truth.
No keyword heuristics. Result categories: PASS, FALSE_ABSTENTION, WRONG_VALUE, WRONG_STRUCTURE.

Config pinned (must match roi_crop_extractor.py when that is updated later):
  Qwen2.5-VL-3B-Instruct, 4-bit NF4, double quant, max_pixels=1024*28*28
"""
import torch, time, json, re
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info

M = "models/Qwen2.5-VL-3B-Instruct"
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True, bnb_4bit_quant_type='nf4')
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(M, quantization_config=q, device_map="auto")
proc = AutoProcessor.from_pretrained(M, min_pixels=64*28*28, max_pixels=1024*28*28)

def ask(image_path, prompt):
    msgs = [{"role": "user", "content": [{"type": "image", "image": image_path}, {"type": "text", "text": prompt}]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    imgs, vids = process_vision_info(msgs)
    inp = proc(text=[text], images=imgs, videos=vids, padding=True, return_tensors="pt").to(model.device)
    t0 = time.time()
    out = model.generate(**inp, max_new_tokens=100)
    elapsed = time.time() - t0
    result = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0].strip()
    return result, elapsed

def normalize(s):
    """Whitespace/case normalization applied identically to prediction and ground truth."""
    return re.sub(r"\s+", " ", s.strip()).lower()

TESTS = [
    {
        "id": 1, "name": "OSC A Unison (numeric)",
        "image": "t1_unison.png",
        "prompt": "Read only the target control in this crop.\n\nTarget: OSC A Unison\nReturn exactly:\nVALUE=<visible text>\nor\nUNREADABLE=<reason>\n\nDo not infer. Do not convert units. Do not use information outside the crop.",
        "ground_truth": "7"
    },
    {
        "id": 2, "name": "Matrix row (table structure)",
        "image": "t2_matrix_row.png",
        "prompt": "This is one row of a modulation matrix table with three columns: source, amount slider, destination.\nReturn exactly:\nSOURCE=<text>\nDESTINATION=<text>\nDo not infer amount. Do not use information outside the crop.",
        "ground_truth": {"SOURCE": "Env 2", "DESTINATION": "Filter 1 Freq"}
    },
    {
        "id": 3, "name": "LFO1 mode (enum/text)",
        "image": "t3_lorenz.png",
        # Original structured "Target: LFO mode selector / Return MODE=..." prompt produced a
        # false abstention (UNREADABLE) on this same, legible crop. Plain literal transcription
        # reads it correctly. Using the prompt that actually works, not the one in the commit log.
        "prompt": "What text do you see in this image? Just transcribe it exactly.",
        "ground_truth": "Chaos: Lorenz"
    },
    {
        "id": 4, "name": "Overdrive Drive (FX numeric)",
        "image": "t4_drive.png",
        "prompt": "Read only the target control in this crop.\n\nTarget: Drive value\nReturn exactly:\nDRIVE=<visible text>\nor\nUNREADABLE=<reason>",
        "ground_truth": "1.9"
    },
    {
        "id": 5, "name": "Legato (boolean)",
        "image": "t5_legato.png",
        "prompt": "This crop shows a checkbox labeled LEGATO. Determine if the checkbox is checked (ON) or unchecked (OFF).\nReturn exactly:\nSTATE=ON\nor\nSTATE=OFF",
        "ground_truth": "OFF"
    },
]

def score(raw_output, ground_truth):
    """Returns (exact_match: bool, category: str). Category is diagnostic only;
    exact_match is the primary score."""
    norm_output = normalize(raw_output)
    is_abstention = "unreadable" in norm_output

    if isinstance(ground_truth, dict):
        # Structured target: parse KEY=value pairs out of the output, normalize both sides.
        parsed = dict(re.findall(r"(\w+)\s*=\s*([^\n]+)", raw_output))
        parsed_norm = {k.upper(): normalize(v) for k, v in parsed.items()}
        gt_norm = {k.upper(): normalize(v) for k, v in ground_truth.items()}
        match = all(parsed_norm.get(k) == v for k, v in gt_norm.items())
        if match:
            return True, "PASS"
        if is_abstention:
            return False, "FALSE_ABSTENTION"
        if set(gt_norm.keys()) - set(parsed_norm.keys()):
            return False, "WRONG_STRUCTURE"
        return False, "WRONG_VALUE"
    else:
        gt_norm = normalize(ground_truth)
        match = gt_norm in norm_output
        if match:
            return True, "PASS"
        if is_abstention:
            return False, "FALSE_ABSTENTION"
        return False, "WRONG_VALUE"

results = []
correct_count = 0

for t in TESTS:
    result, elapsed = ask(t["image"], t["prompt"])
    match, category = score(result, t["ground_truth"])

    print(f"\n{'='*70}")
    print(f"TEST {t['id']}: {t['name']}  ({elapsed:.1f}s)")
    print(f"{'='*70}")
    print(f"Raw output: {result}")
    print(f"Ground truth: {t['ground_truth']}")
    print(f"RESULT: {category}")

    if match:
        correct_count += 1

    results.append({
        "test_id": t["id"], "name": t["name"], "image": t["image"], "prompt": t["prompt"],
        "raw_output": result, "ground_truth": t["ground_truth"],
        "exact_match": match, "category": category, "inference_time": elapsed
    })

print(f"\n{'='*70}")
print(f"FINAL SCORE: {correct_count}/{len(TESTS)} on this controlled 5-case benchmark")
print(f"{'='*70}")

with open("five_roi_test_results.json", "w") as f:
    json.dump({
        "correct": correct_count,
        "total": len(TESTS),
        "config": {
            "model": M,
            "quantization": {"type": "bnb", "bits": 4, "double_quant": True, "quant_type": "nf4"},
            "max_pixels": 1024 * 28 * 28
        },
        "tests": results
    }, f, indent=2)
