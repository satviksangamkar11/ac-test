import os, time, subprocess
from pathlib import Path

print("7B Download Monitor\n" + "="*50)
start = time.time()

while True:
    size_kb = sum(p.stat().st_size for p in Path("models/Qwen2.5-VL-7B-Instruct").rglob("*") if p.is_file()) / 1024 / 1024
    weights = len(list(Path("models/Qwen2.5-VL-7B-Instruct").glob("*.safetensors")))
    elapsed_min = (time.time() - start) / 60
    
    size_str = f"{size_kb/1024:.1f}G" if size_kb > 1024 else f"{size_kb:.0f}M"
    pct = int(size_kb / 15360 * 100) if size_kb < 15360 else 100
    
    if weights == 2:
        print(f"\n✓ COMPLETE in {elapsed_min:.0f}m")
        print(f"  {size_str} | {weights}/2 weights")
        print("\nRunning benchmark...")
        os.system("timeout 900 .venv_qwen/Scripts/python benchmark_7b_vs_3b.py 2>&1 | grep -v '^Loading\|^W0\|UserWarning\|inner'")
        break
    
    print(f"[{time.strftime('%H:%M')}] {size_str:>6} | {weights}/2 weights | ~{pct}% | ETA {elapsed_min + (15360-size_kb)/175/60:.0f}m")
    time.sleep(60)

