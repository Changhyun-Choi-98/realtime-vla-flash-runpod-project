#!/usr/bin/env bash
set -euo pipefail

PROJECT=/workspace/realtime_vla_flash_project
OFFICIAL_DIR=$PROJECT/repos/realtime-vla-flash
cd "$OFFICIAL_DIR"

LOG="$PROJECT/logs/stage2_server_boot_smoke.txt"
OUT="$PROJECT/results/stage2_server_boot_smoke.json"

set +e
timeout 120s uv run python scripts/spec/spec_serve_policy.py \
  --config pi0_libero \
  --base-triton-path "$PROJECT/converted/base" \
  --draft-triton-path "$PROJECT/converted/draft_goal" \
  --task-suite-name libero_goal \
  --backend triton \
  2>&1 | tee "$LOG"
STATUS=${PIPESTATUS[0]}
set -e

python - <<PY
import json
import pathlib

status = int("$STATUS")
log_path = pathlib.Path("$LOG")
log = log_path.read_text(errors="ignore") if log_path.exists() else ""
payload = {
    "exit_status": status,
    "ready_inferred": ("8000" in log.lower() or "server" in log.lower() or "listening" in log.lower()),
    "log_tail": log[-4000:],
}
pathlib.Path("$OUT").write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
PY
