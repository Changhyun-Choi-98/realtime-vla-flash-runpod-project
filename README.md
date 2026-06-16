# Realtime-VLA FLASH Runpod Project

This repository stores lightweight, public-safe artifacts for a Runpod reproduction/probing/profiling project on Realtime-VLA FLASH.

## Final status

Complete: limited closed-loop reproduction + probing + profiling + minimal extension.

## Main results

- Stage -1 simulator gate passed.
- Stage 4 limited baseline: 27/30 success on LIBERO Goal tasks 0-2.
- Stage 6 synchronized profiling: draft route p50 lower than full route p50 in the limited setting.
- Stage 5 camera dropout: strong degradation.
- Stage 7 WristHealthGuard: modest intermittent-dropout recovery.

## Stage reports

- [Stage -1 simulator gate](notes/stage_minus1_report.md)
- [Stage 0 scope lock](notes/stage0_scope_lock.md)
- [Stage 1 model environment](notes/stage1_model_env_report.md)
- [Stage 2 checkpoint/conversion](notes/stage2_checkpoint_conversion_report.md)
- [Stage 2B base checkpoint resolution](notes/stage2b_base_checkpoint_resolution_report.md)
- [Stage 3 closed-loop smoke](notes/stage3_closed_loop_smoke_report.md)
- [Stage 4 limited baseline](notes/stage4_limited_baseline_report.md)
- [Stage 5 camera dropout probe](notes/stage5_camera_dropout_report.md)
- [Stage 6 synchronized profiling](notes/stage6_synchronized_profiling_report.md)
- [Stage 7 WristHealthGuard extension](notes/stage7_wrist_health_guard_report.md)
- [Stage 8 final project report](notes/stage8_final_project_report.md)
- [Stage 8 blog draft](notes/stage8_blog_draft.md)

## Not claimed

- Not full paper reproduction.
- Not full LIBERO benchmark.
- Not hardware-exact paper latency reproduction.
- Not real-world conveyor reproduction.
- Not general robustness proof.

## Artifact policy

Checkpoints, converted weights, videos, datasets, private endpoints, and profiler binaries are excluded from git.
