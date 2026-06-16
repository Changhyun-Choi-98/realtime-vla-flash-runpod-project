# Stage 7 WristHealthGuard Minimal Extension Report

## Decision

PROCEED_TO_STAGE8_FINAL_BLOG

## What was run

Stage 7 implemented and evaluated `WristHealthGuard`, a minimal inference-time wrist-frame fallback. The run used `pi0_libero` with Triton, EGL rendering, LIBERO Goal tasks 0, 1, and 2, seed 7, and the existing converted base/draft artifacts.

Measured conditions:

- `guard_wrist_zero_every4`: 5 episodes per task, 15 measured episodes total.
- `guard_wrist_zero_all`: 3 episodes per task, 9 measured episodes total.
- `sanity_clean_guard`: task 0, 1 episode, no perturbation, excluded from metrics.

## What was not run

- No full LIBERO benchmark.
- No training.
- No full demonstration dataset download.
- No paper reproduction claim.
- No general robustness claim.

## Extension design

- Observation-health metric: mean, standard deviation, and value range on the post-perturbation wrist image.
- Health threshold: `std >= 1.0` and `range >= 5.0`.
- Cache fallback: if the post-perturbation wrist image is unhealthy, reuse the last valid cached wrist frame from the same episode when available and fresh enough.
- Anti-cheating order: simulator observation, Stage 5 dropout, Stage 7 health check/fallback, then policy request.
- Cache reset rule: cache is reset at the start of every episode.
- Target image key: `observation/wrist_image`.
- Environment variables: `STAGE7_WRIST_HEALTH_GUARD`, `STAGE7_GUARD_MODE`, `STAGE7_GUARD_TARGET_KEY`, `STAGE7_HEALTH_MIN_STD`, `STAGE7_HEALTH_MIN_RANGE`, `STAGE7_CACHE_MAX_AGE_QUERIES`, and `STAGE7_CACHE_RESET_PER_EPISODE`.

## Experimental setup

- Official repo commit: `da6ceccad603695a8a3d6fa14dd410c3aadb536f`.
- GPU: NVIDIA L40S.
- Suite/tasks: `libero_goal`, tasks 0, 1, 2.
- Episode counts: 24 measured Stage 7 episodes plus 1 excluded sanity episode.
- Seed: 7.
- Server config: `pi0_libero`, backend `triton`.
- Base path: `/workspace/realtime_vla_flash_project/converted/base`.
- Draft path: `/workspace/realtime_vla_flash_project/converted/draft_goal`.
- Render backend: EGL.
- Stage 5 perturbation patch status: preserved.
- Stage 6 timing patch status: preserved.
- Stage 7 guard patch status: patched.

## Success summary

| Condition | Task | Episodes requested | Episodes completed | Success | Success rate | Stage 5 no-guard success | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| guard_wrist_zero_every4 | 0 | 5 | 5 | 2 | 0.400 | 0.000 | +0.400 |
| guard_wrist_zero_every4 | 1 | 5 | 5 | 0 | 0.000 | 0.000 | +0.000 |
| guard_wrist_zero_every4 | 2 | 5 | 5 | 4 | 0.800 | 0.800 | +0.000 |
| guard_wrist_zero_all | 0 | 3 | 3 | 0 | 0.000 | 0.000 | +0.000 |
| guard_wrist_zero_all | 1 | 3 | 3 | 0 | 0.000 | 0.000 | +0.000 |
| guard_wrist_zero_all | 2 | 3 | 3 | 0 | 0.000 | 0.000 | +0.000 |

Aggregate intermittent dropout improved from 4/15 without the guard to 6/15 with the guard. Persistent all-zero dropout stayed at 0 successes, as expected when the per-episode cache starts empty and no healthy wrist frame ever arrives.

## Guard behavior summary

For `guard_wrist_zero_every4`, there were 419 guarded inference rows, 96 cache hits, 15 cache misses, 308 cache updates, and 96 image replacements. The cache hit and replacement rates were both 0.229. Wrist images were healthy on 0.735 of rows and unhealthy on 0.265.

For `guard_wrist_zero_all`, there were 433 guarded inference rows, 0 cache hits, 433 cache misses, 0 cache updates, and 0 replacements. Wrist images were unhealthy on all rows. This supports the anti-cheating check: the guard did not recover from persistent all-zero dropout by using a clean pre-perturb frame.

## Route / Accepted-Prefix Summary

| Condition | Route counts | Draft ratio | Full ratio | Accepted prefix mean/p50/p95/p99 |
|---|---|---:|---:|---|
| guard_wrist_zero_every4 | full 123, draft 296 | 0.706 | 0.294 | 8.411 / 12.000 / 12.000 / 12.000 |
| guard_wrist_zero_all | full 157, draft 276 | 0.637 | 0.363 | 6.296 / 3.000 / 12.000 / 12.000 |

Accepted prefix remained saturated at p95/p99 even when success was low, so it remains only a partial uncertainty signal.

## Latency Summary

Synchronized `policy_time_gpu_sync_ms` was available from the Stage 6 patch.

| Condition | policy_time_gpu_sync_ms p50/p95/p99 | client_roundtrip_ms p50/p95/p99 |
|---|---|---|
| guard_wrist_zero_every4 | 8.118 / 33.469 / 43.610 ms | 11.952 / 36.693 / 46.487 ms |
| guard_wrist_zero_all | 8.246 / 33.747 / 701.320 ms | 12.630 / 37.808 / 705.086 ms |

The p50/p95 values are close to Stage 5. The all-zero p99 includes large tail latency outliers and should not be treated as a paper-level latency result.

## VRAM Summary

- Peak memory used: 7566 MiB.
- Mean memory used: 4446.189 MiB.
- Peak GPU utilization: 40%.
- Peak power draw: 164.94 W.

## Failure Taxonomy

All 18 measured failures were classified as perturbation-induced perception failures:

- `guard_wrist_zero_every4`: task 0 had 3 failures, task 1 had 5 failures, task 2 had 1 failure.
- `guard_wrist_zero_all`: each task had 3 failures.

No server/client connection, action-shape/control, simulator runtime, or GPU OOM blocker was observed.

## Interpretation

WristHealthGuard produced a modest positive result for intermittent dropout: aggregate success rose from 0.267 to 0.400. The gain came from task 0; task 1 remained at 0/5 and task 2 was unchanged at 4/5.

The guard did not recover persistent all-zero dropout, which is the expected outcome under per-episode cache reset. The all-zero condition had zero cache hits and zero replacements, so there is no evidence that the guard accessed clean pre-perturb images.

Accepted prefix did not become a reliable success/failure signal. The p95/p99 accepted prefix values stayed saturated at 12 for both guarded conditions.

The guard introduced no obvious p50/p95 latency regression relative to Stage 5, although the p99 tail under all-zero dropout was noisy.

## Blog-safe conclusion

The extension is analyzable and blog-safe as a minimal intervention: a last-valid wrist-frame cache partially recovered intermittent synthetic wrist dropout, but did not solve persistent dropout or failures that varied by task. This is useful as a small engineering result, not as a robustness claim.

## What this does not claim

- This is not full robustness evaluation.
- This is not full paper reproduction.
- This does not test all LIBERO suites.
- This does not test real-world sensor dropout.
- This does not prove general robustness beyond the tested perturbations.
