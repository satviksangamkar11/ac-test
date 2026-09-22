"""
Compare 3B vs 7B on architectural requirements:
1. Explicit failure modes (UNOBSERVED_* vs hallucinations)
2. VRAM efficiency
3. Inference speed
4. ROI pipeline performance
"""
import torch, time, json
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from pathlib import Path

MODELS = {
    '3B': 'models/Qwen2.5-VL-3B-Instruct',
    '7B': 'models/Qwen2.5-VL-7B-Instruct'
}

IMAGES = [
    "video_screenshots/HEEGN1Xl5o4/step1_01m09s_osc_a_sawtooth_setup.jpg",
    "video_screenshots/HEEGN1Xl5o4/step2_02m21s_noise_white_noise_active.jpg",
    "video_screenshots/HEEGN1Xl5o4/step3_04m19s_env4_pitch_transient.jpg",
]

prompt = """Read ONLY visible text. For each parameter:
[NAME]: READABLE=[text] | UNREADABLE=[reason]"""

def benchmark_model(model_name, model_path):
    print(f"\n{'='*70}\n{model_name}\n{'='*70}")
    
    if not Path(model_path).exists():
        print(f"  ✗ Not found: {model_path}")
        return None
    
    config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type='nf4'
    )
    
    t0 = time.time()
    try:
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_path, quantization_config=config, device_map='auto', torch_dtype=torch.float16
        )
        proc = AutoProcessor.from_pretrained(model_path)
        load_time = time.time() - t0
        vram = torch.cuda.memory_allocated() / 1e9
        
        print(f"  Load: {load_time:.1f}s | VRAM: {vram:.2f} GB")
        
        results = {"model": model_name, "load_time": load_time, "vram_gb": vram, "images": []}
        
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
                "hallucination_risk": halluc_risk,
                "sample": result_text[:150]
            })
            
            print(f"    {Path(img_path).stem}: {inf_time:.1f}s (failures={has_unreadable}, halluc={halluc_risk})")
        
        with open(f'benchmark_{model_name}.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        del model
        torch.cuda.empty_cache()
        return results
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)[:150]}")
        return None

# Run benchmarks
print("ARCHITECTURAL VALIDATION: 3B vs 7B")
print("Criteria: Explicit failures, no hallucinations, VRAM efficiency\n")

results_3b = benchmark_model("3B", MODELS['3B'])
results_7b = benchmark_model("7B", MODELS['7B'])

# Compare
if results_3b and results_7b:
    print(f"\n{'='*70}\nCOMPARISON\n{'='*70}")
    print(f"\nVRAM:")
    print(f"  3B: {results_3b['vram_gb']:.2f} GB")
    print(f"  7B: {results_7b['vram_gb']:.2f} GB")
    
    print(f"\nLoad time:")
    print(f"  3B: {results_3b['load_time']:.1f}s")
    print(f"  7B: {results_7b['load_time']:.1f}s")
    
    fails_3b = sum(1 for img in results_3b['images'] if img['explicit_failures'])
    fails_7b = sum(1 for img in results_7b['images'] if img['explicit_failures'])
    halluc_3b = sum(1 for img in results_3b['images'] if img['hallucination_risk'])
    halluc_7b = sum(1 for img in results_7b['images'] if img['hallucination_risk'])
    
    print(f"\nExplicit failures (UNOBSERVED_*) per 3 images:")
    print(f"  3B: {fails_3b}/3")
    print(f"  7B: {fails_7b}/3")
    
    print(f"\nHallucination risk per 3 images:")
    print(f"  3B: {halluc_3b}/3")
    print(f"  7B: {halluc_7b}/3")

