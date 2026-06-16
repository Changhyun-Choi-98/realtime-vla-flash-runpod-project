# Stage 8 Final Project Report

## Final Decision

- Project status: complete
- Final type: limited closed-loop reproduction + probing + profiling + minimal extension
- Full paper reproduction: no
- Paper claim status: partially supported in limited setting
- Blog status: ready

## Headline Conclusion

I successfully ran Realtime-VLA FLASH on Runpod L40S through the official repo and public checkpoints, passed a LIBERO/MuJoCo EGL simulator gate, executed a limited LIBERO Goal closed-loop baseline with 27/30 success, added synchronized server-side latency profiling showing lower p50 draft-route latency than full-route latency in this limited setup, found strong sensitivity to wrist-camera dropout, and tested a minimal WristHealthGuard extension that modestly recovered intermittent dropout but did not solve persistent all-zero dropout. This is not a full paper reproduction, hardware-exact latency reproduction, or full robustness evaluation.

## Project Scope

This project did not treat Realtime-VLA FLASH as a full-paper reproduction. Instead, it checked step by step how far the official repo and public checkpoints could be verified on Runpod L40S. The final outputs are a limited closed-loop baseline, synchronized profiling, a synthetic wrist-camera dropout probe, and a minimal local extension.

## Stage Summary

| Stage | Result | Evidence |
|---|---|---|
| Stage -1 | Simulator feasibility passed | `notes/stage_minus1_report.md` |
| Stage 0 | Scope locked | `notes/stage0_scope_lock.md` |
| Stage 1 | Model environment passed | `notes/stage1_model_env_report.md` |
| Stage 2 | Draft checkpoint load/conversion passed; base unresolved initially | `notes/stage2_checkpoint_conversion_report.md` |
| Stage 2B | `pi0_libero` base resolved, converted, server boot passed | `notes/stage2b_base_checkpoint_resolution_report.md` |
| Stage 3 | One-task closed-loop smoke passed, 2/2 success | `notes/stage3_closed_loop_smoke_report.md` |
| Stage 4 | Limited baseline passed, 27/30 success | `notes/stage4_limited_baseline_report.md` |
| Stage 6 | Synchronized profiling passed | `notes/stage6_synchronized_profiling_report.md` |
| Stage 5 | Wrist-camera dropout probe passed with strong degradation | `notes/stage5_camera_dropout_report.md` |
| Stage 7 | WristHealthGuard extension passed as analyzable limited result | `notes/stage7_wrist_health_guard_report.md` |

## Final Metrics

### Stage 4 Limited Baseline

- Task 0: 9/10
- Task 1: 9/10
- Task 2: 9/10
- Aggregate: 27/30
- Route counts: full=88, draft=276
- Draft/full ratio: 0.758 / 0.242
- Accepted prefix mean: 10.074

### Stage 6 Synchronized Profiling

- Steady-state `policy_time_gpu_sync_ms` p50/p95: 8.083 / 33.501 ms
- Full route p50: 33.156 ms
- Draft route p50: 8.067 ms
- Client roundtrip p50: 11.957 ms
- Claim status: `PARTIALLY_SUPPORTED_LIMITED`

### Stage 5 Robustness Probe

- Clean Stage 4 reference: 27/30
- `wrist_zero_every4`: 4/15
- `wrist_zero_all`: 0/15
- Accepted prefix signal: partial

### Stage 7 Minimal Extension

- `guard_wrist_zero_every4`: 6/15
- `guard_wrist_zero_all`: 0/9
- Recovery every4: +0.133
- Recovery allzero: +0.000

## Interpretation

Stage 4 shows that the official setup can run a limited closed-loop baseline on a small LIBERO Goal subset. Stage 6 gives mechanism-level support that the draft path is faster than the full path in synchronized server-side timing on this hardware and task subset. Stage 5 shows that wrist-camera dropout is a serious weakness in this setup. Stage 7 shows that a simple last-valid-frame guard can recover some intermittent dropout but does not solve persistent observation loss.

## Claim Boundary

This project supports a limited reproduction and probing story. It does not support claims about all LIBERO suites, full paper benchmark metrics, hardware-exact paper latency, or real-world conveyor performance.

## Public Write-Up

The public project write-up is indexed at `https://changhyunchoi.com/project/paper-to-prototype-lab/realtime-vla-flash/`. The claim matrix is ready at `notes/stage8_claim_matrix.md` and `results/stage8_claim_matrix.json`.
