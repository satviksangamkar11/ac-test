import torch, time
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

print("Double-quantization config for 7B on 6GB GPU...")
q = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,  # Extra compression
    bnb_4bit_quant_type='nf4'
)

t0 = time.time()
try:
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        'Qwen/Qwen2.5-VL-7B-Instruct',
        quantization_config=q,
        device_map='auto',
        max_memory={0: '5.5GiB', 'cpu': '14GiB'},
        torch_dtype=torch.float16,
        attn_implementation='flash_attention_2'
    )
    print(f"✓ 7B loaded in {time.time()-t0:.1f}s")
    print(f"GPU memory used: {torch.cuda.memory_allocated()/1e9:.2f} GB")
    print("Success!")
except RuntimeError as e:
    print(f"✗ Failed: {str(e)[:200]}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {str(e)[:150]}")
