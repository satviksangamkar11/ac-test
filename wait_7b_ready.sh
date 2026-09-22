#!/bin/bash
echo "Waiting for Qwen2.5-VL-7B weights..."
for i in {1..20}; do
  weights=$(ls -1 models/Qwen2.5-VL-7B-Instruct/*.safetensors 2>/dev/null | wc -l)
  size=$(du -sh models/Qwen2.5-VL-7B-Instruct 2>/dev/null | cut -f1)
  
  if [ "$weights" -eq 2 ]; then
    echo "✓ READY: 7B downloaded ($size, 2 weight shards)"
    exit 0
  fi
  
  echo "$(date +%H:%M:%S) | $size | $weights/2 weights"
  sleep 30
done

echo "⧗ Still downloading after 10 min. Run:"
echo "  du -sh models/Qwen2.5-VL-7B-Instruct"
