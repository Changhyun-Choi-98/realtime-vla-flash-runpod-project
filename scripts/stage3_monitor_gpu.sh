#!/usr/bin/env bash
set -euo pipefail

PROJECT=/workspace/realtime_vla_flash_project
OUT="$PROJECT/logs/stage3_gpu_monitor.csv"

echo "timestamp,index,name,memory.used,memory.total,utilization.gpu,utilization.memory,power.draw" > "$OUT"

while true; do
  nvidia-smi \
    --query-gpu=timestamp,index,name,memory.used,memory.total,utilization.gpu,utilization.memory,power.draw \
    --format=csv,noheader,nounits >> "$OUT" || true
  sleep 1
done
