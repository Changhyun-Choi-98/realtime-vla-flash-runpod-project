#!/usr/bin/env bash
set -euo pipefail

PROJECT=/workspace/realtime_vla_flash_project
LOG_SERVER="$PROJECT/logs/stage3_server.txt"
LOG_CLIENT="$PROJECT/logs/stage3_client_task0_n2.txt"
LOG_ORCH="$PROJECT/logs/stage3_orchestrate.txt"

cd "$PROJECT"

chmod +x scripts/stage3_run_server.sh scripts/stage3_run_client_smoke.sh scripts/stage3_monitor_gpu.sh

redact_server_log() {
  python3 - <<PY
import pathlib
import re
log_path = pathlib.Path("$LOG_SERVER")
if log_path.exists():
    text = log_path.read_text(errors="ignore")
    text = re.sub(r"host: [^,\\n]+", "host: redacted", text)
    text = re.sub(r"ip: \\d{1,3}(?:\\.\\d{1,3}){3}", "ip: redacted", text)
    log_path.write_text(text, encoding="utf-8")
PY
}

set +e

scripts/stage3_monitor_gpu.sh &
GPU_MON_PID=$!

setsid scripts/stage3_run_server.sh > "$LOG_SERVER" 2>&1 &
SERVER_PID=$!

READY=0
for _ in $(seq 1 240); do
  if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | grep -q ':8000 '; then
    READY=1
    break
  fi
  if grep -Eiq "server|listening|started|ready|8000" "$LOG_SERVER" 2>/dev/null; then
    READY=1
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    break
  fi
  sleep 1
done

CLIENT_STATUS=999
if [ "$READY" -eq 1 ]; then
  timeout 1800s scripts/stage3_run_client_smoke.sh > "$LOG_CLIENT" 2>&1
  CLIENT_STATUS=$?
else
  echo "server did not become ready" > "$LOG_CLIENT"
fi

SERVER_ALIVE=0
if kill -0 "$SERVER_PID" 2>/dev/null; then
  SERVER_ALIVE=1
fi

kill -- "-$SERVER_PID" 2>/dev/null || kill "$SERVER_PID" 2>/dev/null || true
kill "$GPU_MON_PID" 2>/dev/null || true
sleep 2
kill -9 -- "-$SERVER_PID" 2>/dev/null || true
kill -9 "$GPU_MON_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true
wait "$GPU_MON_PID" 2>/dev/null || true
redact_server_log

set -e

python3 - <<PY > "$PROJECT/results/stage3_decision.json"
import json
import pathlib
import re

server_log_path = pathlib.Path("$LOG_SERVER")
client_log_path = pathlib.Path("$LOG_CLIENT")
server_log = server_log_path.read_text(errors="ignore") if server_log_path.exists() else ""
client_log = client_log_path.read_text(errors="ignore") if client_log_path.exists() else ""

ready = bool(int("$READY"))
client_status = int("$CLIENT_STATUS")
server_alive = bool(int("$SERVER_ALIVE"))

if not ready:
    decision = "BLOCKED_SERVER_NOT_READY_DURING_CLIENT"
elif client_status != 0 and re.search(r"connect|connection|refused|websocket", client_log, re.I):
    decision = "BLOCKED_CLIENT_CONNECTION"
elif client_status != 0 and re.search(r"shape|control|action", client_log, re.I):
    decision = "BLOCKED_ACTION_SHAPE_OR_CONTROL"
elif client_status != 0 and re.search(r"cuda.*out of memory|CUDA out of memory|OOM", server_log + client_log, re.I):
    decision = "BLOCKED_GPU_OOM"
elif client_status != 0:
    decision = "BLOCKED_ENV_RUNTIME"
else:
    decision = "PROCEED_PARSE_STAGE3_RESULTS"

payload = {
    "server_ready": ready,
    "server_alive_before_cleanup": server_alive,
    "client_exit_status": client_status,
    "decision": decision,
    "server_log_tail": server_log[-3000:],
    "client_log_tail": client_log[-3000:],
}
print(json.dumps(payload, indent=2))
PY

cat "$PROJECT/results/stage3_decision.json" | tee "$LOG_ORCH"
