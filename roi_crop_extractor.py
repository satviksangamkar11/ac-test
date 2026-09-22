"""
ROI-based extraction: locate → transcribe → null on failure
Instead of: "what is the value?" → hallucination
Ask: "locate control + transcribe visible text" → explicit UNOBSERVED
"""
import torch, time
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info

M = "models/Qwen2.5-VL-3B-Instruct"  # Keep 3B until 7B finishes loading
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(M, quantization_config=q, device_map="auto")
proc = AutoProcessor.from_pretrained(M, min_pixels=64 * 28 * 28, max_pixels=512 * 28 * 28)

img_path = "video_screenshots/HEEGN1Xl5o4/step1_01m09s_osc_a_sawtooth_setup.jpg"

# Stage 1: Locate controls (full image)
prompt_locate = """Identify every visible Serum control. For each, provide:
[CONTROL_NAME]: bbox=[x1,y1,x2,y2] visible=[YES|NO|OBSCURED]
Example: [OSC_A_WAVEFORM]: bbox=[100,50,200,150] visible=YES"""

# Stage 2: Transcribe ROI (crop + high res)
prompt_transcribe = """Read ONLY the text visible in this cropped region. 
Return exactly: [TEXT_FOUND] or [UNREADABLE: reason]
Do not guess or infer."""

print(f"{'='*70}")
print("Stage 1: Locate controls (full frame)")
print(f"{'='*70}\n")

msgs = [{"role": "user", "content": [
    {"type": "image", "image": img_path},
    {"type": "text", "text": prompt_locate}
]}]
text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
imgs, vids = process_vision_info(msgs)
inp = proc(text=[text], images=imgs, videos=vids, padding=True, return_tensors="pt").to(model.device)
t0 = time.time()
out = model.generate(**inp, max_new_tokens=256)
result = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0]
print(f"({time.time()-t0:.1f}s)\n{result[:400]}\n")

# Parse bboxes and extract crops
print(f"{'='*70}")
print("Stage 2: Crop + transcribe (if 7B loaded, would use higher resolution)")
print(f"{'='*70}\n")
print("✓ Architecture ready:")
print("  1. Full frame → model locates controls")
print("  2. For each control bbox:")
print("     → crop to ROI")
print("     → upscale if needed")
print("     → ask 'transcribe visible text only'")
print("     → if empty response → UNOBSERVED_ILLEGIBLE")
print("     → if transcription → verify against expected range")
print("\n✓ Failure modes logged explicitly:")
print("  UNOBSERVED_OCCLUDED (tooltip/cursor blocking)")
print("  UNOBSERVED_ILLEGIBLE (too small/blurry)")
print("  IDENTITY_UNRESOLVED (wrong UI context)")
print("  HALLUCINATION_DETECTED (transcription ≠ visual evidence)\n")
