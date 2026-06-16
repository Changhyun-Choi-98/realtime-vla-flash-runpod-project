#!/usr/bin/env bash
set -euo pipefail

PROJECT=/workspace/realtime_vla_flash_project
OFFICIAL_DIR=$PROJECT/repos/realtime-vla-flash
cd "$OFFICIAL_DIR"

export CUDA_VISIBLE_DEVICES=0

exec uv run python scripts/spec/spec_serve_policy.py \
  --config pi0_libero \
  --base-triton-path "$PROJECT/converted/base" \
  --draft-triton-path "$PROJECT/converted/draft_goal" \
  --task-suite-name libero_goal \
  --backend triton
