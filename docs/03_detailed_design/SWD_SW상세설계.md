# SWD SW 상세 설계

| 항목 | 내용 |
|---|---|
| 문서 ID | SWD-001 |
| 상위 입력 | BL-SWR-1.0, BL-SWA-1.0 (`../02_architecture/SWA_SW아키텍처명세.md`) |
| 베이스라인 | BL-SWD-1.0 (G2 승인 대기) |
| 관련 문서 | `TRACE_추적성.md`, `REVIEW_검토기록.md`, `CR_변경요청.md` |

## 1. 공통 규칙

| ID | 규칙 | 이유 |
|---|---|---|
| DD-C01 | 모든 모듈은 `src/childlock/<모듈>.py`이고, 공개 이름은 모듈 docstring의 `@brief`와 함수 docstring(`@brief`, `@param`, `@return`)을 가진다 | 주석률 20%, Doxygen 규칙 |
| DD-C02 | 시간은 인터페이스에서 초(float)로 주고받고, **비교는 정수 밀리초**(`to_ms(x) = round(x * 1000)`)로 한다 | 0.05 s를 200번 더하면 10.000000000000002가 되는 부동소수 오차로 경계값(10.0 s 이하, 200 ms 초과) 판정이 틀어지는 것을 막음 |
| DD-C03 | 차속 비교는 `>= 3.0` 그대로 한다. 입력 차속은 반올림하지 않는다 | 분해능 0.1(D-07)은 시험 설계용이며 입력 값 변환 요구는 없음 |
| DD-C04 | 함수 하나는 NLOC 50, CCN 10 이하. 규칙이 많은 판정은 규칙별 함수 + 순서 목록으로 만든다 | 품질 기준 |
| DD-C05 | 데이터 객체는 `@dataclass(frozen=True)`, 목록은 `tuple`로 둔다 | AD-04 불변성 |

### 1.1 상수 (`model`)

| 이름 | 값 | 출처 |
|---|---|---|
| `CYCLE_MS` | 50 | SWR-023, D-03 |
| `STALE_THRESHOLD_MS` | 200 | SWR-013 |
| `OVERRIDE_WINDOW_MS` | 10000 | SWR-006 |
| `AUTO_LOCK_SPEED_KPH` | 3.0 | SWR-003 |
| `SPEED_MIN_KPH`, `SPEED_MAX_KPH` | 0.0, 300.0 | OEM-IF-001 |
| `EVENT_CAPACITY` | 100 | SWR-012 |
| `WARNING_SENSOR_FAULT` | `"W_SENSOR_FAULT"` | SWR-021 |

## 2. `model` (ASIL B)

SWIF와 SWA 4.3의 타입을 그대로 구현한다.

| 이름 | 종류 | 내용 |
|---|---|---|
| `Lock`, `State`, `InputValidity`, `Side`, `Action`, `Source`, `Gear`, `CrashStatus` | `Enum` (`str` 값) | SWIF 5장 값. JSON 직렬화 시 값 문자열 그대로 사용 |
| `PriorityReason` | `Enum` | 값과 함께 순위 속성 `rank`(crash=1, sensor_fault·input_stale=2, approach_risk=3, ignition_off=4, forced_release=5, isofix=6, auto_lock=7, driver_command=8, hold·input_invalid=9) |
| `Door` | `Enum` | `LEFT`, `RIGHT`. 평가 순서는 LEFT, RIGHT |
| `VehicleSnapshot` | dataclass | SWIF 1장 13개 필드 |
| `DriverCommand` | dataclass | `side`, `action`, `source` |
| `ControllerState` | dataclass | `lock_left`, `lock_right`, `state`, `crash_latched`(bool) |
| `DoorVerdict` | dataclass | `lock`, `priority`(`PriorityReason`), `reason_code`(str), `suppressed_unlock`(bool) |
| `Decision` | dataclass | `lock_left`, `lock_right`, `state`, `priority_reason`, `reason_code`, `warning_code`, `crash_latched`, `suppressed_unlocks`(`tuple[Door, ...]`) |
| `Status` | dataclass | SWIF 4장 7개 필드 |
| `Event` | dataclass | SWIF 6장 8개 필드 |
| `Valid[T]`, `Invalid` | dataclass | 검증 결과. `Invalid.errors: tuple[str, ...]` |
| `INITIAL_STATE` | 상수 | `ControllerState(RELEASE, RELEASE, OFF, False)` (SWR-024) |
| `INITIAL_STATUS` | 상수 | `Status(RELEASE, RELEASE, OFF, NO_DATA, hold, "no_change", None)` (SWR-024) |

함수 `door_lock(decision_or_state, door) -> Lock`: 도어에 해당하는 출력을 돌려준다(좌·우 분기를 한 곳에 모음).

## 3. `validation` (ASIL B)

### 3.1 `parse_snapshot(raw: Mapping[str, object]) -> Valid[VehicleSnapshot] | Invalid`

```
errors = []
if raw가 Mapping이 아님: return Invalid(("not_object",))
for (필드, 검사기) in SNAPSHOT_FIELDS:        # 표 기반, 필드 13개
    if 필드 not in raw: errors.append(f"{필드}:missing"); continue
    값, 오류 = 검사기(raw[필드])
    if 오류: errors.append(f"{필드}:{오류}")
여분 필드는 무시한다
return Invalid(tuple(errors)) if errors else Valid(VehicleSnapshot(...))
```

| 검사기 | 통과 조건 | 실패 코드 |
|---|---|---|
| `_number(lo, hi)` | `type(v) in (int, float)` 이고 `bool`이 아님, 유한수, `lo <= v <= hi` | `type`, `range` |
| `_boolean` | `type(v) is bool` | `type` |
| `_enum(E)` | `str`이고 `E`의 값 중 하나 | `type`, `value` |

| 필드 | 검사기 |
|---|---|
| `source_timestamp_s` | `_number(0.0, inf)` (무한대는 유한수 조건으로 거절) |
| `vehicle_speed_kph` | `_number(0.0, 300.0)` |
| `gear` | `_enum(Gear)` |
| `crash_status` | `_enum(CrashStatus)` |
| 불리언 9개 | `_boolean` |

### 3.2 `parse_command(raw) -> Valid[DriverCommand] | Invalid`

같은 방식으로 `side`(`_enum(Side)`), `action`(`_enum(Action)`), `source`(`_enum(Source)`)를 검사한다.

**단위 검증 기준**: 필드별 누락·형식·범위·열거 오류, 경계값(차속 0.0/300.0 통과, −0.1/300.1 실패, `True`를 숫자 자리에 넣으면 실패, NaN·inf 실패).

## 4. `freshness` (ASIL B)

### `is_stale(now_s: float, last_timestamp_s: float | None) -> bool`

```
if last_timestamp_s is None: return False      # NO_DATA는 controller가 따로 처리
return to_ms(now_s) - to_ms(last_timestamp_s) > STALE_THRESHOLD_MS
```

**단위 검증 기준**: 차이 200 ms → False, 201 ms → True, 기록 없음 → False. 부동소수 경계(0.05 × 4 누적) → 200 ms로 판정.

## 5. `decision` (ASIL B)

### 5.1 진입 함수

```
decide(snapshot: VehicleSnapshot | None,
       commands: tuple[DriverCommand, ...],
       previous: ControllerState,
       validity: InputValidity) -> Decision
```

처리 순서:

1. **crash latch 갱신**
   `latched = (previous.crash_latched and snapshot.ignition_on) or snapshot.crash_status == CONFIRMED`
   (snapshot이 None이면 `previous.crash_latched` 유지)
2. **입력 없음·무효 처리** (`_decide_without_input`)
   - `validity == NO_DATA` → 출력 유지, state 유지(초기 OFF), `hold`, `no_change` (SWR-024)
   - `validity == INVALID` → 출력 유지, state 유지, `input_invalid`, `input_invalid`. 이번 주기 명령은 적용하지 않음 (SWR-013 ①, D-13)
   - 단, `latched`이면 1순위 적용(아래 3단계)
3. **도어별 판정**: `left = _decide_door(LEFT, ctx)`, `right = _decide_door(RIGHT, ctx)`
4. **평가 결과 결합** (`_combine`): 5.4
5. **state 결정** (`_state_of`): 5.5

`ctx`는 `RuleContext(snapshot, commands, previous, latched, stale)` 불변 객체다. `stale = (validity == STALE)`.

### 5.2 도어 판정 `_decide_door(door, ctx) -> DoorVerdict`

```
for rule in RULES:                 # 1순위부터 순서대로
    verdict = rule(door, ctx)
    if verdict is not None: return _with_command_effect(door, verdict, ctx)
return _hold(door, ctx)            # 규칙 없음: 출력 유지, hold, no_change
```

`RULES = (_rule_crash, _rule_fault_or_stale, _rule_approach_risk, _rule_ignition_off, _rule_forced_release, _rule_isofix, _rule_auto_lock, _rule_driver)`

### 5.3 규칙 결정 테이블

`prev` = `previous`의 해당 도어 출력. `cmd(door)` = 이번 주기 명령 중 그 도어를 대상으로 하는(`side`가 그 도어 또는 `all`) 명령의 **마지막** 것.

| 순위 | 함수 | 적용 조건 | 출력 | `priority` | `reason_code` | SWR |
|---|---|---|---|---|---|---|
| 1 | `_rule_crash` | `ctx.latched` | RELEASE | `crash` | `crash_confirmed` | 007 |
| 2 | `_rule_fault_or_stale` | `snapshot.sensor_fault` | `prev` | `sensor_fault` | `sensor_fault` | 021 |
| 2 | 〃 | `ctx.stale` | `prev` | `input_stale` | `input_stale` | 013 ③ |
| 3 | `_rule_approach_risk` | 그 도어 접근위험 true | LOCK | `approach_risk` | `approach_risk_<door>` | 005 |
| 4 | `_rule_ignition_off` | `not snapshot.ignition_on` | RELEASE | `ignition_off` | `ignition_off` | 020 |
| 5 | `_rule_forced_release` | 화재·과온·성인 중 하나 true | RELEASE | `forced_release` | `fire` > `overtemperature` > `adult_present` 중 첫 true | 017 |
| 6 | `_rule_isofix` | 그 도어 ISOFIX true | LOCK | `isofix` | `isofix_<door>` | 018 |
| 7 | `_rule_auto_lock` | `snapshot.vehicle_speed_kph >= 3.0` | LOCK | `auto_lock` | `auto_lock_speed` | 003 |
| 8 | `_rule_driver` | `cmd(door)` 있음 | lock→LOCK, unlock→RELEASE | `driver_command` | `driver_lock` / `driver_unlock` | 001, 002 |
| — | `_hold` | 해당 없음 | `prev` | `hold` | `no_change` | 022 |

`stale`인 주기에는 `snapshot`이 마지막 유효 입력(오래된 값)이므로 2순위에서 멈추고 3순위 이하를 보지 않는다. sensor_fault와 stale이 동시면 sensor_fault를 먼저 검사한다(같은 2순위, 원인이 더 구체적).

**명령 효과 처리** `_with_command_effect(door, verdict, ctx)`: 1~7순위 규칙이 적용된 도어에 `cmd(door)`가 있으면(SWR-004)

| 적용 규칙 순위 | 명령 | 결과 |
|---|---|---|
| 3 (접근위험) | unlock | `suppressed_unlock=True`, `reason_code` 그대로(`approach_risk_<door>`) (SWR-005, SWR-006 입력) |
| 3 (접근위험) | lock | 변화 없음 |
| 4~7 | 모두 | `reason_code="driver_rejected"`, 출력·`priority`는 규칙 그대로 |
| 1~2 | 모두 | 변화 없음 (`crash_confirmed`, `sensor_fault`, `input_stale` 유지) — CR-01 |

### 5.4 결합 `_combine(left, right, ctx) -> (priority, reason_code)`

```
best = left if left.priority.rank <= right.priority.rank else right   # 같으면 좌측
reason = best.reason_code
if snapshot.crash_status == PENDING and best.priority.rank > 3:
    reason = "crash_pending"                                             # SWR-008
return best.priority, reason
```

### 5.5 state와 경고 코드 `_state_of(ctx, validity, previous)`

| 조건 (위에서부터 첫 일치) | state |
|---|---|
| `ctx.latched` | CRASH_RELEASE |
| `validity in (NO_DATA, INVALID)` | `previous.state` |
| `snapshot.sensor_fault` | FAULT |
| `ctx.stale` | DEGRADED |
| `not snapshot.ignition_on` | OFF |
| 그 밖 | NORMAL |

`warning_code`: 유효 입력이 있고 `snapshot.sensor_fault`이면 `W_SENSOR_FAULT`, 아니면 `None`.

`Decision.suppressed_unlocks`: `suppressed_unlock=True`인 도어를 LEFT, RIGHT 순으로 담는다.

**단위 검증 기준**: 결정 테이블의 각 행(규칙 적용·미적용), 인접 순위 7쌍(SWR-022), 명령 효과 표 각 행, 결합 동률(좌측 우선), PENDING 기록 조건(rank 3 이하/초과), state 표 각 행, latch 유지·해제 조건 4가지(이전 latch × ignition).

## 6. `override` (QM)

### `class OverrideTracker` (프로토콜 `OverrideAnnotator` 구현)

내부 상태(도어별): `first_suppressed_ms: int | None`, `active: bool`

```
annotate(decision, now_s, risk_left, risk_right) -> Annotation
    now = to_ms(now_s)
    reason = None
    for door in (LEFT, RIGHT):
        risk = 그 도어 접근위험
        if not risk:
            상태 초기화(first=None, active=False); continue
        if door in decision.suppressed_unlocks:
            first = 그 도어 first_suppressed_ms
            if first is not None and now - first <= OVERRIDE_WINDOW_MS:
                active = True; reason = reason or f"approach_override_{door}"
            else:
                first_suppressed_ms = now            # 새 첫 억제
    state = OVERRIDE if 어느 도어든 active else None
    if decision.state != NORMAL: return Annotation(None, None)   # 높은 state 보존
    return Annotation(state, reason)
```

- 초기화는 접근위험이 false가 된 평가에서 한다(SWR-006 ④).
- `Annotation`은 `state`와 `reason_code`만 갖는다. 출력 필드가 없다(AD-02).
- override가 성립한 뒤에도 `first_suppressed_ms`는 바꾸지 않는다. 같은 창 안의 추가 재입력도 override로 본다.

**단위 검증 기준**: 재입력 간격 10.000 s(성립), 10.001 s(불성립, 새 첫 억제), 부동소수 누적(0.05 × 200), 다른 도어 재입력(불성립), 접근위험 해제 시 초기화, decision.state가 NORMAL이 아니면 주석 없음.

## 7. `event_store` (QM)

### `class EventStore` (프로토콜 `EventSink` 구현)

```
__init__(capacity=EVENT_CAPACITY): self._events = deque(maxlen=capacity); self._next_id = 1
record(status, timestamp_s): append(Event(self._next_id, timestamp_s, status 필드 6개)); self._next_id += 1
list_events() -> tuple[Event, ...]: return tuple(self._events)      # 오름차순
```

`Event` 생성 시 `Status`에서 허용 필드만 복사한다(`warning_code` 제외, SWIF 6장). 파일·네트워크 I/O 없음.

**단위 검증 기준**: ID 1부터 증가, 100건·101건 경계, 필드 집합 = 허용 8개, 새 인스턴스는 빈 이력.

## 8. `clock` (ASIL B)

| 이름 | 설계 |
|---|---|
| `Clock` | `typing.Protocol`, `now() -> float` |
| `ManualClock` | 내부 정수 밀리초 `_ms`. `now()`는 `_ms / 1000`. `advance_ms(n)`은 `n >= 0`만 허용(음수면 `ValueError`) |
| `MonotonicClock` | `time.monotonic()` 기반. 생성 시각을 0으로 하는 상대 시각 |
| `to_ms(seconds) -> int` | `round(seconds * 1000)` (DD-C02) |

`to_ms`는 `freshness`, `override`도 쓰므로 `model`에 둔다(`freshness`가 `clock`을 import하지 않도록, SWA 4.2 규칙 3).

## 9. `controller` (ASIL B)

### `class ChildLockController`

```
__init__(clock: Clock, annotator: OverrideAnnotator, sink: EventSink)
    self._state = INITIAL_STATE; self._status = INITIAL_STATUS
    self._last_valid: VehicleSnapshot | None = None
    self._pending_snapshots = []; self._pending_commands = []

submit_snapshot(raw) / submit_command(raw): 목록에 추가 (검증은 step에서)

step() -> Status
    now = clock.now()
    validity, cycle_invalid = self._ingest_snapshots()     # 받은 순서대로 검증, 마지막 유효 입력 보관
    commands, cmd_invalid = self._ingest_commands()        # 무효 명령은 버리고 개수 기록
    validity = self._validity(now, validity)               # NO_DATA / INVALID / STALE / VALID
    decision = decide(self._last_valid, commands, self._state, validity)
    annotation = self._annotate(decision, now)             # 예외 시 주석 없음
    status = self._to_status(decision, annotation, validity, cmd_invalid)
    self._state = ControllerState(decision.lock_left, decision.lock_right, decision.state, decision.crash_latched)
    self._status = status
    self._record(status)                                   # 예외 시 무시(로그)
    return status

status() -> Status: return self._status
```

**입력 유효성 결정** `_validity(now, cycle)`

| 조건 (첫 일치) | 결과 |
|---|---|
| 이번 주기 마지막으로 받은 snapshot이 무효 | INVALID |
| 유효 입력을 한 번도 받지 않음 | NO_DATA |
| `is_stale(now, last_valid.source_timestamp_s)` | STALE |
| 그 밖 | VALID |

**상태 변환** `_to_status`: 출력은 `decision` 값 그대로. `state`는 `annotation.state or decision.state`. `reason_code`는 `annotation.reason_code or decision.reason_code`, 단 무효 명령이 있었고 결정 결과가 `hold`이면 `command_invalid`.

**QM 호출 보호**: `_annotate`, `_record`는 `try/except Exception`으로 감싸고 `logging.getLogger(__name__).exception(...)`으로 기록한다. 판정 결과와 출력은 이미 확정된 뒤다(SWA 10장).

**단위 검증 기준**: 초기 상태, 유효성 결정 표 각 행, 같은 주기 명령 순서, 무효 명령 이유 코드, override 주석 반영, QM 예외 주입 시 출력 불변, 출력은 annotation과 무관.

## 10. `replay` (QM)

| 이름 | 설계 |
|---|---|
| `ReplayStep` | dataclass: `advance_ms`(int), `snapshots`(tuple of dict), `commands`(tuple of dict) |
| `run(steps, annotator_factory, sink_factory) -> tuple[Status, ...]` | `ManualClock(0)`과 새 `ChildLockController`로 각 단계마다 시계 전진 → 입력 제출 → `step()` |
| `result_hash(statuses, events) -> str` | 상태·이벤트를 키 정렬 JSON(`sort_keys=True`, `separators=(",", ":")`)으로 만든 뒤 SHA-256 16진 문자열 |
| `load_vector(path) -> tuple[ReplayStep, ...]` | JSON 파일 읽기(UTF-8) |

**단위 검증 기준**: 같은 벡터 반복 실행 해시 동일, 입력 하나를 바꾸면 해시 변경, 시계 전진 누적.

## 11. `web` (QM)

| 이름 | 설계 |
|---|---|
| `create_app(controller, run_loop=True) -> FastAPI` | 라우트 등록. `run_loop`이면 시작 시 50 ms 주기 `asyncio` 작업으로 `controller.step()` 호출 |
| `POST /api/snapshot`, `POST /api/command` | JSON 본문을 그대로 `submit_*`. 응답 202 `{"accepted": true}`. JSON 구문 오류는 FastAPI가 422 |
| `GET /api/status` | `serialize_status(controller.status())` → 200. 직렬화 중 예외 → 500 `{"error": "serialization_failed"}` |
| `GET /api/events` | 이벤트 목록 JSON |
| `POST /api/step` | `run_loop=False`일 때 시험용 수동 평가 1회 |
| `GET /` | 정적 `index.html`: 입력 폼, 상태 표시(좌·우 출력, state, 입력 유효성, priority_reason, reason_code, warning_code), 1초 이하 주기 폴링 |
| `serialize_status(status) -> dict` | Enum은 `.value`, 나머지는 그대로. `priority_reason`을 `reason_code`와 함께 표시 |
| `__main__` | `uvicorn.run(create_app(...), host="127.0.0.1", port=8000)` |

**단위 검증 기준**: 각 라우트 응답 코드·본문, 직렬화 실패 주입 시 500, 정적 화면에 필수 표시 항목 존재.

## 12. 단위 구성 요약

| 모듈 | 단위(공개) | ASIL |
|---|---|---|
| `model` | Enum 10종, dataclass 10종, `door_lock`, `to_ms`, 상수 | B |
| `validation` | `parse_snapshot`, `parse_command` | B |
| `freshness` | `is_stale` | B |
| `decision` | `decide` (+ 규칙 함수 8개, `_hold`, `_with_command_effect`, `_combine`, `_state_of`) | B |
| `clock` | `Clock`, `ManualClock`, `MonotonicClock` | B |
| `controller` | `ChildLockController` | B |
| `override` | `OverrideTracker`, `Annotation` | QM |
| `event_store` | `EventStore` | QM |
| `replay` | `ReplayStep`, `run`, `result_hash`, `load_vector` | QM |
| `web` | `create_app`, `serialize_status`, 정적 화면 | QM |
