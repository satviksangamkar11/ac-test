import torch, time, re
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
    "video_screenshots/HEEGN1Xl5o4/step3_04m19s_env4_pitch_transient.jpg",
]

prompt = "Transcribe all visible text labels and values. List each unique text element only once."

for img_path in imgs:
    msgs = [{"role": "user", "content": [
        {"type": "image", "image": img_path},
        {"type": "text", "text": prompt}
    ]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    img_objs, vids = process_vision_info(msgs)
    inp = proc(text=[text], images=img_objs, videos=vids, padding=True, return_tensors="pt").to(model.device)
    t0 = time.time()
    out = model.generate(**inp, max_new_tokens=256)
    result = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0]
    elapsed = time.time() - t0
    
    # Deduplicate
    lines = result.split('\n')
    seen = set()
    unique = []
    for line in lines:
        clean = line.strip()
        if clean and clean not in seen:
            seen.add(clean)
            unique.append(clean)
    
    print(f"\n{'='*70}")
    print(f"{Path(img_path).stem}  ({elapsed:.1f}s)")
    print(f"{'='*70}")
    for line in unique[:20]:
        print(line)
    if len(unique) > 20:
        print(f"... +{len(unique)-20} more")
