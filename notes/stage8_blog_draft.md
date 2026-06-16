---
layout: post
title: "Realtime-VLA FLASH Runpod Reproduction: Closed-loop Baseline, Profiling, and Wrist-camera Robustness"
nav_exclude: true
section: project
subcategory: paper-to-prototype-lab
date: 2026-06-16
tags:
  - Korean
  - VLA
  - inference-optimization
  - closed-loop
  - LIBERO
  - profiling
  - robustness
language: ko
summary: "Realtime-VLA FLASH official repo와 public checkpoint를 Runpod L40S에서 실행해, LIBERO Goal limited closed-loop baseline, synchronized latency profiling, wrist-camera dropout robustness probe, 그리고 WristHealthGuard minimal extension을 검증한 프로젝트"
math: true
comments: true
comment_id: "project-realtime-vla-flash"
permalink: /project/paper-to-prototype-lab/realtime-vla-flash/
---

# TL;DR

Realtime-VLA FLASH official repo와 public checkpoint를 Runpod L40S에서 실제로 실행했다. 먼저 LIBERO/MuJoCo EGL simulator gate를 통과했고, 이후 `pi0_libero` base checkpoint와 `draft_libero_goal` checkpoint를 Triton artifact로 변환했다. 그 다음 limited LIBERO Goal closed-loop baseline을 실행해 tasks 0-2에서 27/30 success를 얻었다.

Latency 쪽은 Stage 4의 wall-clock timing만으로는 부족하다고 판단해 Stage 6에서 server-side `torch.cuda.synchronize()` 기반 timing을 추가했다. 이 limited setup에서 draft route p50는 8.067 ms, full route p50는 33.156 ms였다. 이 결과는 FLASH의 mechanism-level support로 볼 수 있지만, hardware-exact paper latency reproduction은 아니다.

Robustness 쪽에서는 synthetic wrist-camera dropout을 넣었고, 성능이 크게 떨어지는 것을 확인했다. `wrist_zero_every4`는 4/15, `wrist_zero_all`은 0/15였다. 마지막으로 minimal local research extension인 WristHealthGuard를 구현했다. 이 guard는 intermittent dropout을 4/15에서 6/15로 조금 회복했지만, persistent all-zero dropout은 0/9로 해결하지 못했다.

이 프로젝트의 결론은 명확하다. 제한된 closed-loop baseline, profiling, probing, minimal extension은 성공했다. 하지만 full paper reproduction, hardware-exact latency reproduction, full robustness evaluation은 아니다.

# Why this paper

Realtime-VLA FLASH는 diffusion-based VLA(vision-language-action) policy의 inference latency를 줄이기 위한 speculative inference framework다. VLA policy는 closed-loop 환경에서 action chunk를 빠르게 내야 하고, simulation이나 robot control loop에서는 latency가 단순 throughput보다 더 직접적인 문제가 된다.

내가 이 논문을 고른 이유는 세 가지였다.

첫째, 논문의 claim이 system-level이다. 단순히 model accuracy만 보는 것이 아니라, draft path, full path, parallel verification, accepted prefix, fallback 같은 runtime mechanism이 실제 closed-loop에서 작동해야 한다.

둘째, official repo와 public checkpoint가 있어서 Runpod 한 대에서 어디까지 갈 수 있는지 검증할 수 있었다.

셋째, 실패해도 배울 것이 많았다. simulator, checkpoint, Triton conversion, policy server, LIBERO client, timing, robustness가 모두 한 chain에 묶여 있기 때문이다.

# What this project claims and does not claim

이 프로젝트가 claim하는 것:

- Runpod L40S에서 official repo 기반 Realtime-VLA FLASH setup을 구성했다.
- LIBERO/MuJoCo EGL offscreen simulation gate를 통과했다.
- public `pi0_libero` base checkpoint와 `draft_libero_goal` checkpoint를 사용해 Triton artifacts를 만들었다.
- limited LIBERO Goal baseline에서 tasks 0-2, 총 30 measured episodes를 실행했고 27/30 success를 얻었다.
- synchronized server-side profiling에서 draft route p50 latency가 full route p50 latency보다 낮았다.
- synthetic wrist-camera dropout이 이 subset에서 성능을 크게 떨어뜨렸다.
- WristHealthGuard라는 minimal local extension이 intermittent dropout을 modest하게 회복했다.

이 프로젝트가 claim하지 않는 것:

- full paper reproduction
- full LIBERO benchmark
- hardware-exact paper latency reproduction
- real-world conveyor result
- general robustness proof
- upstream-quality extension

# Paper claim decomposition

논문의 큰 메시지를 그대로 하나의 문장으로 재현하려 하지 않았다. 대신 claim을 작은 단위로 쪼갰다.

1. Simulator가 돌아가는가?
2. Official repo environment가 잡히는가?
3. Checkpoint와 Triton conversion이 되는가?
4. Policy server가 뜨는가?
5. Closed-loop client가 실제 action을 받아 simulator를 굴리는가?
6. Limited baseline success가 나오는가?
7. Draft route가 full route보다 빠른가?
8. Accepted prefix가 route/fallback behavior를 설명하는가?
9. Observation perturbation에 취약한가?
10. 간단한 inference-time guard가 일부 failure를 줄일 수 있는가?

이렇게 쪼개면 어디까지 support되고 어디부터 unsupported인지 훨씬 분명해진다.

# Method recap: Realtime-VLA FLASH

Realtime-VLA FLASH는 diffusion-based VLA policy의 inference를 speculative하게 줄이는 구조로 이해할 수 있다. 자세한 수식 재현보다, 이 프로젝트에서는 runtime 관점의 의미를 확인하는 데 집중했다.

## Full path

Full path는 더 비싼 기준 policy path다. 이 path는 latency가 더 크지만, speculative draft result를 검증하거나 fallback하는 기준 역할을 한다.

## Draft path

Draft path는 더 빠른 action proposal을 만든다. Stage 6 limited profiling에서 draft route p50 `policy_time_gpu_sync_ms`는 8.067 ms였다.

## Parallel verification

FLASH의 핵심은 draft를 만들고 full path와 비교해 prefix를 얼마나 accept할지 결정하는 것이다. 이 과정이 잘 작동하면 모든 step에서 full path를 실행하는 것보다 control loop latency를 줄일 수 있다.

## Accepted prefix

Accepted prefix는 draft action chunk 중 얼마나 받아들였는지를 나타낸다. Stage 4 clean baseline에서는 accepted prefix mean이 10.074였고 p50/p95/p99는 12였다. 하지만 Stage 5/7 robustness probe에서는 failure 상황에서도 p95/p99가 12로 유지되는 경우가 많았다. 따라서 accepted prefix는 useful diagnostic이지만, 단독 failure detector는 아니었다.

## Phase-aware fallback

Fallback은 full route 또는 shorter prefix로 돌아가는 mechanism이다. 이 프로젝트에서는 route mix와 accepted prefix를 log로 추적했지만, phase-aware behavior 자체를 paper와 동일한 수준으로 분석하지는 않았다.

# Action representation and control-loop meaning

Server는 `(50, 7)` action chunk를 반환했다. 여기서 7D action은 robot control command의 compact representation이고, chunk는 한 번의 policy query로 여러 low-level control step을 실행할 수 있게 한다.

Closed-loop 관점에서는 "policy가 한 번 action을 냈다"보다 "이 action chunk가 simulator episode 안에서 task success로 이어졌는가"가 중요하다. 그래서 Stage 3 이후부터는 server readiness뿐 아니라 LIBERO rollout, episode logs, infer logs, trace logs, video artifacts를 함께 확인했다.

# Stage -1: simulator feasibility gate

Stage -1은 model을 설치하거나 checkpoint를 받기 전에 simulator만 확인했다.

결과:

- MuJoCo import: passed
- robosuite import: passed
- LIBERO import: passed
- OffScreenRenderEnv reset: passed
- rendered camera observations: passed
- 20-step dummy 7D rollout: passed
- EGL backend: passed
- OSMesa backend: passed

이 단계 덕분에 이후 checkpoint/model setup을 진행할 근거가 생겼다.

# Stage 1-2B: model/checkpoint/server readiness

Stage 1에서는 top-level model environment를 `.venv-libero`와 분리해서 구성했다.

주요 version:

- Python 3.11.13
- torch 2.7.1+cu126
- CUDA 12.6 from torch
- Triton 3.3.1
- JAX 0.5.3
- transformers 4.53.2
- GPU: NVIDIA L40S

Stage 2에서는 draft checkpoint를 다운로드하고 load/conversion을 확인했다. 처음에는 base checkpoint가 unresolved blocker였다.

Stage 2B에서 `gs://openpi-assets/checkpoints/pi0_libero`가 public JAX/Orbax-style base checkpoint로 확인됐고, base conversion과 server boot smoke가 통과했다.

# Stage 3: one-task closed-loop smoke

Stage 3은 task 0에서 2 episodes만 실행한 integration smoke였다.

결과:

- Episodes completed: 2/2
- Success: 2/2
- Server ready: yes
- Server alive during client: yes
- Action chunk shape: `(50, 7)`
- Videos/logs: produced locally

이 단계는 "전체 성능"이 아니라 end-to-end chain이 살아 있는지 확인하는 목적이었다.

# Stage 4: limited closed-loop baseline

Stage 4는 이 프로젝트의 clean baseline이다.

Setup:

- Suite: `libero_goal`
- Tasks: 0, 1, 2
- Episodes: 10 per task
- Total measured episodes: 30
- Seed: 7
- Backend: Triton + EGL

결과:

| Task | Success |
|---:|---:|
| 0 | 9/10 |
| 1 | 9/10 |
| 2 | 9/10 |
| Aggregate | 27/30 |

Route behavior:

- Full route: 88
- Draft route: 276
- Draft ratio: 0.758
- Full ratio: 0.242
- Accepted prefix mean: 10.074

이 결과는 limited closed-loop baseline으로는 강한 evidence다. 하지만 tasks 0-2만 사용했으므로 full LIBERO benchmark로 읽으면 안 된다.

# Stage 6: synchronized latency profiling

Stage 4 timing은 wall-clock timing이라 paper latency와 비교하기에 부족했다. 그래서 Stage 6에서는 server-side action generation path에 `torch.cuda.synchronize()` 기반 timing을 추가했다.

Measured setup:

- Tasks: 0, 1, 2
- 3 measured episodes per task
- 9 measured episodes total
- Warm-up excluded

결과:

- Steady-state `policy_time_gpu_sync_ms` p50/p95: 8.083 / 33.501 ms
- Draft route `policy_time_gpu_sync_ms` p50: 8.067 ms
- Full route `policy_time_gpu_sync_ms` p50: 33.156 ms
- Client roundtrip p50: 11.957 ms
- Claim status: `PARTIALLY_SUPPORTED_LIMITED`

해석:

이 limited setting에서는 draft route가 full route보다 낮은 p50 latency를 보였다. 이는 FLASH mechanism을 support하는 evidence다. 하지만 hardware, task subset, benchmark scope가 paper와 같지 않으므로 hardware-exact latency reproduction은 아니다.

# Stage 5: wrist-camera dropout robustness probe

Stage 5에서는 synthetic wrist-camera dropout을 넣었다.

Conditions:

- `wrist_zero_every4`: policy query index가 4의 배수일 때 wrist image를 zero 처리
- `wrist_zero_all`: 모든 policy query에서 wrist image를 zero 처리

결과:

| Condition | Success |
|---|---:|
| Stage 4 clean | 27/30 |
| wrist_zero_every4 | 4/15 |
| wrist_zero_all | 0/15 |

Route/prefix behavior:

- Stage 4 full ratio: 0.242
- `wrist_zero_every4` full ratio: 0.322
- `wrist_zero_all` full ratio: 0.388
- `wrist_zero_every4` accepted prefix mean: 7.929
- `wrist_zero_all` accepted prefix mean: 6.550

Wrist-camera dropout은 이 subset에서 매우 큰 성능 저하를 만들었다. Accepted prefix mean과 full route ratio는 변화했지만, high percentile accepted prefix는 여전히 saturated되어 있었다. 이 점이 중요하다. Accepted prefix는 partial signal이지 complete uncertainty signal이 아니었다.

# Stage 7: WristHealthGuard minimal extension

Stage 7에서는 observation-health-aware wrist-frame fallback을 구현했다.

핵심 규칙:

1. Simulator observation을 받는다.
2. Stage 5 dropout perturbation을 먼저 적용한다.
3. Perturbed wrist image의 health를 계산한다.
4. Unhealthy이고 같은 episode 안의 recent valid cache가 있으면 cache frame으로 대체한다.
5. Healthy이면 cache를 업데이트한다.
6. Policy에는 최종 image만 보낸다.

Anti-cheating rule은 중요했다. Guard는 clean pre-perturb image를 볼 수 없다. Persistent all-zero dropout에서는 첫 frame부터 zero가 되므로 valid cache가 없고, 따라서 회복하면 안 된다.

결과:

| Condition | Stage 5 no guard | Stage 7 guard |
|---|---:|---:|
| wrist_zero_every4 | 4/15 | 6/15 |
| wrist_zero_all | 0/15 | 0/9 |

Guard behavior:

- Every4 cache hits: 96
- Every4 replacements: 96
- Every4 cache hit rate: 0.229
- All-zero cache hits: 0
- All-zero replacements: 0
- All-zero cache misses: 433

해석:

WristHealthGuard는 intermittent dropout을 조금 회복했다. 하지만 task 1은 여전히 0/5였고, persistent all-zero는 전혀 해결하지 못했다. 이 결과는 오히려 좋은 sanity check다. Extension이 clean image를 몰래 쓰지 않았다는 evidence가 되기 때문이다.

# Failure mode taxonomy

이 프로젝트에서 관찰한 failure mode는 다음과 같이 정리할 수 있다.

- simulator/setup failure: Stage -1에서 통과
- checkpoint/path ambiguity: Stage 2에서 blocker였고 Stage 2B에서 해결
- policy behavior/no success: Stage 4의 일부 failure
- perturbation-induced perception failure: Stage 5와 Stage 7의 주요 failure
- accepted-prefix saturation despite failure: Stage 5/7에서 관찰
- persistent observation loss: WristHealthGuard로도 해결되지 않음
- latency measurement ambiguity: Stage 4에서 발견, Stage 6에서 개선

# Claim reproduction matrix

자세한 matrix는 `notes/stage8_claim_matrix.md`와 `results/stage8_claim_matrix.json`에 있다.

요약:

| Claim | Status |
|---|---|
| Simulator feasibility | supported |
| Official repo/env readiness | supported |
| Checkpoint/conversion | supported |
| Policy server boot | supported |
| One-task closed-loop smoke | supported |
| Limited LIBERO Goal baseline | supported limited |
| Latency mechanism | partially supported limited |
| Accepted-prefix behavior | supported limited |
| Wrist-camera dropout robustness | negative limited |
| WristHealthGuard extension | partially supported limited |
| Full benchmark | not claimed |
| Real-world conveyor | not claimed |

# Cost / artifact / reproducibility notes

이 프로젝트는 모든 lightweight artifact를 GitHub에 남겼다.

Tracked:

- stage reports
- scripts
- configs
- logs
- parsed JSON/CSV summaries
- figures
- claim matrix
- blog draft

Excluded:

- checkpoints
- converted weights
- videos
- datasets
- private endpoints
- credentials
- profiler binaries

재실행하려면 official repo commit, Runpod GPU environment, public checkpoint access, and local storage for base checkpoint/conversion artifacts가 필요하다.

# What this project does not claim

다시 강조한다.

이 프로젝트는 full LIBERO benchmark가 아니다. 모든 paper task/suite를 실행하지 않았다. Real-world conveyor result도 실행하지 않았다. Hardware-exact latency comparison도 아니다. Robustness를 해결했다는 claim도 아니다.

이 프로젝트는 limited closed-loop reproduction + probing + profiling + minimal extension이다.

# Final takeaway

Realtime-VLA FLASH는 Runpod L40S에서 official repo와 public checkpoint로 limited closed-loop까지 실제로 연결할 수 있었다. Clean subset baseline은 27/30 success로 좋았다. Synchronized profiling은 draft route가 full route보다 빠른 p50를 보였다. 하지만 wrist-camera dropout에는 민감했고, accepted prefix는 failure detector로 충분하지 않았다. Minimal WristHealthGuard는 intermittent dropout을 조금 도왔지만 persistent observation loss는 해결하지 못했다.

가장 중요한 결과는 숫자 하나가 아니라 claim boundary다. 이 프로젝트는 논문 전체를 재현했다고 말하지 않는다. 대신 어떤 부분은 실행했고, 어떤 부분은 partially supported이며, 어떤 부분은 아직 claim할 수 없는지 명확히 나눴다.

# Career takeaway

Research engineering에서 중요한 능력은 "좋아 보이는 결과"를 만드는 것만이 아니다. 불확실한 논문 코드를 실제 서버 위에서 단계별로 살리고, blocker를 분류하고, 측정을 개선하고, negative result까지 artifact로 남기는 능력이 더 중요할 때가 많다.

이번 프로젝트는 그 흐름을 보여준다. Simulator gate에서 시작해 checkpoint resolution, Triton conversion, closed-loop rollout, synchronized profiling, robustness probe, minimal extension까지 이어졌다. 최종 결과는 제한적이지만 정직하다. 그리고 그 정직함이 다음 실험을 가능하게 만든다.
