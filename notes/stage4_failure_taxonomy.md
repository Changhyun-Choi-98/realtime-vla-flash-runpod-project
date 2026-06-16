# Stage 4 Failure Taxonomy

## No failure

Episode completed successfully and all required logs were produced.

## Policy behavior/no success

Episode ran to the configured horizon without a success signal. This is the observed Stage 4 failure class for the three measured failures.

## Per-task long-horizon failure

Episode requires extended manipulation or recovery behavior and reaches the maximum step budget without success.

## Gripper/contact failure

The policy reaches the object or target area but fails grasp, release, drawer, contact, or placement dynamics.

## Perception/pose failure

The policy appears to act on an incorrect object pose, camera interpretation, or spatial relationship.

## Route/fallback instability

Accepted prefix collapses, full fallback frequency spikes, or route behavior changes in a way that correlates with failures.

## Client/server connection failure

The `.venv-libero` client cannot connect to the policy server, loses the websocket connection, or receives malformed responses.

## Action shape/control failure

The returned action chunk has invalid rank, horizon, or dimension, or robosuite rejects the command.

## Simulator runtime failure

MuJoCo, robosuite, LIBERO, EGL, rendering, or environment stepping fails during rollout.

## Logging/observability failure

Episode logs, infer logs, trace logs, videos, or GPU monitor data are missing or unreadable.

## GPU OOM

CUDA out-of-memory or GPU process death prevents completion.

## Latency/profiling invalidity

Timing values are missing, dominated by warm-up/cold-start, not GPU-synchronized, or insufficient for paper-level latency claims.
