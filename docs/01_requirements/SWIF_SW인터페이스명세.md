# SWIF SW 인터페이스 명세

| 항목 | 내용 |
|---|---|
| 문서 ID | SWIF-001 |
| 상위 입력 | OEM-SWR-001 6장 외부 인터페이스 계약 (OEM-IF-001~009) |
| 베이스라인 | BL-SWR-1.0 (G1 승인 대기) |
| 관련 문서 | `SWR_SW요구사항명세.md`, `../00_plan/개발계획.md` 3장 결정 사항 |

SW 요구사항(SWR)이 참조하는 입력·출력 데이터의 논리 정의다. 전송 방식(HTTP 경로, 직렬화 형식)은 아키텍처 설계(SWE.2)에서 정한다.

## 1. 입력: VehicleSnapshot

차량에서 SW로 들어오는 상태 묶음이다. 한 번에 한 묶음씩 들어오며, 모든 필드가 함께 검증된다.

| 필드 | 형식 | 범위 / 값 | 출처 IF | 비고 |
|---|---|---|---|---|
| `source_timestamp_s` | 실수 | 0.0 이상, 단위 s | OEM-IF-001 | freshness 판정과 운전자 명령 시각의 기준 (D-11) |
| `vehicle_speed_kph` | 실수 | 0.0 ~ 300.0, 단위 km/h, 분해능 0.1 (D-07) | OEM-IF-001 | |
| `gear` | 열거 | `P`, `N`, `D`, `R` | OEM-IF-001 | 검증만 하며 판정에는 쓰지 않는다 (REV-F-03) |
| `crash_status` | 열거 | `NONE`, `PENDING`, `CONFIRMED` | OEM-IF-002 | |
| `rear_left_approach_risk` | 불리언 | `true` / `false` | OEM-IF-003 | |
| `rear_right_approach_risk` | 불리언 | `true` / `false` | OEM-IF-003 | |
| `fire_detected` | 불리언 | `true` / `false` | OEM-IF-007 | |
| `overtemperature_detected` | 불리언 | `true` / `false` | OEM-IF-007 | |
| `adult_present` | 불리언 | `true` / `false` | OEM-IF-007 | 성인 존재 여부만 표현. 영상·음성·개인 식별정보 없음 |
| `isofix_left` | 불리언 | `true` / `false` | OEM-IF-008 | |
| `isofix_right` | 불리언 | `true` / `false` | OEM-IF-008 | |
| `ignition_on` | 불리언 | `true` / `false` | OEM-IF-009 | |
| `sensor_fault` | 불리언 | `true` / `false` | OEM-IF-009 | |

**유효성 규칙** (SWR-013)
- 필드 누락, 형식 오류(예: 불리언 자리에 문자열), 범위 밖 값, 정의되지 않은 열거 값이 하나라도 있으면 묶음 전체가 INVALID다.
- 불리언은 JSON의 `true`/`false`만 허용한다. `0`/`1`, `"true"` 같은 값은 형식 오류다.
- 실수 필드에 불리언을 넣은 경우도 형식 오류다.

## 2. 입력: DriverCommand

운전자 명령이다. 받은 시각은 그 시점의 최신 유효 VehicleSnapshot의 `source_timestamp_s`를 쓴다 (OEM-IF-004, D-11).

| 필드 | 형식 | 값 | 출처 IF |
|---|---|---|---|
| `side` | 열거 | `left`, `right`, `all` | OEM-IF-004 |
| `action` | 열거 | `lock`, `unlock` | OEM-IF-004 |
| `source` | 열거 | `physical_button`, `avn`, `voice`, `mobile_app` | OEM-IF-004 |

필드 누락, 형식 오류, 등록되지 않은 값은 거절한다 (SWR-013).

## 3. 출력: 차일드락 논리 출력

| 필드 | 값 | 출처 IF | 비고 |
|---|---|---|---|
| `lock_left` | `LOCK` / `RELEASE` | OEM-IF-005 | 후석 좌측 차일드락 논리 명령 |
| `lock_right` | `LOCK` / `RELEASE` | OEM-IF-005 | 후석 우측 차일드락 논리 명령 |

PC/SIL 논리 출력까지만 다룬다. 구동기 적용 feedback은 범위 밖이다.

## 4. 출력: 상태 (Status)

표시 인터페이스(OEM-IF-006)로 제공하는 현재 상태다.

| 필드 | 형식 | 값 |
|---|---|---|
| `lock_left`, `lock_right` | 열거 | 3장과 같음 |
| `state` | 열거 | 5.1 상태 값 |
| `input_validity` | 열거 | `VALID`, `INVALID`, `STALE`, `NO_DATA` |
| `priority_reason` | 열거 | 5.2 판정 근거 값 |
| `reason_code` | 문자열 | 5.3 이유 코드 |
| `warning_code` | 문자열 또는 없음 | `W_SENSOR_FAULT` (센서 고장일 때만) |

`priority_reason`은 `reason_code`로도 매핑된다(OEM-IF-006). 상태를 직렬화하지 못하면 표시 인터페이스는 HTTP 500으로 응답한다.

## 5. 열거 값

### 5.1 state

| 값 | 의미 | 관련 요구 |
|---|---|---|
| `OFF` | 시동 꺼짐, 또는 기동 후 첫 유효 입력 전 | SWR-020, SWR-024 |
| `NORMAL` | 정상 판정 중 | — |
| `CRASH_RELEASE` | 충돌 확정에 따른 긴급 해제 유지 중 | SWR-007 |
| `FAULT` | 센서 고장으로 직전 확정 출력 유지 중 | SWR-021 |
| `DEGRADED` | 입력 freshness 상실로 직전 확정 출력 유지 중 | SWR-013 |
| `OVERRIDE` | 접근위험 중 운전자 재입력(override) 기록됨, 잠금 유지 중 | SWR-006 |

### 5.2 priority_reason (판정 우선순위, SWR-022)

| 순위 | 값 | 규칙 |
|---|---|---|
| 1 | `crash` | 충돌 CONFIRMED 긴급 해제 |
| 2 | `sensor_fault` | 센서 고장 출력 유지 |
| 2 | `input_stale` | freshness 상실 출력 유지 |
| 3 | `approach_risk` | 접근위험 도어 잠금 |
| 4 | `ignition_off` | 시동 꺼짐 해제 |
| 5 | `forced_release` | 화재·과온·성인 탑승 강제 해제 |
| 6 | `isofix` | ISOFIX 강제 잠금 |
| 7 | `auto_lock` | 주행 자동 잠금 |
| 8 | `driver_command` | 운전자 명령 |
| — | `hold` | 적용할 규칙 없음, 직전 출력 유지 |
| — | `input_invalid` | 입력 거절, 직전 출력 유지 |

### 5.3 reason_code

| 값 | 의미 |
|---|---|
| `crash_confirmed` | 충돌 CONFIRMED로 해제 |
| `crash_pending` | 충돌 PENDING, 해제하지 않음 |
| `sensor_fault` | 센서 고장, 출력 유지 |
| `input_stale` | 입력 freshness 상실, 출력 유지 |
| `input_invalid` | VehicleSnapshot 거절 |
| `command_invalid` | DriverCommand 거절 |
| `approach_risk_left`, `approach_risk_right` | 접근위험으로 해당 도어 잠금 또는 해제 억제 |
| `approach_override_left`, `approach_override_right` | 접근위험 억제 후 10초 이하 재입력 override 기록 |
| `ignition_off` | 시동 꺼짐 해제 |
| `fire`, `overtemperature`, `adult_present` | 해당 입력에 따른 강제 해제 |
| `isofix_left`, `isofix_right` | ISOFIX 강제 잠금 |
| `auto_lock_speed` | 차속 3.0 km/h 이상 자동 잠금 |
| `driver_lock`, `driver_unlock` | 운전자 명령 적용 |
| `driver_rejected` | 상위 규칙 때문에 운전자 명령을 적용하지 않음 |
| `no_change` | 적용할 규칙 없음 |

## 6. 출력: 결정 이벤트 (Event)

결정 이력 저장소(SWR-010~012)에 보존하는 기록이다. 아래 필드만 허용한다 (D-06).

| 필드 | 형식 | 비고 |
|---|---|---|
| `event_id` | 정수 | 프로세스 기동 후 1부터 1씩 증가 |
| `timestamp_s` | 실수 | 판정에 쓴 입력의 `source_timestamp_s` |
| `state` | 열거 | 5.1 |
| `lock_left`, `lock_right` | 열거 | 3장 |
| `priority_reason` | 열거 | 5.2 |
| `reason_code` | 문자열 | 5.3 |
| `input_validity` | 열거 | 4장 |
