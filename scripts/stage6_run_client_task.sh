#!/usr/bin/env bash
set -euo pipefail

TASK_ID="${1:?task id required}"
NUM_TRIALS="${2:?num trials required}"
RUN_NAME="${3:?run name required}"

PROJECT=/workspace/realtime_vla_flash_project
OFFICIAL_DIR=$PROJECT/repos/realtime-vla-flash

source "$PROJECT/.venv-libero/bin/activate"

export PYTHONPATH="$OFFICIAL_DIR/third_party/libero:$OFFICIAL_DIR/packages/openpi-client/src:${PYTHONPATH:-}"
export LIBERO_CONFIG_PATH=/tmp/libero
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
export CUDA_VISIBLE_DEVICES=0

mkdir -p /tmp/libero
cat > /tmp/libero/config.yaml <<EOF
benchmark_root: $OFFICIAL_DIR/third_party/libero/libero/libero
bddl_files: $OFFICIAL_DIR/third_party/libero/libero/libero/bddl_files
init_states: $OFFICIAL_DIR/third_party/libero/libero/libero/init_files
datasets: $OFFICIAL_DIR/third_party/libero/libero/datasets
assets: $OFFICIAL_DIR/third_party/libero/libero/libero/assets
EOF

cd "$OFFICIAL_DIR"

python scripts/spec/spec_client_libero.py \
  --host 127.0.0.1 \
  --port 8000 \
  --task-suite-name libero_goal \
  --task "$TASK_ID" \
  --num-trials-per-task "$NUM_TRIALS" \
  --video-out-path "$PROJECT/videos/stage6_sync_profile" \
  --run-name "$RUN_NAME" \
  --seed 7
