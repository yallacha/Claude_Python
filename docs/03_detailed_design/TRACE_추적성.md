# TRACE SWR·아키텍처 ↔ 상세 설계 단위 추적성

| 항목 | 내용 |
|---|---|
| 문서 ID | TRACE-SWD-001 |
| 범위 | SWR(BL-SWR-1.1 승인 대기), SWA 컴포넌트(BL-SWA-1.0) ↔ 상세 설계 단위(BL-SWD-1.0) |
| 하위 추적 | 단위 시험(SWE.4)은 4단계에서 이 표에 "단위 시험" 열을 추가한다 |

## 1. SWR → 상세 설계 단위

| SWR | 단위 (SWD 절) |
|---|---|
| SWR-001 | `decision._rule_driver` (5.3), `controller.submit_command`·`step` (9) |
| SWR-002 | `decision._rule_driver` (5.3), `controller` (9) |
| SWR-003 | `decision._rule_auto_lock` (5.3) |
| SWR-004 | `decision._with_command_effect` (5.3), `decision._decide_door` (5.2) |
| SWR-005 | `decision._rule_approach_risk`, `_with_command_effect` (5.3) |
| SWR-006 | `override.OverrideTracker.annotate` (6), `controller._to_status` (9) |
| SWR-007 | `decision.decide` latch 갱신 (5.1), `_rule_crash` (5.3), `_state_of` (5.5) |
| SWR-008 | `decision._combine` (5.4) |
| SWR-009 | `decision._decide_door`의 도어별 호출 (5.1, 5.2), `model.door_lock` (2) |
| SWR-010 | `event_store.EventStore.record` (7) |
| SWR-011 | `event_store.EventStore.record`, `model.Event` (2, 7) |
| SWR-012 | `event_store.EventStore` deque 용량, `list_events` (7) |
| SWR-013 | `validation.parse_snapshot`·`parse_command` (3), `freshness.is_stale` (4), `controller._validity` (9), `decision._decide_without_input`·`_rule_fault_or_stale` (5.1, 5.3) |
| SWR-014 | `controller.status` (9), `web` `GET /api/status`, `serialize_status` (11) |
| SWR-015 | `web` 정적 화면, `GET /api/status` 500 처리 (11) |
| SWR-016 | `decision.decide` 순수성 (5), `clock.ManualClock` (8), `replay.run`·`result_hash` (10) |
| SWR-017 | `decision._rule_forced_release` (5.3) |
| SWR-018 | `decision._rule_isofix` (5.3) |
| SWR-020 | `decision._rule_ignition_off` (5.3), `_state_of` (5.5), latch 해제 (5.1) |
| SWR-021 | `decision._rule_fault_or_stale` (5.3), `_state_of` 경고 코드 (5.5) |
| SWR-022 | `decision.RULES` 순서 (5.2), `model.PriorityReason.rank` (2), `_combine` (5.4) |
| SWR-023 | `controller.step` (9), `clock` (8), `web` 50 ms 루프 (11), `model.CYCLE_MS` (1.1) |
| SWR-024 | `model.INITIAL_STATE`·`INITIAL_STATUS` (2), `decision._decide_without_input` NO_DATA (5.1) |

SWR 23/23 할당.

## 2. SWA 컴포넌트 → 상세 설계

| 컴포넌트 | SWD 절 | 단위 수(공개) |
|---|---|---|
| `model` | 1.1, 2 | Enum 10, dataclass 10, 함수 2, 상수 |
| `validation` | 3 | 2 |
| `freshness` | 4 | 1 |
| `decision` | 5 | 1 (+ 내부 함수 12) |
| `clock` | 8 | 3 |
| `controller` | 9 | 1 클래스 |
| `override` | 6 | 1 클래스 + `Annotation` |
| `event_store` | 7 | 1 클래스 |
| `replay` | 10 | 4 |
| `web` | 11 | 2 + 정적 화면 |

SWA 컴포넌트 10/10 상세 설계.

## 3. 아키텍처 인터페이스 → 상세 설계 일치

| SWA 5장 인터페이스 | SWD 시그니처 | 일치 |
|---|---|---|
| `parse_snapshot(raw)` | 3.1 | 예 |
| `parse_command(raw)` | 3.2 | 예 |
| `is_stale(now_s, last_timestamp_s)` | 4 | 예 |
| `decide(snapshot, commands, previous, input_validity)` | 5.1 | 예 |
| `OverrideAnnotator.annotate(decision, now_s, risk_left, risk_right)` | 6 | 예 |
| `EventSink.record(status, timestamp_s)` / `list_events()` | 7 | 예 |
| `controller.submit_*`, `step`, `status` | 9 | 예 |
| `Clock.now()` | 8 | 예 |
| HTTP API | 11 (`POST /api/step` 시험용 추가) | 예 (추가는 SWA 변경 아님: 시험 전용, `run_loop=False`일 때만) |
