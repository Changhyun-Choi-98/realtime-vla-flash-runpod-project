# Stage 5 Next Step Recommendation

Proceed to Stage 7 minimal extension.

Recommended extension: add an observation-health-aware full-path refresh schedule. In this probe, full-path ratio increased under wrist-camera dropout and accepted-prefix mean dropped, but high-percentile accepted prefix remained saturated even when success collapsed. That makes a simple accepted-prefix-only cap too brittle for this perturbation.

Concrete next task:

- detect wrist-camera health on the client before policy query;
- force or schedule full-path refreshes when the wrist stream is blank, stale, or low-information;
- keep the evaluation bounded to the same LIBERO Goal subset before expanding;
- continue treating results as partial reproduction evidence, not paper reproduction.
