# Stage 2B Base Checkpoint Resolution Report

## Decision

**PROCEED_TO_STAGE3_ONE_TASK_CLOSED_LOOP_SMOKE**

Stage 2B resolved the public base checkpoint path for the official FLASH quick start and verified that the base conversion plus bounded policy-server boot smoke can run on this pod.

## What was checked

- Official repo state at commit `da6ceccad603695a8a3d6fa14dd410c3aadb536f`.
- Source references for `pi0_libero`, `pi05_libero`, `openpi-assets`, `--jax-path`, and Triton base/draft paths.
- Metadata-only availability for public candidate checkpoint paths.
- Controlled download only after `gs://openpi-assets/checkpoints/pi0_libero` was classified as a JAX/Orbax root for `pi0_libero`.
- Base conversion with `convert_for_triton.py --mode base`.
- Bounded server boot with `spec_serve_policy.py --config pi0_libero --backend triton`.

## Official repo evidence

- `README.md` uses the official quick-start server command with `--config pi0_libero`, `--task-suite-name libero_goal`, `--base-triton-path`, and `--draft-triton-path`.
- `scripts/spec/triton/convert_for_triton.py` appends `/params` to `--jax-path` and requires sibling `assets` for the base artifact.
- `scripts/spec/spec_serve_policy.py` defaults include `pi0_libero` and a JAX checkpoint placeholder for `/path/to/openpi-assets/checkpoints/pi0_libero`.
- `pi05_libero` was inspected only and was not used as a substitute for `pi0_libero`.

## Candidate checkpoint table

| Candidate | Exists? | Classification | Size | Has params? | Has assets/norm_stats? | Selected? | Reason |
|---|---:|---|---:|---:|---:|---:|---|
| gs://openpi-assets/checkpoints/pi0_libero | yes | MATCH_FLASH_PI0_LIBERO_JAX | metadata only | yes | yes | yes | Candidate has params, assets, and Orbax/JAX checkpoint metadata and is shaped for convert_for_triton --jax-path. |
| gs://openpi-assets/checkpoints/pi0_libero/params | yes | UNKNOWN_ACCESS_ERROR | 32.9 KiB | yes | yes | no | Params subdir alone is not suitable for --jax-path because converter appends /params and also needs sibling assets. |
| gs://openpi-assets/checkpoints/pi0_libero_torch | no | NOT_FOUND | unknown | no | no | no | Candidate path was not found or could not be listed as existing. |
| gs://openpi-assets/checkpoints/pi0_libero_torch/params | no | NOT_FOUND | unknown | no | no | no | Candidate path was not found or could not be listed as existing. |
| gs://openpi-assets/checkpoints/pi0_base | yes | BASE_PI0_PRETRAIN_ONLY | metadata only | yes | yes | no | pi0_base is a pretraining/fine-tuning base, not the paper-compatible pi0_libero policy checkpoint. |
| gs://openpi-assets/checkpoints/pi0_base/params | yes | BASE_PI0_PRETRAIN_ONLY | 26.2 KiB | yes | yes | no | pi0_base is a pretraining/fine-tuning base, not the paper-compatible pi0_libero policy checkpoint. |
| gs://openpi-assets/checkpoints/pi05_libero | yes | PUBLIC_PI05_LIBERO_MISMATCH | metadata only | yes | yes | no | pi05_libero was inspected only and is not compatible with the pi0_libero draft unless proven otherwise. |
| gs://openpi-assets/checkpoints/pi05_libero/params | yes | PUBLIC_PI05_LIBERO_MISMATCH | 40.6 KiB | yes | yes | no | pi05_libero was inspected only and is not compatible with the pi0_libero draft unless proven otherwise. |
| s3://openpi-assets/checkpoints/pi0_libero | no | NOT_FOUND | unknown | no | no | no | Candidate path was not found or could not be listed as existing. |
| s3://openpi-assets/checkpoints/pi0_libero/params | no | NOT_FOUND | unknown | no | no | no | Candidate path was not found or could not be listed as existing. |
| /openpi-assets/checkpoints/pi0_libero_torch | no | LOCAL_PLACEHOLDER_ONLY | unknown | no | no | no | README/default local placeholder path does not exist on this pod. |
| /openpi-assets/checkpoints/pi0_libero | no | LOCAL_PLACEHOLDER_ONLY | unknown | no | no | no | README/default local placeholder path does not exist on this pod. |
| /workspace/realtime_vla_flash_project/checkpoints/base_candidates/pi0_libero | no | NOT_FOUND | unknown | no | no | no | Candidate path was not found or could not be listed as existing. |
| /workspace/realtime_vla_flash_project/checkpoints/base_candidates/pi0_libero_torch | no | NOT_FOUND | unknown | no | no | no | Candidate path was not found or could not be listed as existing. |

## Selected base checkpoint

- Public path: `gs://openpi-assets/checkpoints/pi0_libero`
- Local path used for conversion: `/workspace/realtime_vla_flash_project/checkpoints/base_candidates/openpi_cache/openpi-assets/checkpoints/pi0_libero`
- Why selected: exactly one metadata candidate matched `MATCH_FLASH_PI0_LIBERO_JAX` and had `params`, `assets`, and Orbax/JAX checkpoint metadata.
- Download status: `BASE_CHECKPOINT_RESOLVED`
- Downloaded size: `12G`
- Structure: params=yes, assets=yes, checkpoint metadata=yes, norm stats=yes

## Base conversion result

- Status: `success`
- Command: `uv run python scripts/spec/triton/convert_for_triton.py --mode base --jax-path /workspace/realtime_vla_flash_project/checkpoints/base_candidates/openpi_cache/openpi-assets/checkpoints/pi0_libero --output /workspace/realtime_vla_flash_project/converted/base`
- Output dir: `/workspace/realtime_vla_flash_project/converted/base`
- Sample files: `base_weights.pkl, assets/physical-intelligence/libero/norm_stats.json`

## Server boot smoke result

- Status: `ready`
- Readiness evidence: `log/port readiness pattern or process remained alive`
- Note: the smoke started the server only long enough to infer readiness, then terminated it. It did not run a client, policy rollout, benchmark, or evaluation.

## Failure classification

No blocker remains in Stage 2B. Base checkpoint resolution, base conversion, and bounded server boot smoke all passed.

## Blog-safe conclusion

A public `pi0_libero` JAX/Orbax checkpoint exists at `gs://openpi-assets/checkpoints/pi0_libero`. On this Runpod pod, it can be downloaded through the official OpenPI downloader, converted with the official FLASH Triton converter, paired with the converted `draft_libero_goal.pt`, and used to start the official Triton policy server far enough to report readiness.

## What this does not claim

- Does not claim paper reproduction.
- Does not claim closed-loop success.
- Does not claim latency reproduction.
- Does not use pi05_libero as a substitute for pi0_libero unless compatibility is proven.
