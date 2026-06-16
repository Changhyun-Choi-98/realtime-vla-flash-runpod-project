#!/usr/bin/env bash
set -euo pipefail

PROJECT=/workspace/realtime_vla_flash_project
OFFICIAL_DIR=$PROJECT/repos/realtime-vla-flash
LOG="$PROJECT/logs/stage2b_server_boot_smoke.txt"
OUT="$PROJECT/results/stage2b_server_boot_smoke.json"

cd "$OFFICIAL_DIR"

if [ ! -s "$PROJECT/converted/draft_goal/draft_triton.pkl" ] || [ ! -d "$PROJECT/converted/base" ] || ! find "$PROJECT/converted/base" -type f | grep -q .; then
  cat > "$LOG" <<'EOF'
SERVER_BOOT_STATUS=SKIPPED
reason=base or draft converted artifact missing
EOF
  python - <<PY
import json
import pathlib
payload = {
    "status": "skipped",
    "reason": "base or draft converted artifact missing",
    "ready_inferred": False,
}
pathlib.Path("$OUT").write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
PY
  exit 0
fi

set +e
setsid bash -c "timeout 180s uv run python scripts/spec/spec_serve_policy.py \
  --config pi0_libero \
  --base-triton-path '$PROJECT/converted/base' \
  --draft-triton-path '$PROJECT/converted/draft_goal' \
  --task-suite-name libero_goal \
  --backend triton" > "$LOG" 2>&1 &
SERVER_PID=$!

READY=0
for _ in $(seq 1 180); do
  if grep -Eiq "server|listening|started|ready" "$LOG" 2>/dev/null; then
    READY=1
    break
  fi
  if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | grep -q ':8000 '; then
    READY=1
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    break
  fi
  sleep 1
done

ALIVE=0
if kill -0 "$SERVER_PID" 2>/dev/null; then
  ALIVE=1
  kill -- "-$SERVER_PID" 2>/dev/null || kill "$SERVER_PID" 2>/dev/null || true
  sleep 2
  kill -9 -- "-$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null
else
  wait "$SERVER_PID"
fi
STATUS=$?
set -e

python - <<PY
import pathlib
import re
log_path = pathlib.Path("$LOG")
if log_path.exists():
    text = log_path.read_text(errors="ignore")
    text = re.sub(r"host: [^,\\n]+", "host: redacted", text)
    text = re.sub(r"ip: \\d{1,3}(?:\\.\\d{1,3}){3}", "ip: redacted", text)
    log_path.write_text(text, encoding="utf-8")
PY

python - <<PY
import json
import pathlib
log_path = pathlib.Path("$LOG")
log = log_path.read_text(errors="ignore") if log_path.exists() else ""
payload = {
    "status": "ready" if int("$READY") == 1 else "failure",
    "exit_status": int("$STATUS"),
    "ready_inferred": bool(int("$READY")),
    "process_alive_during_probe": bool(int("$ALIVE")),
    "readiness_evidence": "log/port readiness pattern or process remained alive" if int("$READY") == 1 else None,
    "log_tail": log[-4000:],
}
pathlib.Path("$OUT").write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
PY
