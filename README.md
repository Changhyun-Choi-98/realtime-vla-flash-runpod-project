# Realtime-VLA FLASH Runpod Project

Lightweight, public-safe artifacts from a staged Runpod project on
[Realtime-VLA FLASH](https://github.com/dexmal/realtime-vla-flash).

This project is a **limited closed-loop reproduction + probing + profiling + minimal extension**, not a full paper reproduction.

## Final Status

Complete.

| Item | Value |
|---|---|
| Official repo commit | `da6ceccad603695a8a3d6fa14dd410c3aadb536f` |
| Hardware | Runpod NVIDIA L40S |
| Main config | `pi0_libero` |
| Main suite | `libero_goal` |
| Main tasks | 0, 1, 2 |
| Project blog | [Realtime-VLA FLASH project page](https://changhyunchoi.com/project/paper-to-prototype-lab/realtime-vla-flash/) |
| Blog draft | [`notes/stage8_blog_draft.md`](notes/stage8_blog_draft.md) |
| Final report | [`notes/stage8_final_project_report.md`](notes/stage8_final_project_report.md) |
| Claim matrix | [`notes/stage8_claim_matrix.md`](notes/stage8_claim_matrix.md) |

## Headline Result

I successfully ran Realtime-VLA FLASH on Runpod L40S through the official repo and public checkpoints, passed a LIBERO/MuJoCo EGL simulator gate, executed a limited LIBERO Goal closed-loop baseline with **27/30 success**, added synchronized server-side latency profiling showing lower p50 draft-route latency than full-route latency in this limited setup, found strong sensitivity to synthetic wrist-camera dropout, and tested a minimal `WristHealthGuard` extension that modestly recovered intermittent dropout but did not solve persistent all-zero dropout.

This is not a full paper reproduction, hardware-exact latency reproduction, or full robustness evaluation.

## Project Blog

Project-related blog posts are published and indexed here:

- [Realtime-VLA FLASH project page](https://changhyunchoi.com/project/paper-to-prototype-lab/realtime-vla-flash/)

The tracked notes in this repository are the public-safe experiment artifacts behind that write-up.

## Main Results

| Stage | Result | Evidence |
|---|---|---|
| Stage -1 | LIBERO/MuJoCo EGL simulator gate passed | [`notes/stage_minus1_report.md`](notes/stage_minus1_report.md) |
| Stage 1 | Model environment passed | [`notes/stage1_model_env_report.md`](notes/stage1_model_env_report.md) |
| Stage 2/2B | Draft/base checkpoint conversion and server boot passed | [`notes/stage2b_base_checkpoint_resolution_report.md`](notes/stage2b_base_checkpoint_resolution_report.md) |
| Stage 3 | One-task closed-loop smoke passed, 2/2 success | [`notes/stage3_closed_loop_smoke_report.md`](notes/stage3_closed_loop_smoke_report.md) |
| Stage 4 | Limited baseline: 27/30 success on LIBERO Goal tasks 0-2 | [`notes/stage4_limited_baseline_report.md`](notes/stage4_limited_baseline_report.md) |
| Stage 6 | Synchronized profiling: draft route p50 lower than full route p50 | [`notes/stage6_synchronized_profiling_report.md`](notes/stage6_synchronized_profiling_report.md) |
| Stage 5 | Wrist-camera dropout caused strong degradation | [`notes/stage5_camera_dropout_report.md`](notes/stage5_camera_dropout_report.md) |
| Stage 7 | `WristHealthGuard` modestly recovered intermittent dropout | [`notes/stage7_wrist_health_guard_report.md`](notes/stage7_wrist_health_guard_report.md) |
| Stage 8 | Final report, claim matrix, and blog draft ready | [`notes/stage8_final_project_report.md`](notes/stage8_final_project_report.md) |

## Key Metrics

| Metric | Result |
|---|---:|
| Stage 4 task 0 success | 9/10 |
| Stage 4 task 1 success | 9/10 |
| Stage 4 task 2 success | 9/10 |
| Stage 4 aggregate success | 27/30 |
| Stage 4 route counts | full 88, draft 276 |
| Stage 4 draft/full ratio | 0.758 / 0.242 |
| Stage 6 steady-state `policy_time_gpu_sync_ms` p50/p95 | 8.083 / 33.501 ms |
| Stage 6 draft route p50 | 8.067 ms |
| Stage 6 full route p50 | 33.156 ms |
| Stage 5 `wrist_zero_every4` | 4/15 |
| Stage 5 `wrist_zero_all` | 0/15 |
| Stage 7 `guard_wrist_zero_every4` | 6/15 |
| Stage 7 `guard_wrist_zero_all` | 0/9 |

Machine-readable summaries:

- [`results/stage8_final_metrics.json`](results/stage8_final_metrics.json)
- [`results/stage8_project_summary.json`](results/stage8_project_summary.json)
- [`results/stage8_claim_matrix.json`](results/stage8_claim_matrix.json)

## What Is Claimed

- Limited reproduction of the official setup on Runpod L40S.
- Limited closed-loop baseline on LIBERO Goal tasks 0-2.
- Mechanism-level support that the draft route is faster than the full route in synchronized server-side timing for this limited setup.
- Synthetic wrist-camera dropout probe showing strong sensitivity.
- Minimal local research extension showing modest intermittent-dropout recovery.

## Not Claimed

- Not full paper reproduction.
- Not full LIBERO benchmark.
- Not hardware-exact paper latency reproduction.
- Not real-world conveyor reproduction.
- Not general robustness proof.
- Not an upstream-ready robustness method.

## Repository Map

```text
configs/     Stage configs
scripts/     Stage orchestration, parsing, and patch scripts
logs/        Lightweight public-safe logs
results/     Parsed JSON/CSV summaries
figures/     Public-safe summary figures
notes/       Stage reports, claim matrix, blog draft
patches/     Local research patches applied during probes
```

## Artifact Policy

Checkpoints, converted weights, videos, datasets, private endpoints, credentials, tokens, and profiler binaries are excluded from git.

Local-only paths include:

- `checkpoints/`
- `converted/`
- `videos/`
- `datasets/`
- `tmp/`
- large profiler outputs under `profiling/`

The tracked artifacts are intended to be safe for public review and blog publication.

## Reading Order

For a quick review:

1. [`notes/stage8_final_project_report.md`](notes/stage8_final_project_report.md)
2. [`notes/stage8_blog_draft.md`](notes/stage8_blog_draft.md)
3. [`notes/stage8_claim_matrix.md`](notes/stage8_claim_matrix.md)
4. [`results/stage8_final_metrics.json`](results/stage8_final_metrics.json)

For the full experimental trail, read the stage reports in order from Stage -1 through Stage 8.
