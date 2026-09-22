import torch, time
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info

M = "models/Qwen2.5-VL-3B-Instruct"
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(M, quantization_config=q, device_map="auto")
proc = AutoProcessor.from_pretrained(M, min_pixels=64 * 28 * 28, max_pixels=1024 * 28 * 28)

img = "video_screenshots/HEEGN1Xl5o4/step1_01m09s_osc_a_sawtooth_setup.jpg"

prompts = [
    # Pure OCR: read all text
    "Read and transcribe every piece of text visible in this image. Include parameter names, labels, numbers, and indicators. Do not describe or interpret.",
    
    # Character-strict
    "Extract every visible text string, label, and numeric value shown on screen. If you see a number or word, transcribe it exactly as displayed.",
    
    # Panel-by-panel
    "Go panel by panel. In each panel, transcribe the exact text labels and any numbers or values shown. Do not infer.",
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
    out = model.generate(**inp, max_new_tokens=512)
    result = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0]
    elapsed = time.time() - t0
    
    print(f"\n{'='*70}")
    print(f"OCR PROMPT {i} ({elapsed:.1f}s)")
    print(f"{'='*70}")
    print(result[:500].strip())
    print()
