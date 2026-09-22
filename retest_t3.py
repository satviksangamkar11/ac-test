import torch, time
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

prompt = "Read only the target text in this crop.\n\nTarget: LFO mode selector\nReturn exactly:\nMODE=<visible text>\nor\nUNREADABLE=<reason>"
r, t = ask("t3_lorenz_v2.png", prompt)
print(f"Larger crop (750x180): {r} ({t:.1f}s)")

r2, t2 = ask("t3_lorenz.png", "What text do you see in this image? Just transcribe it exactly.")
print(f"Original crop, different prompt: {r2} ({t2:.1f}s)")
