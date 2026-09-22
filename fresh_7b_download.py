import os, sys
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

print("Fresh 7B download attempt...")
from huggingface_hub import hf_hub_download

try:
    # Download one shard at a time to verify progress
    for i in [1, 2]:
        print(f"\nDownloading shard {i}/2...")
        path = hf_hub_download(
            'Qwen/Qwen2.5-VL-7B-Instruct',
            f'model-0000{i}-of-00002.safetensors',
            local_dir='models/Qwen2.5-VL-7B-Instruct',
            force_download=False
        )
        print(f"  ✓ Shard {i} saved")
    
    print("\n✓ Download complete!")
except KeyboardInterrupt:
    print("Interrupted")
except Exception as e:
    print(f"Error: {e}")
