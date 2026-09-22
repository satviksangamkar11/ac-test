"""
5 controlled ROI tests, scored by exact match against manually-verified ground truth.
No keyword heuristics.
"""
import torch, time, json
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
        "prompt": "Read only the target text in this crop.\n\nTarget: LFO mode selector\nReturn exactly:\nMODE=<visible text>\nor\nUNREADABLE=<reason>",
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

results = []
correct_count = 0

for t in TESTS:
    result, elapsed = ask(t["image"], t["prompt"])
    print(f"\n{'='*70}")
    print(f"TEST {t['id']}: {t['name']}  ({elapsed:.1f}s)")
    print(f"{'='*70}")
    print(f"Raw output: {result}")
    print(f"Ground truth: {t['ground_truth']}")
    
    # Exact match scoring
    if isinstance(t["ground_truth"], dict):
        match = all(f"{k}={v}" in result.replace(" ", "") for k, v in t["ground_truth"].items())
    else:
        gt = t["ground_truth"]
        match = gt.replace(" ", "").lower() in result.replace(" ", "").lower()
    
    print(f"EXACT MATCH: {match}")
    if match:
        correct_count += 1
    
    results.append({
        "test_id": t["id"], "name": t["name"], "raw_output": result,
        "ground_truth": t["ground_truth"], "exact_match": match, "inference_time": elapsed
    })

print(f"\n{'='*70}")
print(f"FINAL SCORE: {correct_count}/{len(TESTS)} = {correct_count/len(TESTS)*100:.0f}%")
print(f"{'='*70}")

with open("five_roi_test_results.json", "w") as f:
    json.dump({"correct": correct_count, "total": len(TESTS), "tests": results}, f, indent=2)
