# Stage 6 Synchronized Profiling Report

## Decision

**PROCEED_TO_STAGE5_ROBUSTNESS_PROBE**

## What was run

Stage 6 ran a bounded synchronized profiling pass on `libero_goal` tasks 0, 1, and 2. It used one warm-up episode on task 0, excluded from metrics, followed by 3 measured episodes per task for 9 measured episodes total.

## What was not run

- No full LIBERO benchmark.
- No robustness probe.
- No training.
- No full demonstration dataset download.
- No full paper reproduction claim.

## Timing instrumentation

- Source locations audited: `scripts/spec/spec_serve_policy.py`, `scripts/spec/spec_client_libero.py`, `src/openpi/serving/websocket_policy_server.py`, model/runtime timing helpers, and related analysis scripts.
- Existing timings used GPU sync: partially. Existing Triton/model action-generation paths already use `torch.cuda.synchronize()` in several places, but the websocket envelope fields `policy_time_ms` and `serve_time_ms` are wall-clock request timings and did not expose an explicit Stage 6 GPU-sync timing field in `infer.jsonl`.
- Patch summary: Stage 6 added explicit `torch.cuda.synchronize()` before and after server-side action generation when `STAGE6_SYNC_PROFILE=1`, then exported the result through client `infer.jsonl`.
- Fields added: `policy_time_gpu_sync_ms`, `policy_time_wall_ms`, `gpu_sync_before_after_used`, `timing_patch_stage`, `timing_patch_note`.
- Caveats: this measures server-side action generation with torch synchronization plus client roundtrip. It is still a limited Runpod L40S measurement, not hardware-exact paper latency reproduction.

## Experimental setup

- Official repo commit: `da6ceccad603695a8a3d6fa14dd410c3aadb536f`
- GPU: NVIDIA L40S
- Suite/tasks: `libero_goal` tasks `[0, 1, 2]`
- Episodes: 1 warm-up excluded, 9 measured
- Seed: `7`
- Warm-up: task 0, 1 episode
- Server config: `pi0_libero`, Triton backend
- Base Triton path: `/workspace/realtime_vla_flash_project/converted/base`
- Draft Triton path: `/workspace/realtime_vla_flash_project/converted/draft_goal`
- Render backend: `egl`

## Episode summary

- Episodes requested: `9`
- Episodes completed: `9`
- Success count: `9`
- Success rate: `1.000`
- Videos produced: `9` measured videos, kept local-only

## Route / accepted-prefix summary

- Infer log files: `10` including warm-up; `9` measured episode infer logs
- Route counts: `{'full': 18, 'draft': 65}`
- Draft ratio: `0.783`
- Full ratio: `0.217`
- Accepted prefix: `mean=10.699, p50=12.000, p90=12.000, p95=12.000, p99=12.000`
- Chunk execution length: `mean=10.699, p50=12.000, p90=12.000, p95=12.000, p99=12.000`

## Latency summary

- Warm-up first inference: `policy_time_gpu_sync_ms=16654.738`, `serve_time_ms=20914.653`, `client_roundtrip_ms=20915.986`
- First measured inference per task: task 0 `32.776 ms`, task 1 `3825.461 ms`, task 2 `4483.438 ms` for `policy_time_gpu_sync_ms`
- Steady-state synchronized policy time: `p50=8.083`, `p90=33.300`, `p95=33.501`, `p99=592.753` ms
- Steady-state serve time: `p50=10.700`, `p90=35.564`, `p95=36.002`, `p99=594.689` ms
- Steady-state client roundtrip: `p50=11.957`, `p90=37.155`, `p95=38.068`, `p99=596.742` ms
- Draft route synchronized policy time: `p50=8.067`, `p95=8.242`, `p99=598.390` ms
- Full route synchronized policy time: `p50=33.156`, `p95=34.773`, `p99=37.048` ms

The p99 outlier reflects residual first-use behavior that is not removed by excluding only the first inference of each run. Treat p50/p90/p95 as the more stable Stage 6 steady-state indicators unless a later profiling stage adds stricter per-route warm-up.

## VRAM summary

- Peak memory used: `7506 MiB`
- Mean memory used: `2244.890 MiB`
- Peak GPU utilization: `90%`
- Peak power draw: `142.98 W`

## Comparison to paper

The paper reports 58.0 ms full-inference rounds, 19.1 ms task level average latency, and 7.8 ms fastest flash-path round. This Stage 6 run used a Runpod NVIDIA L40S and a limited LIBERO Goal subset, not the full paper benchmark or hardware-exact setup. The synchronized route-level numbers support the latency mechanism in a limited setting, but they do not reproduce the full paper claim.

## Blog-safe conclusion

In this limited Stage 6 profile, synchronized server-side FLASH timing was present for all measured inference rows. Draft route p50 was about `8.067 ms`, full route p50 was about `33.156 ms`, and measured rollout integration remained healthy at `9/9` success. This is blog-safe as a limited profiling result with clear caveats.

## What this does not claim

- This is not full LIBERO benchmark reproduction.
- This does not reproduce all four LIBERO suites.
- This does not reproduce the real-world conveyor result.
- This does not claim hardware-exact paper latency unless hardware and metric match.
