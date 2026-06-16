#!/usr/bin/env bash
set -euo pipefail

PROJECT=/workspace/realtime_vla_flash_project
LOG_SERVER="$PROJECT/logs/stage5_server.txt"
LOG_ORCH="$PROJECT/logs/stage5_orchestrate.txt"

cd "$PROJECT"

chmod +x \
  scripts/stage5_run_server.sh \
  scripts/stage5_run_client_condition.sh \
  scripts/stage5_monitor_gpu.sh

redact_server_log() {
  python3 - <<PY
import pathlib
import re
log_path = pathlib.Path("$LOG_SERVER")
if log_path.exists():
    text = log_path.read_text(errors="ignore")
    text = re.sub(r"host: [^,\\n]+", "host: redacted", text)
    text = re.sub(r"ip: \\d{1,3}(?:\\.\\d{1,3}){3}", "ip: redacted", text)
    text = re.sub(r"Connection from \\([^\\n]+\\)", "Connection from (redacted)", text)
    log_path.write_text(text, encoding="utf-8")
PY
}

set +e

scripts/stage5_monitor_gpu.sh &
GPU_MON_PID=$!

setsid scripts/stage5_run_server.sh > "$LOG_SERVER" 2>&1 &
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

SANITY_STATUS=999
EVERY4_TASK0_STATUS=999
EVERY4_TASK1_STATUS=999
EVERY4_TASK2_STATUS=999
ALL_TASK0_STATUS=999
ALL_TASK1_STATUS=999
ALL_TASK2_STATUS=999

if [ "$READY" -eq 1 ]; then
  timeout 1800s scripts/stage5_run_client_condition.sh 0 1 stage5_sanity_clean_task0_seed7_n1 none \
    > "$PROJECT/logs/stage5_sanity_clean_task0_n1.txt" 2>&1
  SANITY_STATUS=$?

  timeout 7200s scripts/stage5_run_client_condition.sh 0 5 stage5_wrist_zero_every4_task0_seed7_n5 wrist_zero_every4 \
    > "$PROJECT/logs/stage5_wrist_zero_every4_task0_n5.txt" 2>&1
  EVERY4_TASK0_STATUS=$?
  timeout 7200s scripts/stage5_run_client_condition.sh 1 5 stage5_wrist_zero_every4_task1_seed7_n5 wrist_zero_every4 \
    > "$PROJECT/logs/stage5_wrist_zero_every4_task1_n5.txt" 2>&1
  EVERY4_TASK1_STATUS=$?
  timeout 7200s scripts/stage5_run_client_condition.sh 2 5 stage5_wrist_zero_every4_task2_seed7_n5 wrist_zero_every4 \
    > "$PROJECT/logs/stage5_wrist_zero_every4_task2_n5.txt" 2>&1
  EVERY4_TASK2_STATUS=$?

  timeout 7200s scripts/stage5_run_client_condition.sh 0 5 stage5_wrist_zero_all_task0_seed7_n5 wrist_zero_all \
    > "$PROJECT/logs/stage5_wrist_zero_all_task0_n5.txt" 2>&1
  ALL_TASK0_STATUS=$?
  timeout 7200s scripts/stage5_run_client_condition.sh 1 5 stage5_wrist_zero_all_task1_seed7_n5 wrist_zero_all \
    > "$PROJECT/logs/stage5_wrist_zero_all_task1_n5.txt" 2>&1
  ALL_TASK1_STATUS=$?
  timeout 7200s scripts/stage5_run_client_condition.sh 2 5 stage5_wrist_zero_all_task2_seed7_n5 wrist_zero_all \
    > "$PROJECT/logs/stage5_wrist_zero_all_task2_n5.txt" 2>&1
  ALL_TASK2_STATUS=$?
else
  echo "server did not become ready" > "$PROJECT/logs/stage5_sanity_clean_task0_n1.txt"
  for f in \
    stage5_wrist_zero_every4_task0_n5 \
    stage5_wrist_zero_every4_task1_n5 \
    stage5_wrist_zero_every4_task2_n5 \
    stage5_wrist_zero_all_task0_n5 \
    stage5_wrist_zero_all_task1_n5 \
    stage5_wrist_zero_all_task2_n5; do
    echo "server did not become ready" > "$PROJECT/logs/${f}.txt"
  done
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

python3 - <<PY > "$PROJECT/results/stage5_orchestration.json"
import json
payload = {
    "server_ready": bool(int("$READY")),
    "server_alive_before_cleanup": bool(int("$SERVER_ALIVE")),
    "exit_status": {
        "sanity": int("$SANITY_STATUS"),
        "wrist_zero_every4_task0": int("$EVERY4_TASK0_STATUS"),
        "wrist_zero_every4_task1": int("$EVERY4_TASK1_STATUS"),
        "wrist_zero_every4_task2": int("$EVERY4_TASK2_STATUS"),
        "wrist_zero_all_task0": int("$ALL_TASK0_STATUS"),
        "wrist_zero_all_task1": int("$ALL_TASK1_STATUS"),
        "wrist_zero_all_task2": int("$ALL_TASK2_STATUS")
    }
}
print(json.dumps(payload, indent=2))
PY

python3 - <<PY > "$PROJECT/results/stage5_decision.json"
import json
import pathlib
orch = json.loads(pathlib.Path("$PROJECT/results/stage5_orchestration.json").read_text())
if not orch.get("server_ready"):
    decision = "BLOCKED_SERVER_NOT_READY"
elif any(v != 0 for k, v in orch["exit_status"].items() if k != "sanity"):
    decision = "BLOCKED_CLIENT_OR_ENV_RUNTIME"
else:
    decision = "PROCEED_PARSE_STAGE5_RESULTS"
payload = {
    "decision": decision,
    "orchestration": orch
}
print(json.dumps(payload, indent=2))
PY

cat "$PROJECT/results/stage5_decision.json" | tee "$LOG_ORCH"
