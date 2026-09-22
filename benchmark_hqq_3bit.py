"""
Benchmark: 3B with BNB 4-bit vs HQQ 3-bit
Measures VRAM, inference time, hallucination rate
"""
import torch, time, json
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from hqq.core.quantize import HQQLinear
from qwen_vl_utils import process_vision_info
from pathlib import Path

MODEL = 'models/Qwen2.5-VL-3B-Instruct'
IMAGES = [
    "video_screenshots/HEEGN1Xl5o4/step1_01m09s_osc_a_sawtooth_setup.jpg",
    "video_screenshots/HEEGN1Xl5o4/step2_02m21s_noise_white_noise_active.jpg",
    "video_screenshots/HEEGN1Xl5o4/step3_04m19s_env4_pitch_transient.jpg",
]

prompt = """Read ONLY visible text. For each parameter:
[NAME]: READABLE=[text] | UNREADABLE=[reason]"""

def test_config(name, quantization_config=None, hqq_config=None):
    print(f"\n{'='*70}\n{name}\n{'='*70}")
    
    t0 = time.time()
    try:
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            MODEL,
            quantization_config=quantization_config,
            device_map='auto',
            torch_dtype=torch.float16
        )
        
        # Apply HQQ if specified
        if hqq_config:
            print("  Applying HQQ quantization...")
            HQQLinear.quantize_model_(model, **hqq_config)
        
        proc = AutoProcessor.from_pretrained(MODEL)
        load_time = time.time() - t0
        vram = torch.cuda.memory_allocated() / 1e9
        
        print(f"  Load: {load_time:.1f}s | VRAM: {vram:.2f} GB")
        
        results = {"name": name, "load_time": load_time, "vram_gb": vram, "images": []}
        
        for img_path in IMAGES:
            msgs = [{"role": "user", "content": [
                {"type": "image", "image": img_path},
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
            halluc_risk = any(x in result_text for x in ["100", "50", "75", "120", "180"])
            
            results["images"].append({
                "file": Path(img_path).stem,
                "inference_time": inf_time,
                "explicit_failures": has_unreadable,
                "hallucination_risk": halluc_risk
            })
            
            print(f"    {Path(img_path).stem}: {inf_time:.1f}s (failures={has_unreadable})")
        
        with open(f'benchmark_{name.replace(" ", "_")}.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        del model
        torch.cuda.empty_cache()
        return results
        
    except Exception as e:
        print(f"  ✗ Failed: {str(e)[:100]}")
        return None

# Benchmark 1: 4-bit baseline
config_4bit = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type='nf4'
)
r1 = test_config("4-bit BNB (baseline)", quantization_config=config_4bit)

# Benchmark 2: HQQ 3-bit
config_hqq3 = {
    'quant_config': {
        'weight_quant': 'nf3',
        'scale_quant': None,
        'group_size': 64
    }
}
r2 = test_config("3-bit HQQ", hqq_config=config_hqq3)

# Summary
print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
if r1:
    print(f"\n4-bit:  {r1['vram_gb']:.2f} GB VRAM, {r1['load_time']:.1f}s load")
if r2:
    print(f"3-bit:  {r2['vram_gb']:.2f} GB VRAM, {r2['load_time']:.1f}s load")
    if r1:
        savings = (r1['vram_gb'] - r2['vram_gb']) / r1['vram_gb'] * 100 if r2['vram_gb'] < r1['vram_gb'] else 0
        print(f"\n→ 3-bit saves {savings:.1f}% VRAM" if savings > 0 else "\n→ 3-bit uses more VRAM")

