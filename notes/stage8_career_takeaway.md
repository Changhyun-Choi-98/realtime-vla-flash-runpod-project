# Stage 8 Career Takeaway

이 프로젝트의 핵심 가치는 "논문을 끝까지 믿거나 부정하기 전에, 어디까지 실제로 돌아가는지 단계별로 좁혀서 확인했다"는 점이다.

## 보여준 역량

- GPU 서버에서 simulator, model environment, checkpoint, conversion, policy server, client rollout을 단계별로 연결했다.
- official repo와 public checkpoint를 기준으로 재현 가능한 artifact trail을 남겼다.
- 제한된 closed-loop baseline을 실제로 실행하고, 성공률과 route behavior를 정리했다.
- latency claim을 그대로 받아들이지 않고 synchronized profiling을 추가해 측정 방법을 개선했다.
- robustness probe를 설계해 wrist-camera dropout이라는 구체적 failure mode를 확인했다.
- WristHealthGuard라는 작은 inference-time extension을 구현하고, 긍정/부정 결과를 모두 보수적으로 해석했다.

## 면접/포트폴리오용 한 문장

Realtime-VLA FLASH를 Runpod L40S에서 official repo와 public checkpoint로 실행해 limited closed-loop baseline, synchronized latency profiling, synthetic robustness probe, 그리고 minimal local extension까지 단계적으로 검증했다.

## 중요한 태도

가장 좋은 결과만 골라 말하지 않았다. 성공한 부분, 막혔다가 해결한 부분, 여전히 claim하지 못하는 부분을 모두 분리했다. 이 방식이 research engineering에서 더 신뢰할 수 있는 기록이다.
