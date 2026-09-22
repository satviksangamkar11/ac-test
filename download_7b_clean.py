import os, time
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

from huggingface_hub import snapshot_download

print("=" * 70)
print("DOWNLOADING: Qwen2.5-VL-7B-Instruct")
print("=" * 70)

t0 = time.time()
try:
    path = snapshot_download(
        'Qwen/Qwen2.5-VL-7B-Instruct',
        local_dir='models/Qwen2.5-VL-7B-Instruct',
        repo_type='model'
    )
    elapsed = time.time() - t0
    
    import subprocess
    size_output = subprocess.check_output(['du', '-sh', 'models/Qwen2.5-VL-7B-Instruct'], 
                                         text=True).split()[0]
    weights = len([f for f in os.listdir('models/Qwen2.5-VL-7B-Instruct') 
                   if f.endswith('.safetensors')])
    
    print(f"\n✓ SUCCESS")
    print(f"  Downloaded: {size_output}")
    print(f"  Weight shards: {weights}/2")
    print(f"  Time: {elapsed/60:.1f} min")
    print(f"  Path: {path}")
    
except Exception as e:
    print(f"\n✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
