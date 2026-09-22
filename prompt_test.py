import torch, time
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from pathlib import Path

M = "models/Qwen2.5-VL-3B-Instruct"
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(M, quantization_config=q, device_map="auto")
proc = AutoProcessor.from_pretrained(M, min_pixels=64 * 28 * 28, max_pixels=512 * 28 * 28)

img = "video_screenshots/HEEGN1Xl5o4/step1_01m09s_osc_a_sawtooth_setup.jpg"

prompts = [
    # Original (baseline)
    "List all visible synthesizer parameters, settings, and values. Be concise.",
    
    # Strict OCR (read-only, no inference)
    "Read ONLY the exact text visible on screen. Do not infer or add values not shown. List parameter names and visible numeric values or text labels only.",
    
    # Serum-specific format
    "This is a Serum synthesizer UI. Extract ONLY values that are visibly displayed as text, numbers, or indicators on the screen. Do not estimate. Format as: [CONTROL_NAME]: [VISIBLE_VALUE]",
]

for i, prompt in enumerate(prompts, 1):
    msgs = [{"role": "user", "content": [
        {"type": "image", "image": img},
        {"type": "text", "text": prompt}
    ]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    imgs, vids = process_vision_info(msgs)
    inp = proc(text=[text], images=imgs, videos=vids, padding=True, return_tensors="pt").to(model.device)
    t0 = time.time()
    out = model.generate(**inp, max_new_tokens=256)
    result = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0]
    elapsed = time.time() - t0
    
    print(f"\n{'='*60}")
    print(f"PROMPT {i} ({elapsed:.1f}s)")
    print(f"{'='*60}")
    print(f"Q: {prompt}")
    print(f"\nA: {result[:400].strip()}")
    print()
