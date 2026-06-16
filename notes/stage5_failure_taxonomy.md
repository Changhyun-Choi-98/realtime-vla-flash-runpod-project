# Stage 5 Failure Taxonomy

Observed failure classes:

- no failure: successful episode under the perturbation.
- perturbation-induced perception failure: episode reached the horizon without success after wrist-camera zeroing.
- accepted-prefix saturation despite failure: failures where accepted prefix still reached 12 on many calls.

Classes not observed in the final corrected Stage 5 run:

- gripper/contact failure.
- object localization failure as a separately proven mechanism.
- stale action / late correction as a separately proven mechanism.
- route/fallback instability.
- server/client connection failure.
- action shape/control failure.
- simulator runtime failure.
- logging/observability failure in the corrected final run.
- GPU OOM.

Reviewer caveat: failure labels are inferred from episode outcomes, perturbation condition, and absence of runtime/control errors. Video inspection is still needed before making fine-grained claims such as contact failure or pose-estimation failure.
