# Runpod Manifest - Stage -1

Generated UTC: 2026-06-16T00:23:56Z

## Purpose

This manifest records the machine state before model/checkpoint installation for the Realtime-VLA FLASH Stage -1 simulator feasibility gate.

## Scope

Stage -1 checks simulator feasibility only. It does not download checkpoints, download full datasets, run model inference, start Triton conversion, run a policy server, or claim paper reproduction.

## Machine Summary

| Item | Value |
|---|---|
| GPU / VRAM / driver / CUDA from nvidia-smi | NVIDIA L40S, 46068 MiB VRAM, driver 580.159.03, CUDA 13.0 |
| Workspace disk | 378T total, 125T available, 68% used |
| OS | Ubuntu 24.04.3 LTS |
| Stage -1 Python env | `.venv-libero` with Python 3.8 |
| Decision | `PROCEED_CLOSED_LOOP_EGL` |

## Official Repo

| Item | Value |
|---|---|
| URL | https://github.com/dexmal/realtime-vla-flash.git |
| Path | /workspace/realtime_vla_flash_project/repos/realtime-vla-flash |
| Commit | `da6ceccad603695a8a3d6fa14dd410c3aadb536f` |
| Branch | `main` |

## Bootstrap log

See:

- logs/stage_minus1_bootstrap.txt
