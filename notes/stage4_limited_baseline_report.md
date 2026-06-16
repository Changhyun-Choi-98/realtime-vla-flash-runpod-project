# Stage 4 Limited Baseline Report

## Decision

**PROCEED_TO_STAGE5_ROBUSTNESS_AND_STAGE6_PROFILING**

## What was run

FLASH+Triton `pi0_libero` was evaluated on a small LIBERO Goal subset: tasks 0, 1, and 2, with 10 measured episodes per task. A single task 0 warm-up episode ran first and is excluded from measured metrics.

## What was not run

- No full LIBERO benchmark.
- No all-suite LIBERO evaluation.
- No training.
- No full demonstration dataset download.
- No paper reproduction claim.

## Experimental setup

- Official repo commit: `da6ceccad603695a8a3d6fa14dd410c3aadb536f`
- GPU: NVIDIA L40S
- Suite/tasks: `libero_goal` tasks `[0, 1, 2]`
- Episodes: 1 warm-up excluded, 30 measured
- Seed: `7`
- Server config: `pi0_libero` with `triton` backend
- Base Triton path: `/workspace/realtime_vla_flash_project/converted/base`
- Draft Triton path: `/workspace/realtime_vla_flash_project/converted/draft_goal`
- Render backend: `egl`

## Episode / success summary

| Task | Episodes requested | Episodes completed | Success | Success rate |
|---:|---:|---:|---:|---:|
| 0 | 10 | 10 | 9 | 0.900 |
| 1 | 10 | 10 | 9 | 0.900 |
| 2 | 10 | 10 | 9 | 0.900 |

Aggregate measured result: `27/30` success, success rate `0.900`.

## Route / accepted-prefix summary

- Route counts: `{'full': 88, 'draft': 276}`
- Draft ratio: `0.758`
- Full ratio: `0.242`
- Route counts by task: `{'0': {'full': 16, 'draft': 104}, '1': {'full': 44, 'draft': 84}, '2': {'full': 28, 'draft': 88}}`
- Accepted prefix: `mean=10.074, p50=12.000, p95=12.000, p99=12.000`
- Chunk execution length: `mean=10.074, p50=12.000, p95=12.000, p99=12.000`
- Interpretation: accepted prefix is usually saturated at 12, but it varies in this Stage 4 run; the mean is `10.074` because some task 1 and task 2 inferences accepted shorter or zero prefixes and triggered full fallback behavior.

## Latency summary

- Warm-up first inference client roundtrip: `72177.654 ms`
- Warm-up first inference server policy time: `72174.566 ms`
- Measured run first inference client roundtrips: `[36.667, 26923.978, 17090.191]` ms
- Steady-state server policy time: `mean=34.532, p50=10.676, p95=35.627, p99=41.964` ms
- Steady-state serve time: `mean=34.654, p50=10.810, p95=35.761, p99=42.059` ms
- Steady-state client roundtrip: `mean=35.803, p50=11.996, p95=37.205, p99=43.287` ms
- Caveat: `Stage 4 timing is preliminary and is not paper-level latency reproduction because GPU-synchronized profiling is not implemented here.`

## VRAM summary

- Peak memory used: `7506.000 MiB`
- Mean memory used: `3883.877 MiB`
- GPU memory total: `46068.000 MiB`
- Peak GPU utilization: `78.000%`
- Peak power draw: `149.890 W`

## Failure taxonomy

- Task 0, episode 5: policy behavior/no success after 310 steps.
- Task 1, episode 1: policy behavior/no success after 310 steps.
- Task 2, episode 4: policy behavior/no success after 310 steps.

All three measured failures are classified as policy behavior/no success: the episode completed the maximum rollout horizon without a task success signal. No client/server connection failure, action shape/control failure, simulator runtime failure, or GPU OOM blocked the run.

## Comparison to paper

This is a limited baseline, not full paper reproduction. It uses a different task subset and episode count from a full benchmark. Hardware and software environment may differ from the paper. Latency values are preliminary because this stage does not implement GPU-synchronized profiling.

## Blog-safe conclusion

The limited Stage 4 baseline completed all 30 measured episodes across LIBERO Goal tasks 0, 1, and 2. Aggregate success was 27/30, with each task at 9/10. The run is strong enough to justify Stage 5 robustness probing and Stage 6 synchronized profiling, while remaining clearly below the bar for full paper reproduction.

## What this does not claim

- This is not full LIBERO benchmark reproduction.
- This does not reproduce all paper tasks or suites.
- This does not reproduce the real-world conveyor result.
- This does not claim paper-level latency unless GPU-synchronized profiling is later added.
