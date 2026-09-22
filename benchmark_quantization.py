"""
Benchmark: 4-bit vs 3-bit HQQ vs 2-bit
Measures: OCR accuracy, hallucination detection, VRAM usage
"""
import torch, time, json
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from pathlib import Path

BENCHMARK_IMAGES = [
    "video_screenshots/HEEGN1Xl5o4/step1_01m09s_osc_a_sawtooth_setup.jpg",
    "video_screenshots/HEEGN1Xl5o4/step2_02m21s_noise_white_noise_active.jpg",
    "video_screenshots/HEEGN1Xl5o4/step3_04m19s_env4_pitch_transient.jpg",
]

TESTS = {
    "4bit_bnb": {
        "config": BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type='nf4'
        ),
        "name": "BNB 4-bit + double quant"
    },
    # Will add HQQ 3-bit and 2-bit once HQQ is installed
}

prompt_ocr = """Read ONLY visible text. For each parameter:
[NAME]: READABLE=[text] | UNREADABLE=[reason]"""

print(f"{'='*70}")
print("Quantization Benchmark: Qwen2.5-VL-7B-Instruct")
print(f"{'='*70}\n")

for test_name, test_cfg in TESTS.items():
    print(f"\nLoading {test_cfg['name']}...")
    t0 = time.time()
    
    try:
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            'models/Qwen2.5-VL-7B-Instruct',
            quantization_config=test_cfg['config'],
            device_map='auto',
            max_memory={0: '5.5GiB', 'cpu': '14GiB'},
            torch_dtype=torch.float16
        )
        proc = AutoProcessor.from_pretrained('models/Qwen2.5-VL-7B-Instruct')
        load_time = time.time() - t0
        
        vram_used = torch.cuda.memory_allocated() / 1e9
        
        print(f"  ✓ Loaded in {load_time:.1f}s, VRAM: {vram_used:.2f} GB\n")
        
        results = {"test": test_name, "load_time": load_time, "vram_gb": vram_used, "images": []}
        
        # Test on benchmark images
        for img_path in BENCHMARK_IMAGES:
            msgs = [{"role": "user", "content": [
                {"type": "image", "image": img_path},
                {"type": "text", "text": prompt_ocr}
            ]}]
            text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            imgs, vids = process_vision_info(msgs)
            inp = proc(text=[text], images=imgs, videos=vids, padding=True, return_tensors="pt").to(model.device)
            
            t_inf = time.time()
            out = model.generate(**inp, max_new_tokens=200)
            inf_time = time.time() - t_inf
            
            result_text = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0]
            
            has_unreadable = "UNREADABLE" in result_text
            has_readable = "READABLE" in result_text
            hallucination_risk = "100" in result_text or "50" in result_text  # invented numbers
            
            results["images"].append({
                "file": Path(img_path).stem,
                "inference_time": inf_time,
                "has_explicit_failures": has_unreadable,
                "has_readable_values": has_readable,
                "hallucination_risk": hallucination_risk,
                "sample": result_text[:200]
            })
            
            print(f"  {Path(img_path).stem}: {inf_time:.1f}s (failures={has_unreadable}, halluc_risk={hallucination_risk})")
        
        # Save results
        with open(f'benchmark_{test_name}.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        del model
        torch.cuda.empty_cache()
        
    except Exception as e:
        print(f"  ✗ Failed: {str(e)[:150]}")

print(f"\n{'='*70}")
print("Benchmark complete. Compare JSON files for quantization trade-offs.")
