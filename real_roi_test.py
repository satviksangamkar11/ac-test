"""
Real ROI test: crop vs full-frame, scored against KNOWN ground truth (not keyword matching)
Ground truth for step1_01m09s (verified by manual visual inspection):
  OSC A: OCT=0, SEM=0, FIN=0, CRS=--
"""
import torch, time
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info

M = "models/Qwen2.5-VL-3B-Instruct"
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True, bnb_4bit_quant_type='nf4')
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(M, quantization_config=q, device_map="auto")
proc = AutoProcessor.from_pretrained(M, min_pixels=64*28*28, max_pixels=1024*28*28)

GROUND_TRUTH = {"OCT": "0", "SEM": "0", "FIN": "0"}

def ask(image_path, prompt, label):
    msgs = [{"role": "user", "content": [{"type": "image", "image": image_path}, {"type": "text", "text": prompt}]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    imgs, vids = process_vision_info(msgs)
    inp = proc(text=[text], images=imgs, videos=vids, padding=True, return_tensors="pt").to(model.device)
    t0 = time.time()
    out = model.generate(**inp, max_new_tokens=100)
    elapsed = time.time() - t0
    result = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0]
    print(f"\n[{label}] ({elapsed:.1f}s)")
    print(result.strip()[:300])
    return result

print("="*70)
print("TEST A: Full frame (what we did before — known to fail)")
print("="*70)
ask("video_screenshots/HEEGN1Xl5o4/step1_01m09s_osc_a_sawtooth_setup.jpg",
    "What are the OCT, SEM, and FIN values for OSC A in this Serum screenshot?",
    "FULL FRAME")

print("\n" + "="*70)
print("TEST B: ROI crop (targeted, upscaled)")
print("="*70)
result_roi = ask("roi_test_osca.png",
    "Read the OCT, SEM, and FIN numeric values shown. Respond as OCT=x SEM=x FIN=x",
    "ROI CROP")

print("\n" + "="*70)
print("GROUND TRUTH CHECK")
print("="*70)
print(f"Expected: OCT=0 SEM=0 FIN=0")
correct = all(f"{k}={v}" in result_roi.replace(" ", "").upper().replace("=0.0","=0") or f"{k}: {v}" in result_roi 
              for k, v in GROUND_TRUTH.items())
print(f"ROI crop matches ground truth: {correct}")
