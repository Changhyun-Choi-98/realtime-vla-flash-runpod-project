# Stage 2 Checkpoint and Conversion Report

## Decision

`BLOCKED_BASE_CHECKPOINT_UNRESOLVED`

Draft checkpoint download/load/conversion succeeded, but base conversion was skipped because the official FLASH pi0_libero JAX checkpoint path is unresolved in the checked-out repo artifacts.

## Help command audit

- `convert_for_triton`: `ok` exit `0`
- `spec_serve_policy`: `ok` exit `0`
- `spec_client_libero`: `failed_or_missing` exit `1`
- `pi0_benchmark`: `ok` exit `0`

`spec_client_libero.py --help` failed in the top-level model environment because LIBERO is intentionally not installed there. This preserves the Stage -1/Stage 1 environment separation.

## Config audit result

Available LIBERO-related configs:

- `pi05_libero`: resolution `ok`, model `Pi0Config`, weight loader `CheckpointWeightLoader(params_path='gs://openpi-assets/checkpoints/pi05_base/params')`
- `pi0_fast_libero`: resolution `ok`, model `Pi0FASTConfig`, weight loader `CheckpointWeightLoader(params_path='gs://openpi-assets/checkpoints/pi0_fast_base/params')`
- `pi0_fast_libero_low_mem_finetune`: resolution `ok`, model `Pi0FASTConfig`, weight loader `CheckpointWeightLoader(params_path='gs://openpi-assets/checkpoints/pi0_fast_base/params')`
- `pi0_libero`: resolution `ok`, model `Pi0Config`, weight loader `CheckpointWeightLoader(params_path='gs://openpi-assets/checkpoints/pi0_base/params')`
- `pi0_libero_low_mem_finetune`: resolution `ok`, model `Pi0Config`, weight loader `CheckpointWeightLoader(params_path='gs://openpi-assets/checkpoints/pi0_base/params')`

Tooling:

- `gsutil`: `False`
- `huggingface-cli`: `True`
- `gcloud`: `False`

`gs://openpi-assets/checkpoints/pi05_libero` metadata was visible through fsspec with entries for `assets` and `params`.

## Base checkpoint candidate and status

Status: `SKIPPED_UNRESOLVED_BASE_CHECKPOINT`

The checked-out repo identifies these relevant paths:

- `pi0_libero` weight loader: `gs://openpi-assets/checkpoints/pi0_base/params`
- `pi05_libero` weight loader: `gs://openpi-assets/checkpoints/pi05_base/params`
- README_OPENPI inference checkpoint: `gs://openpi-assets/checkpoints/pi05_libero`
- FLASH quick-start base conversion placeholder: `/path/to/jax/checkpoint`
- FLASH draft-cache example: `/openpi-assets/checkpoints/pi0_libero_torch`

No base checkpoint was downloaded because the official FLASH `pi0_libero` base conversion path was not resolved to a justified local JAX checkpoint directory.

## Draft checkpoint path/load result

Path: `/workspace/realtime_vla_flash_project/checkpoints/drafts/draft_libero_goal.pt`

Status: `loaded`

File size: `441154745` bytes

Top-level type: `dict`

Tensor count: `14`

## Draft conversion status

Status: `ok`

Output: `/workspace/realtime_vla_flash_project/converted/draft_goal/draft_triton.pkl`

## Base conversion status

Status: `SKIPPED_UNRESOLVED_BASE_CHECKPOINT`

## Server boot smoke status

Status: `SKIPPED_BASE_CONVERSION_NOT_AVAILABLE`

The server boot smoke was skipped because both base and draft Triton artifacts are required, and base conversion was not available.

## Exact blockers

- The draft checkpoint can be downloaded, loaded, and converted.
- The base checkpoint required for FLASH `pi0_libero` Triton conversion remains unresolved.
- Stage 3 one-task closed-loop smoke should not run until the base checkpoint path is resolved and base conversion succeeds.

## Next recommendation

Resolve the base checkpoint path before Stage 3. Do not run full benchmark or claim paper reproduction.
