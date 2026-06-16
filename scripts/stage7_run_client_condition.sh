#!/usr/bin/env bash
set -euo pipefail

TASK_ID="${1:?task id required}"
NUM_TRIALS="${2:?num trials required}"
RUN_NAME="${3:?run name required}"
DROPOUT_CONDITION="${4:?dropout condition required}"
GUARD_ENABLED="${5:?guard enabled required}"

PROJECT=/workspace/realtime_vla_flash_project
OFFICIAL_DIR=$PROJECT/repos/realtime-vla-flash

source "$PROJECT/.venv-libero/bin/activate"

export PYTHONPATH="$OFFICIAL_DIR/third_party/libero:$OFFICIAL_DIR/packages/openpi-client/src:${PYTHONPATH:-}"
export LIBERO_CONFIG_PATH=/tmp/libero
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
export CUDA_VISIBLE_DEVICES=0

if [ "$DROPOUT_CONDITION" = "none" ]; then
  export STAGE5_CAMERA_PERTURB=0
  export STAGE5_PERTURB_CONDITION=none
  export STAGE5_PERTURB_MODE=none
  export STAGE5_PERTURB_PERIOD=0
else
  export STAGE5_CAMERA_PERTURB=1
  export STAGE5_PERTURB_CONDITION="$DROPOUT_CONDITION"
  export STAGE5_PERTURB_TARGET_KEY=robot0_eye_in_hand_image
  export STAGE5_PERTURB_SEED=7
  if [ "$DROPOUT_CONDITION" = "wrist_zero_every4" ]; then
    export STAGE5_PERTURB_MODE=zero_periodic
    export STAGE5_PERTURB_PERIOD=4
  elif [ "$DROPOUT_CONDITION" = "wrist_zero_all" ]; then
    export STAGE5_PERTURB_MODE=zero_all
    export STAGE5_PERTURB_PERIOD=1
  else
    echo "unknown dropout condition: $DROPOUT_CONDITION" >&2
    exit 2
  fi
fi

export STAGE7_WRIST_HEALTH_GUARD="$GUARD_ENABLED"
export STAGE7_GUARD_MODE=last_valid_cache
export STAGE7_GUARD_TARGET_KEY=observation/wrist_image
export STAGE7_HEALTH_MIN_STD=1.0
export STAGE7_HEALTH_MIN_RANGE=5.0
export STAGE7_CACHE_MAX_AGE_QUERIES=8
export STAGE7_CACHE_RESET_PER_EPISODE=1

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
  --video-out-path "$PROJECT/videos/stage7_wrist_health_guard" \
  --run-name "$RUN_NAME" \
  --seed 7
