# Stage 1 Model Environment Report

## Environment creation status

Top-level `uv sync` completed in the official repo environment. The Stage -1 LIBERO environment at `.venv-libero` was not modified.

## Versions

| Item | Value |
|---|---|
| Python | 3.11.13 (main, Jun  4 2025, 08:57:30) [GCC 13.3.0] |
| Python executable | `/workspace/realtime_vla_flash_project/repos/realtime-vla-flash/.venv/bin/python3` |
| torch | 2.7.1+cu126 |
| torch CUDA | 12.6 |
| GPU | NVIDIA L40S |
| Device capability | [8, 9] |
| triton | 3.3.1 |
| jax | 0.5.3 |
| JAX devices | cuda:0 |
| transformers | 4.53.2 |
| numpy | 1.26.4 |
| openpi | unknown |

## Import smoke

Status: `ok`

The smoke imports passed for `torch`, `triton`, `jax`, `transformers`, `numpy`, `openpi`, `openpi.training.config`, and `openpi.policies.policy_config`.

## Transformers patch

Status: `ok`

Patch source: `repos/realtime-vla-flash/src/openpi/models_pytorch/transformers_replace`

Patch target: official repo `.venv` transformers package.

## Important warnings

- `uv sync` emitted repeated package metadata warnings about invalid version specifiers from dependencies and repaired them while resolving.
- First import of the OpenPI config stack is slow on this pod; the final smoke uses bounded subprocess probes and succeeds.
- The checkpoint audit later triggered a Hugging Face remote-code warning for `physical-intelligence/fast` tokenizer code while resolving config/data metadata.
