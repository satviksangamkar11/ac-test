#!/bin/bash
echo "7B Download Monitor (updated every 60s)"
echo "========================================"
start_time=$(date +%s)

while true; do
  size=$(du -sh models/Qwen2.5-VL-7B-Instruct 2>/dev/null | cut -f1)
  weights=$(ls -1 models/Qwen2.5-VL-7B-Instruct/*.safetensors 2>/dev/null | wc -l)
  elapsed=$(($(date +%s) - start_time))
  mins=$((elapsed / 60))
  
  if [ "$weights" -eq 2 ]; then
    echo ""
    echo "✓✓✓ DOWNLOAD COMPLETE ✓✓✓"
    echo "Size: $size | Weights: 2/2"
    echo "Total time: ${mins}m"
    echo ""
    echo "Running 7B vs 3B benchmark..."
    timeout 900 /d/ableton\ claude\ final\ best/.venv_qwen/Scripts/python /d/ableton\ claude\ final\ best/benchmark_7b_vs_3b.py 2>&1 | grep -v "^Loading\|^W0\|UserWarning\|inner" | tail -100
    break
  fi
  
  pct=$(($(echo "$size" | sed 's/G.*//' | sed 's/M.*/0.001/') * 100 / 15))
  echo "[$(date +%H:%M:%S)] $size / ~15GB [$weights/2 weights] (~${pct}%)"
  
  sleep 60
done
