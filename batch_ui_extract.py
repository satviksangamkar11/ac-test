import time, json, torch, os
from pathlib import Path
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info

M = "models/Qwen2.5-VL-3B-Instruct"
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(M, quantization_config=q, device_map="auto")
proc = AutoProcessor.from_pretrained(M, min_pixels=64 * 28 * 28, max_pixels=512 * 28 * 28)
print("Model loaded.\n")

imgs = sorted(Path("video_screenshots/HEEGN1Xl5o4").glob("*.jpg"))
for img_path in imgs:
    msgs = [{"role": "user", "content": [
        {"type": "image", "image": str(img_path)},
        {"type": "text", "text": "List all visible synthesizer parameters, settings, and values. Be concise."}
    ]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    img_objs, vids = process_vision_info(msgs)
    inp = proc(text=[text], images=img_objs, videos=vids, padding=True, return_tensors="pt").to(model.device)
    t0 = time.time()
    out = model.generate(**inp, max_new_tokens=200)
    result = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0]
    elapsed = time.time() - t0
    print(f"{img_path.stem}  ({elapsed:.1f}s)")
    print(result.strip()[:300])
    print()
