import os, time
from pathlib import Path

print("Waiting for 7B... (will auto-benchmark when ready)\n")
start = time.time()

while True:
    size_bytes = sum(p.stat().st_size for p in Path("models/Qwen2.5-VL-7B-Instruct").rglob("*") if p.is_file())
    size_gb = size_bytes / 1024 / 1024 / 1024
    weights = len(list(Path("models/Qwen2.5-VL-7B-Instruct").glob("*.safetensors")))
    elapsed_min = (time.time() - start) / 60
    pct = int(size_gb / 15 * 100)
    
    if weights == 2:
        print(f"\n{'='*70}")
        print(f"✓✓✓ 7B READY ✓✓✓")
        print(f"Size: {size_gb:.1f}GB | Weights: 2/2 | Time: {elapsed_min:.0f}m")
        print(f"{'='*70}\n")
        print("Running 3B vs 7B benchmark...\n")
        os.system(".venv_qwen/Scripts/python benchmark_7b_vs_3b.py 2>&1 | grep -v 'Loading\|UserWarning'")
        break
    
    remaining_gb = 15 - size_gb
    eta_min = remaining_gb * 60 / 175
    print(f"[{time.strftime('%H:%M')}] {size_gb:5.1f}GB {pct:3d}% | ETA {eta_min:3.0f}m")
    time.sleep(60)

