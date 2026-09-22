import torch, time, json
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from pathlib import Path

M = "models/Qwen2.5-VL-3B-Instruct"
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(M, quantization_config=q, device_map="auto")
proc = AutoProcessor.from_pretrained(M, min_pixels=64 * 28 * 28, max_pixels=1024 * 28 * 28)

imgs = [
    "video_screenshots/HEEGN1Xl5o4/step1_01m09s_osc_a_sawtooth_setup.jpg",
    "video_screenshots/HEEGN1Xl5o4/step2_02m21s_noise_white_noise_active.jpg",
]

# Three prompts that force explicit failure logging
prompts = {
    "confidence": """For each Serum control visible on screen, respond ONLY with:
[CONTROL_NAME]: READABLE=[numeric_value] | UNREADABLE=[reason: occlusion/blur/cut_off/ambiguous]
Do NOT guess. If you cannot clearly read a value, respond UNREADABLE.""",
    
    "delta_check": """Compare this image to what you expect for a Serum panel. 
For each visible control:
- If value is clearly displayed: [NAME]: [EXACT_VALUE]
- If you see the control but cannot read the value: [NAME]: UNOBSERVED_OCCLUDED
- If the control position is where you expect it but is missing: [NAME]: IDENTITY_UNRESOLVED
Never make up a value.""",
    
    "confidence_score": """For each parameter, output [NAME]: value=[X] confidence=[HIGH|MED|LOW|FAILED]
Only use HIGH if you are >90% certain of the exact value.
Use FAILED if the display is too blurry, occluded, or ambiguous to read."""
}

for img_path in imgs:
    print(f"\n{'='*80}")
    print(f"IMAGE: {Path(img_path).stem}")
    print(f"{'='*80}")
    
    for prompt_name, prompt_text in prompts.items():
        msgs = [{"role": "user", "content": [
            {"type": "image", "image": img_path},
            {"type": "text", "text": prompt_text}
        ]}]
        text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        img_objs, vids = process_vision_info(msgs)
        inp = proc(text=[text], images=img_objs, videos=vids, padding=True, return_tensors="pt").to(model.device)
        t0 = time.time()
        out = model.generate(**inp, max_new_tokens=300)
        result = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0]
        elapsed = time.time() - t0
        
        print(f"\n[{prompt_name}]  ({elapsed:.1f}s)")
        print("-" * 80)
        print(result[:500].strip())
