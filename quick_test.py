import time, torch
from PIL import Image, ImageDraw
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info

M = "models/Qwen2.5-VL-3B-Instruct"
img = Image.new("RGB", (400, 200), (30, 30, 35)); d = ImageDraw.Draw(img)
for y, t in enumerate(["OSC A Pitch: +12 SEMI", "Filter Cutoff: 75%", "Unison Voices: 7", "Warp Mode: Phase Dist (PD)"]):
    d.text((20, 20 + y * 40), t, fill=(255, 255, 255))
img.save("test_ui.png")

t0 = time.time()
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    M, quantization_config=q, device_map="auto")
proc = AutoProcessor.from_pretrained(M, min_pixels=64 * 28 * 28, max_pixels=256 * 28 * 28)
print(f"loaded {time.time()-t0:.1f}s")

msgs = [{"role": "user", "content": [{"type": "image", "image": "test_ui.png"},
        {"type": "text", "text": "Extract parameters and values in JSON."}]}]
text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
imgs, vids = process_vision_info(msgs)
inp = proc(text=[text], images=imgs, videos=vids, padding=True, return_tensors="pt").to(model.device)
t1 = time.time()
out = model.generate(**inp, max_new_tokens=128)
print(f"inference {time.time()-t1:.1f}s")
print(proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0])
