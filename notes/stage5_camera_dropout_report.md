# Stage 5 Camera Dropout Robustness Report

## Decision

PROCEED_TO_STAGE7_MINIMAL_EXTENSION

The wrist-camera perturbation produced a clear measurable effect versus the Stage 4 clean baseline. Stage 4 clean success was 27/30 (0.900). In Stage 5, `wrist_zero_every4` completed all 15 measured episodes with 4/15 success (0.267), and `wrist_zero_all` completed all 15 measured episodes with 0/15 success (0.000).

## What was run

- One sanity clean patched-client episode on LIBERO Goal task 0, excluded from robustness metrics.
- `wrist_zero_every4` on LIBERO Goal tasks 0, 1, and 2, with 5 episodes per task.
- `wrist_zero_all` on LIBERO Goal tasks 0, 1, and 2, with 5 episodes per task.
- Server: `pi0_libero`, Triton backend, converted base and draft artifacts.
- Client: LIBERO EGL simulator through `.venv-libero`.

## What was not run

- No full LIBERO benchmark.
- No training.
- No full demonstration dataset download.
- No paper reproduction claim.
- No robustness generalization claim beyond this small task subset and these two perturbations.

## Perturbation design

- Target image key: `robot0_eye_in_hand_image`.
- Policy request field changed: `observation/wrist_image`.
- `wrist_zero_every4`: zeroed the wrist image when `policy_query_index % 4 == 0`.
- `wrist_zero_all`: zeroed the wrist image on every policy query.
- Seed: 7.
- Baseline reference: Stage 4 limited clean baseline.

## Experimental setup

- Official repo commit: `da6ceccad603695a8a3d6fa14dd410c3aadb536f`.
- GPU: NVIDIA L40S.
- Suite/tasks: `libero_goal`, tasks 0, 1, 2.
- Server config: `pi0_libero`.
- Base path: `/workspace/realtime_vla_flash_project/converted/base`.
- Draft path: `/workspace/realtime_vla_flash_project/converted/draft_goal`.
- Render backend: EGL.
- Stage 6 timing patch status: preserved.
- Stage 5 perturbation patch status: applied, with trace/infer fields logged.

## Success summary

| Condition | Task | Episodes requested | Episodes completed | Success | Success rate | Success drop vs Stage 4 |
|---|---:|---:|---:|---:|---:|---:|
| wrist_zero_every4 | 0 | 5 | 5 | 0 | 0.000 | 0.900 |
| wrist_zero_every4 | 1 | 5 | 5 | 0 | 0.000 | 0.900 |
| wrist_zero_every4 | 2 | 5 | 5 | 4 | 0.800 | 0.100 |
| wrist_zero_all | 0 | 5 | 5 | 0 | 0.000 | 0.900 |
| wrist_zero_all | 1 | 5 | 5 | 0 | 0.000 | 0.900 |
| wrist_zero_all | 2 | 5 | 5 | 0 | 0.000 | 0.900 |

## Route / accepted-prefix summary

- Stage 4 clean route ratio: draft/full = 0.758 / 0.242.
- `wrist_zero_every4`: route counts `{"full": 154, "draft": 325}`, draft/full = 0.678 / 0.322.
- `wrist_zero_all`: route counts `{"full": 269, "draft": 424}`, draft/full = 0.612 / 0.388.
- `wrist_zero_every4` accepted prefix mean/p50/p95/p99: 7.929 / 12.000 / 12.000 / 12.000.
- `wrist_zero_all` accepted prefix mean/p50/p95/p99: 6.550 / 9.000 / 12.000 / 12.000.
- Perturbation fields were complete: 127/479 every-4 inference rows were perturbed, and 693/693 all-zero inference rows were perturbed.

## Latency summary

Synchronized server-side timing from the Stage 6 patch was present.

- `wrist_zero_every4` policy_time_gpu_sync_ms p50/p95/p99: 8.279 / 33.703 / 43.770.
- `wrist_zero_every4` client_roundtrip_ms p50/p95/p99: 12.783 / 37.671 / 52.209.
- `wrist_zero_all` policy_time_gpu_sync_ms p50/p95/p99: 8.289 / 33.671 / 46.745.
- `wrist_zero_all` client_roundtrip_ms p50/p95/p99: 12.921 / 37.625 / 49.541.

These timings are useful for this robustness probe, but they are not a full paper latency reproduction.

## VRAM summary

- Peak memory used: 7608 MiB.
- Mean memory used: 4399.773 MiB.
- Peak GPU utilization: 56%.
- Peak power draw: 171.5 W.

## Failure taxonomy

All measured failures were classified as perturbation-induced perception failures. There were no server/client connection failures, action shape/control failures, simulator runtime failures, or GPU OOM failures.

## Interpretation

- Wrist-camera dropout reduced success sharply. The periodic dropout condition fell from the Stage 4 clean 0.900 aggregate success rate to 0.267, while full wrist dropout fell to 0.000.
- The effect was task-specific. Task 2 retained 4/5 success under every-4 dropout, while tasks 0 and 1 collapsed to 0/5.
- Accepted-prefix length dropped in mean for both perturbations and dropped in p50 for full wrist dropout, but p95/p99 stayed saturated at 12. This suggests accepted prefix is a partial uncertainty signal here, not a complete failure detector.
- Full-path ratio increased under perturbation, from 0.242 in Stage 4 to 0.322 for every-4 and 0.388 for all-zero.
- The observed failure mode is consistent with close-range visual information being important for these manipulation tasks.

## Blog-safe conclusion

In this limited LIBERO Goal subset, zeroing the wrist camera substantially degraded FLASH+Triton closed-loop behavior. Periodic wrist dropout reduced aggregate success to 4/15, and full wrist dropout reduced it to 0/15. The route mix shifted toward more full-path calls and accepted-prefix means dropped, but high-percentile accepted-prefix values remained saturated, so accepted-prefix length alone should not be treated as a reliable robustness monitor.

## What this does not claim

- This is not full robustness evaluation.
- This is not full paper reproduction.
- This does not test all LIBERO suites.
- This does not test real-world camera corruption.
- This does not prove general robustness beyond the tested perturbations.

## Notes

The first Stage 5 execution exposed a logging-only issue: perturbation fields were not copied into infer records. The client patch was fixed and the Stage 5 output directory was rerun cleanly so the final artifacts include explicit `stage5_perturb_*` fields. The final metrics in this report come from the corrected run.
