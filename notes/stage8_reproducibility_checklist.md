# Stage 8 Reproducibility Checklist

## Fixed Inputs

- Official repo: `https://github.com/dexmal/realtime-vla-flash`
- Official commit: `da6ceccad603695a8a3d6fa14dd410c3aadb536f`
- Project repo: `https://github.com/Changhyun-Choi-98/realtime-vla-flash-runpod-project.git`
- Hardware used: Runpod NVIDIA L40S
- Simulator: LIBERO/MuJoCo with EGL offscreen rendering
- Main config: `pi0_libero`
- Suite: `libero_goal`
- Main tasks: 0, 1, 2
- Seed: 7

## Environment

- Stage -1 LIBERO/client environment remained separate from the model environment.
- Stage 1 top-level model environment used the repo-pinned `uv` setup.
- Transformers replacement patch was applied inside the top-level environment.

## Checkpoint and Conversion

- Draft checkpoint: `draft_libero_goal.pt`, local-only.
- Base checkpoint: `gs://openpi-assets/checkpoints/pi0_libero`, downloaded locally.
- Triton conversion outputs were local-only and excluded from git.

## Evaluation Scope

- Stage 3: one-task smoke only.
- Stage 4: limited LIBERO Goal tasks 0-2, 10 episodes each.
- Stage 5: synthetic wrist-camera dropout probe.
- Stage 6: synchronized server-side profiling.
- Stage 7: minimal local WristHealthGuard extension.

## Public-Safe Artifact Policy

- Checkpoints, converted weights, videos, datasets, private endpoints, tokens, and profiler binaries were not committed.
- Logs and reports are lightweight artifacts intended for public review.
- Videos exist locally but are intentionally not tracked.

## Re-run Notes

- Re-running the project from scratch requires enough disk for the public base checkpoint and converted Triton artifacts.
- Stage 4, Stage 5, Stage 6, and Stage 7 should not be compared directly to the paper benchmark without matching task scope, hardware, and timing methodology.
- The blog should cite the stage reports and claim matrix rather than isolated log snippets.
