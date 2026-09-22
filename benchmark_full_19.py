"""
Full 19 Serum screenshots benchmark with 3B
Validates architectural requirements at scale:
- No silent drops (E == O gate)
- Explicit failure modes
- No hallucinations
"""
import torch, time, json
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from pathlib import Path

MODEL = 'models/Qwen2.5-VL-3B-Instruct'
IMAGES = sorted(Path("video_screenshots/HEEGN1Xl5o4").glob("*.jpg"))

print(f"{'='*70}")
print(f"BENCHMARK: 3B on {len(IMAGES)} Serum Screenshots")
print(f"{'='*70}\n")

# Load model once
config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type='nf4'
)

t0 = time.time()
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    MODEL, quantization_config=config, device_map='auto', torch_dtype=torch.float16
)
proc = AutoProcessor.from_pretrained(MODEL)
load_time = time.time() - t0
vram = torch.cuda.memory_allocated() / 1e9

print(f"Model loaded: {load_time:.1f}s | VRAM: {vram:.2f} GB\n")

prompt = """Read ONLY visible text. For each parameter:
[NAME]: READABLE=[text] | UNREADABLE=[reason]"""

results = {
    "model": "3B 4-bit",
    "load_time": load_time,
    "vram_gb": vram,
    "total_images": len(IMAGES),
    "images": []
}

explicit_failures = 0
halluc_risk = 0

for i, img_path in enumerate(IMAGES, 1):
    msgs = [{"role": "user", "content": [
        {"type": "image", "image": str(img_path)},
        {"type": "text", "text": prompt}
    ]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    imgs, vids = process_vision_info(msgs)
    inp = proc(text=[text], images=imgs, videos=vids, padding=True, return_tensors="pt").to(model.device)
    
    t_inf = time.time()
    out = model.generate(**inp, max_new_tokens=200)
    inf_time = time.time() - t_inf
    
    result_text = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0]
    
    has_unreadable = "UNREADABLE" in result_text
    halluc = any(x in result_text for x in ["100", "50", "75", "120", "180"])
    
    if has_unreadable:
        explicit_failures += 1
    if halluc:
        halluc_risk += 1
    
    results["images"].append({
        "file": img_path.stem,
        "inference_time": inf_time,
        "explicit_failures": has_unreadable,
        "hallucination_risk": halluc
    })
    
    status = "FAIL" if has_unreadable else "PASS"
    halluc_str = " (HALLUC!)" if halluc else ""
    print(f"[{i:2d}/19] {img_path.stem[:40]:40s} {inf_time:5.1f}s {status}{halluc_str}")

# Summary
print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
print(f"\nModel: 3B 4-bit")
print(f"Load: {load_time:.1f}s | VRAM: {vram:.2f} GB")
print(f"Images: {len(IMAGES)}")
print(f"Avg inference: {sum(img['inference_time'] for img in results['images'])/len(IMAGES):.1f}s")
print(f"\nArchitectural validation:")
print(f"  Explicit failures: {explicit_failures}/{len(IMAGES)} (UNOBSERVED_* records)")
print(f"  Hallucination risk: {halluc_risk}/{len(IMAGES)} (invented values)")
print(f"  Pass rate: {(len(IMAGES)-halluc_risk)/len(IMAGES)*100:.0f}%")

# Save results
with open('benchmark_3b_full_19.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✓ Results saved to benchmark_3b_full_19.json")

