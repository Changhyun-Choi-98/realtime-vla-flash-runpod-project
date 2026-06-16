# Stage 3 Failure Taxonomy

## Server startup

Server fails to bind port 8000, crashes before readiness, cannot load converted base/draft artifacts, or reports model initialization errors.

## Client connection

The `.venv-libero` client cannot connect to the websocket policy server, times out before inference, or receives protocol-level connection errors.

## Protocol/API mismatch

The server and client disagree on request or response fields, including missing `actions`, missing timing dictionaries, or incompatible observation key expectations.

## Action shape/control

The returned action chunk has the wrong rank, horizon, or action dimension, or LIBERO/robosuite rejects the action during `env.step`.

## Simulator runtime

MuJoCo, robosuite, LIBERO, EGL, or camera rendering fails during reset, rollout, rendering, or cleanup. Ignored cleanup exceptions after successful episode completion should be recorded but not treated as rollout failure unless they change exit status or artifact creation.

## Policy behavior/no success

The server and simulator run end to end, episodes complete, logs are parseable, but no episode reaches success.

## Logging/observability

An episode completes but `episode_log.json`, `trace.jsonl`, `infer.jsonl`, video files, or GPU monitor logs are missing or unreadable.

## GPU OOM

CUDA out-of-memory appears in server or client logs, the server process dies during inference, or GPU memory exhaustion prevents episode completion.

## Latency/profiling invalidity

Timing values are missing, dominated by cold-start behavior, not GPU-synchronized, or gathered from too few samples to support latency claims.
