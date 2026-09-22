import os
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
from huggingface_hub import snapshot_download
print("Downloading Qwen2.5-VL-7B-Instruct...")
path = snapshot_download('Qwen/Qwen2.5-VL-7B-Instruct', local_dir='models/Qwen2.5-VL-7B-Instruct')
print(f"Downloaded to: {path}")
