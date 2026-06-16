# Stage 4 Next Step Recommendation

Proceed to Stage 5 robustness probe and Stage 6 synchronized profiling.

Recommended next scope:

- Stage 5: run a small robustness probe such as camera dropout or instruction paraphrase on the same limited task subset.
- Stage 6: add synchronized profiling for policy/server latency, GPU timing, and route behavior.
- Keep videos, checkpoints, converted weights, datasets, and profiler binaries local-only and gitignored.
- Continue to describe results as limited baseline evidence, not full paper reproduction.
