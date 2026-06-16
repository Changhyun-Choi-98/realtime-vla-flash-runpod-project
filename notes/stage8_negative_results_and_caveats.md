# Stage 8 Negative Results And Caveats

## 주요 negative result

- Stage 5 synthetic wrist-camera dropout caused strong degradation.
- `wrist_zero_every4` dropped from Stage 4 clean 27/30 aggregate success to 4/15 in the matched perturbation probe.
- `wrist_zero_all` dropped to 0/15.
- Stage 7 WristHealthGuard improved intermittent dropout only modestly, from 4/15 to 6/15.
- Stage 7 did not recover persistent all-zero dropout, remaining at 0/9.
- Accepted prefix remained saturated at high percentiles under failure, so it was only a partial uncertainty signal.

## Latency caveats

- Stage 4 latency was wall-clock only and explicitly preliminary.
- Stage 6 added synchronized server-side timing, but the run used Runpod L40S and a limited LIBERO Goal task subset.
- Stage 6 p99 values include residual first-use/tail behavior and should be interpreted cautiously.
- The project provides mechanism-level support in a limited setting, not hardware-exact paper latency reproduction.

## Scope caveats

- No full LIBERO benchmark was run.
- No all-suite evaluation was run.
- No real-world conveyor result was attempted.
- No training was performed.
- No full demonstration dataset was downloaded.
- The WristHealthGuard patch is a minimal local research extension, not an upstream feature.

## Blog-safe framing

Use:

- limited reproduction
- limited closed-loop baseline
- partial support
- mechanism-level support
- independent Runpod L40S profiling
- synthetic wrist-camera dropout
- minimal local research extension

Avoid claiming:

- paper-level reproduction
- hardware-exact latency
- full robustness
- real-world transfer
- all-suite benchmark coverage
