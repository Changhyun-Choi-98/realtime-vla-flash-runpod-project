# Upstream Issue Draft

No upstream issue is needed for Stage 2B because the public `pi0_libero` JAX/Orbax base checkpoint was resolved and validated.

Resolved path:

```text
gs://openpi-assets/checkpoints/pi0_libero
```

Validated command shape:

```bash
uv run python scripts/spec/triton/convert_for_triton.py   --mode base   --jax-path /workspace/realtime_vla_flash_project/checkpoints/base_candidates/openpi_cache/openpi-assets/checkpoints/pi0_libero   --output /workspace/realtime_vla_flash_project/converted/base
```

If a future run cannot access this path, ask maintainers for the exact public base checkpoint path for:

```text
convert_for_triton.py --mode base --jax-path <...>
spec_serve_policy.py --config pi0_libero
```
