# Stage 7 Failure Taxonomy

## Observed Classes

- no failure: successful completed episodes.
- intermittent dropout recovered: successes under `guard_wrist_zero_every4` where cached wrist frames were available.
- persistent dropout not recoverable: all `guard_wrist_zero_all` episodes failed with no valid cache.
- cache miss due no prior valid frame: all-zero rows had 433 cache misses and 0 cache hits.
- perturbation-induced perception failure: the concrete failure mode for all failed Stage 7 episodes.
- accepted-prefix saturation despite failure: p95/p99 accepted prefix remained 12 even with low success.

## Not Observed

- stale-cache-induced failure: not directly identified from logs.
- gripper/contact failure: not separated from perception failures in the available logs.
- object localization failure: possible but not directly labeled.
- route/fallback instability: route mix changed, but no protocol instability was observed.
- server/client connection failure: not observed.
- action shape/control failure: not observed.
- simulator runtime failure: not observed as a blocking runtime failure.
- logging/observability failure: not observed.
- GPU OOM: not observed.

## Per-Condition Summary

`guard_wrist_zero_every4` completed 15 measured episodes with 6 successes and 9 failures. Failures were task dependent: task 0 had 3, task 1 had 5, and task 2 had 1.

`guard_wrist_zero_all` completed 9 measured episodes with 0 successes and 9 failures. This condition produced only cache misses, which is expected under the anti-cheating cache reset rule.
