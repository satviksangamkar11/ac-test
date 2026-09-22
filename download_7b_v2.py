import os, time
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
from huggingface_hub import snapshot_download

print("Downloading Qwen2.5-VL-7B-Instruct weights...")
t0 = time.time()
try:
    path = snapshot_download(
        'Qwen/Qwen2.5-VL-7B-Instruct',
        local_dir='models/Qwen2.5-VL-7B-Instruct',
        allow_patterns=['*.safetensors'],  # Only weights, skip READMEs
        resume_download=True
    )
    elapsed = time.time() - t0
    print(f"\n✓ Downloaded in {elapsed/60:.1f} min to: {path}")
except Exception as e:
    print(f"✗ Error: {e}")
