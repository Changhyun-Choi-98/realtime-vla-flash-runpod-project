# Stage 6 Latency Claim Assessment

## Paper claim

The paper reference values used for this assessment are:

- Full-inference reference rounds: `58.0 ms`
- Task level FLASH+Triton average latency: `19.1 ms`
- Fastest flash-path round: `7.8 ms`

## Our measurement method

Stage 6 added server-side `torch.cuda.synchronize()` before and after action generation while `STAGE6_SYNC_PROFILE=1`. It records `policy_time_gpu_sync_ms` and retains existing `serve_time_ms` and `client_roundtrip_ms`.

## Comparable fields

- `policy_time_gpu_sync_ms` is the closest Stage 6 field to server-side synchronized action-generation latency.
- Route-specific draft and full timing can be compared qualitatively to the paper latency motivation.

## Non-comparable fields

- Client roundtrip includes local websocket/client overhead and is not the same as paper kernel-level or benchmark-level timing.
- This run uses Runpod NVIDIA L40S hardware and only three LIBERO Goal tasks.
- This run does not cover all paper tasks, all suites, or the real-world conveyor setting.

## Result

Measured Stage 6 route-level synchronized timing:

- Draft route `policy_time_gpu_sync_ms`: `p50=8.067 ms`, `p95=8.242 ms`, `p99=598.390 ms`
- Full route `policy_time_gpu_sync_ms`: `p50=33.156 ms`, `p95=34.773 ms`, `p99=37.048 ms`
- Steady-state overall `policy_time_gpu_sync_ms`: `p50=8.083 ms`, `p90=33.300 ms`, `p95=33.501 ms`, `p99=592.753 ms`

The high draft p99 comes from residual first-use behavior and should not be described as stable steady-state latency.

## Claim status

`PARTIALLY_SUPPORTED_LIMITED`

## Recommended wording for blog

In a limited LIBERO Goal subset on Runpod L40S, GPU-synchronized server-side profiling showed draft-route p50 latency around `8.1 ms` and full-route p50 latency around `33.2 ms`. These numbers support the mechanism-level latency story in this environment, but they are not a full or hardware-exact reproduction of the paper's reported benchmark latency.
