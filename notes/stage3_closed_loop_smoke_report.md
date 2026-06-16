# Stage 3 Closed-loop Smoke Report

## Decision

**PROCEED_TO_STAGE4_LIMITED_BASELINE**

## What was run

A bounded Stage 3 smoke test ran one LIBERO Goal task (`task_id=0`) for two trials only. It connected the converted `pi0_libero` Triton base artifact and converted `draft_libero_goal` draft artifact to the official policy server, then used the `.venv-libero` client with EGL offscreen rendering.

## Server setup

- Command: `scripts/stage3_run_server.sh`
- Config: `pi0_libero`
- Backend: `triton`
- Base Triton path: `/workspace/realtime_vla_flash_project/converted/base`
- Draft Triton path: `/workspace/realtime_vla_flash_project/converted/draft_goal`
- Ready: `True`
- Alive during client: `True`

## Client setup

- Command: `scripts/stage3_run_client_smoke.sh`
- Environment: `.venv-libero`
- Suite: `libero_goal`
- Task: `0`
- Trials: `2`
- Seed: `7`
- Render backend: `egl`

## Episode summary

| Suite | Task | Episodes requested | Episodes completed | Success | Success rate |
|---|---:|---:|---:|---:|---:|
| libero_goal | 0 | 2 | 2 | 2 | 1.000 |

## Route / accepted prefix summary

- Infer calls: `21`
- Route counts: `{'full': 2, 'draft': 19}`
- Flash/draft counts: `{'draft': 19, 'full': 2}`
- Accepted prefix mean/p50/p95: `12.000` / `12.000` / `12.000`
- Missing fields: `[]`

## Latency summary

- Server policy time p50/p95: `10.805 ms` / `17393.080 ms`
- Serve time p50/p95: `10.931 ms` / `17393.295 ms`
- Client roundtrip p50/p95: `12.289 ms` / `17394.629 ms`
- Caveat: `Stage 3 smoke timing is preliminary and not paper-level latency reproduction.` The p95 is dominated by cold-start and first large inference behavior in this two-episode smoke.

## VRAM summary

- Peak memory used: `7390.000 MiB`
- Mean memory used: `1918.058 MiB`
- GPU memory total: `46068.000 MiB`
- Peak GPU utilization: `29.000%`
- Peak power draw: `127.390 W`

## Failure analysis

No blocking failure. Two requested episodes completed successfully. The client emitted ignored EGL cleanup exceptions after completion; these did not change the zero client exit status or the produced episode artifacts.

## Blog-safe conclusion

The Stage 3 one-task closed-loop smoke passed as an integration test: server readiness, client connection, action shape `(50, 7)`, simulator execution, episode logging, infer/trace logs, videos, and two completed successful task 0 episodes were observed. This is enough to proceed to a limited Stage 4 baseline probe, with strong caveats that this is still only a tiny smoke test.

## What this does not claim

- This is not full paper reproduction.
- This is not full LIBERO benchmark reproduction.
- This does not claim paper-level success rate.
- This does not claim paper latency reproduction unless GPU-synchronized timing exists.
