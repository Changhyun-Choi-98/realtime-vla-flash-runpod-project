# Stage -1 LIBERO Simulator Feasibility Report

## Decision

**PROCEED_CLOSED_LOOP_EGL**

## Pass backend

```text
egl
```

## Official repo

* URL: https://github.com/dexmal/realtime-vla-flash.git
* Path: /workspace/realtime_vla_flash_project/repos/realtime-vla-flash
* Commit: `da6ceccad603695a8a3d6fa14dd410c3aadb536f`
* Branch: `main`

## What was tested

* MuJoCo import
* robosuite import
* LIBERO import
* LIBERO OffScreenRenderEnv reset
* rendered camera observation availability
* 20-step dummy 7D action rollout
* EGL backend
* OSMesa backend

## What was not tested

* No checkpoint download
* No full dataset download
* No model server
* No Triton conversion
* No closed-loop policy evaluation
* No paper claim reproduction

## Key logs

* `logs/stage_minus1_bootstrap.txt`
* `logs/stage_minus1_imports.txt`
* `logs/stage_minus1_smoke_egl.txt`
* `logs/stage_minus1_smoke_osmesa.txt`

## Result files

* `results/stage_minus1_libero_smoke_egl.json`
* `results/stage_minus1_libero_smoke_osmesa.json`
* `results/stage_minus1_decision.json`

## Interpretation

MuJoCo/robosuite/LIBERO offscreen rendering works through EGL. Continue to Stage 0/1.

## Required next action

If decision is `PROCEED_CLOSED_LOOP_EGL`, continue to Stage 0/1: scope lock and model environment setup.

If decision is `PARTIAL_PROCEED_CLOSED_LOOP_OSMESA_ONLY`, continue only with strong latency caveats.

If decision is `STOP_CLOSED_LOOP_CONVERT_TO_INFERENCE_ONLY`, do not proceed with closed-loop reproduction on this pod.

## Reviewer notes

* Ubuntu 24.04 did not provide `libgl1-mesa-glx`; `libgl1` was installed as the modern replacement.
* The official LIBERO requirement sync succeeded inside `.venv-libero`; no fallback simulator-only pip install was needed.
* The smoke script fixes the task suite lookup typo from the draft command by using `benchmark_dict[suite_name]()`.
* LIBERO warned that the datasets path does not exist. This is expected for Stage -1 because demonstrations/full datasets were intentionally not downloaded.
* robosuite emitted its standard first-run private macro warning; imports and both smoke tests still succeeded.
