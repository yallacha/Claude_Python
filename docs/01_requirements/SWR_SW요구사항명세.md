# SWR SW 요구사항 명세

| 항목 | 내용 |
|---|---|
| 문서 ID | SWR-SPEC-001 |
| 대상 | 전자식 차일드락 제어 SW (Python 3.12 PC/SIL 참조 구현, Web 시뮬레이터) |
| 상위 입력 | OEM-SWR-001 Rev 1.0 (BL-OEM-1.0) |
| 베이스라인 | BL-SWR-1.0 (G1 승인 대기) |
| 관련 문서 | `SWIF_SW인터페이스명세.md`, `UC_유스케이스.md`, `TRACE_추적성.md`, `REVIEW_검토기록.md`, `../00_plan/개발계획.md` |

## 1. 개요

OEM-SWR-001의 OEM 요구 13건을 SW 요구사항으로 도출한다. ID는 OEM-SWR-001 9장 추적 계획(SWR-001~021)을 따르고, SWR-019는 결번이다(D-08). 판정 우선순위, 평가 주기, 초기 상태는 OEM 요구 여러 건에 걸친 공통 규칙이라 SWR-022~024로 추가 도출했다.

OEM 사양서에 정의되지 않은 부분은 공급자 가정(D-xx, `../00_plan/개발계획.md` 3장)에 따른다. 공급자 가정은 OEM 확인 질의 대상이며 `REVIEW_검토기록.md` 4장에 목록이 있다.

## 2. 공통 정의

| 용어 | 정의 |
|---|---|
| 평가 주기 | SW가 입력을 읽고 출력을 결정하는 주기. 50 ms 고정 (SWR-023, D-03) |
| 다음 평가주기 | 입력이 바뀐 뒤 처음 실행되는 평가. 입력 변화 후 최대 50 ms 안에 실행된다 |
| 확정 출력 | 직전 평가에서 결정되어 내보낸 `lock_left`, `lock_right` 값 |
| 유효 입력 | 유효성 규칙(SWIF 1장)을 통과한 VehicleSnapshot |
| freshness 상실 | 평가 시각 − 최신 유효 VehicleSnapshot의 `source_timestamp_s` > 0.200 s |
| 출력 유지 | 출력을 바꾸지 않고 확정 출력을 그대로 내보냄 |
| 해제 억제 | 운전자 해제 명령을 적용하지 않고 잠금을 유지함 |

이 문서의 "SW는 ~해야 한다"는 PC/SIL 참조 구현의 동작 요구다. 시간 요구는 주입형 시계(고정 시계)를 기준으로 판정한다.

## 3. 요구사항 목록

| ID | 제목 | 분류 | ASIL | 상위 OEM 요구 | 검증 수준 |
|---|---|---|---|---|---|
| SWR-001 | 운전자 잠금 명령 처리 | 기능 | QM | OEM-FR-001 | 단위, 시스템(PC/SIL, Web) |
| SWR-002 | 운전자 해제 명령 처리 | 기능 | QM | OEM-FR-001 | 단위, 시스템(PC/SIL, Web) |
| SWR-003 | 주행 자동 잠금 | 기능 | QM | OEM-FR-002 | 단위, 시스템(PC/SIL) |
| SWR-004 | 운전자 명령 적용 조건 | 기능 | QM | OEM-FR-001 | 단위, 시스템(PC/SIL) |
| SWR-005 | 접근위험 도어 잠금과 해제 억제 | 기능(안전) | B | OEM-SR-002 | 단위, 시스템(PC/SIL) |
| SWR-006 | 접근위험 억제 후 재입력 override | 기능 | QM | OEM-SR-002, OEM-FR-003 | 단위, 시스템(PC/SIL, Web) |
| SWR-007 | 충돌 확정 긴급 해제 | 기능(안전) | B | OEM-SR-001 | 단위, 시스템(PC/SIL) |
| SWR-008 | 충돌 판정 대기(PENDING) 처리 | 기능(안전) | B | OEM-SR-001 | 단위, 시스템(PC/SIL) |
| SWR-009 | 좌·우 독립 판정 | 기능(안전) | B | OEM-SR-002 | 단위, 시스템(PC/SIL) |
| SWR-010 | 결정 이벤트 ID 부여 | 비기능 | QM | OEM-NFR-002 | 단위, 통합 |
| SWR-011 | 결정 이벤트 허용 필드 | 비기능 | QM | OEM-NFR-002 | 단위, 통합 |
| SWR-012 | 결정 이력 용량과 휘발성 | 비기능 | QM | OEM-NFR-002 | 단위, 통합 |
| SWR-013 | 입력 유효성·freshness 감시 | 기능(안전) | B | OEM-SR-003 | 단위, 시스템(PC/SIL) |
| SWR-014 | 상태 조회 | 기능 | QM | OEM-FR-004 | 통합, 시스템(Web) |
| SWR-015 | 상태 표시와 직렬화 오류 응답 | 기능 | QM | OEM-FR-004 | 통합, 시스템(Web) |
| SWR-016 | 결정론적 재생 | 비기능 | QM | OEM-NFR-001 | 시스템(PC/SIL) |
| SWR-017 | 화재·과온·성인 탑승 강제 해제 | 기능 | QM | OEM-FR-005 | 단위, 시스템(PC/SIL, Web) |
| SWR-018 | ISOFIX 강제 잠금 | 기능 | QM | OEM-FR-006 | 단위, 시스템(PC/SIL, Web) |
| SWR-019 | (결번) | — | — | — | — |
| SWR-020 | 시동 꺼짐 해제 | 기능 | QM | OEM-FR-007 | 단위, 시스템(PC/SIL, Web) |
| SWR-021 | 센서 고장 출력 유지 | 기능(안전) | B | OEM-SR-004 | 단위, 시스템(PC/SIL) |
| SWR-022 | 판정 우선순위 | 기능(안전) | B | OEM-SR-001, SR-002, SR-004, FR-002, FR-005, FR-006, FR-007 | 단위, 시스템(PC/SIL) |
| SWR-023 | 평가 주기 | 비기능(타이밍) | B | OEM-SR-001, OEM-SR-003 | 단위, 시스템(PC/SIL) |
| SWR-024 | 기동 시 초기 상태 | 기능 | QM | OEM-FR-007 | 단위, 시스템(PC/SIL) |

ASIL B 요구는 OEM이 ASIL B로 할당한 OEM-SR-001~004에서 도출된 요구다. SWR-006은 OEM-SR-002와 관련되지만 ASIL B 출력(잠금)을 바꾸지 않으므로 QM이다(D-02). SWR-022, SWR-023은 ASIL B 요구의 동작을 결정하므로 ASIL B로 둔다.

## 4. 요구사항 상세

각 요구사항의 검증 기준은 SW 검증(SWE.6) 시험 사양서의 베이시스가 된다. 출처가 공급자 가정이면 D-xx로 표시한다.

### SWR-001 운전자 잠금 명령 처리

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 유효한 DriverCommand(`action=lock`)를 받으면, SWR-004의 적용 조건을 만족할 때 `side`가 지정한 출력(`left`→`lock_left`, `right`→`lock_right`, `all`→둘 다)만 다음 평가주기에 `LOCK`으로 해야 한다. 지정하지 않은 출력은 바꾸지 않아야 한다. |
| 검증 기준 | 정지(0.0 km/h)·정상 입력·모든 출력 RELEASE에서 `source` 4종 × `side` 3종 각각에 대해, 다음 평가주기에 지정 출력만 LOCK이고 나머지는 RELEASE이며 `reason_code=driver_lock`이다. |
| 출처 | OEM-FR-001 |
| 관련 IF | OEM-IF-004, OEM-IF-005 |

### SWR-002 운전자 해제 명령 처리

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 유효한 DriverCommand(`action=unlock`)를 받으면, SWR-004의 적용 조건을 만족할 때 `side`가 지정한 출력만 다음 평가주기에 `RELEASE`로 해야 한다. 지정하지 않은 출력은 바꾸지 않아야 한다. |
| 검증 기준 | 정지·정상 입력·모든 출력 LOCK에서 `source` 4종 × `side` 3종 각각에 대해, 다음 평가주기에 지정 출력만 RELEASE이고 나머지는 LOCK이며 `reason_code=driver_unlock`이다. |
| 출처 | OEM-FR-001 |
| 관련 IF | OEM-IF-004, OEM-IF-005 |

### SWR-003 주행 자동 잠금

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 유효 입력의 `vehicle_speed_kph`가 3.0 이상인 평가주기마다, 상위 우선순위 규칙(SWR-022 1~6순위)이 적용되지 않는 출력을 `LOCK`으로 해야 한다. 차속이 3.0 미만으로 내려가도 출력을 자동으로 해제하지 않아야 한다. |
| 검증 기준 | ① 차속 3.0 km/h인 첫 평가주기에 두 출력이 LOCK, `reason_code=auto_lock_speed`. ② 차속 2.9 km/h에서는 자동 잠금하지 않음. ③ 3.0 이상에서 2.9로 내려간 뒤에도 출력 LOCK 유지. |
| 출처 | OEM-FR-002, D-07(분해능 0.1) |
| 관련 IF | OEM-IF-001, OEM-IF-005 |

### SWR-004 운전자 명령 적용 조건

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 운전자 명령을 판정 우선순위(SWR-022) 8순위로 처리해야 한다. 지정된 출력에 1~7순위 규칙 중 하나라도 적용되고 있으면 그 출력에는 명령을 적용하지 않고, `reason_code`를 상위 규칙이 접근위험이면 `approach_risk_<side>`(SWR-005), 그 밖에는 `driver_rejected`로 해야 한다. `side=all`이면 좌·우를 각각 판정한다. |
| 검증 기준 | ① 차속 3.0 km/h 이상에서 해제 명령 → 출력 LOCK 유지, `driver_rejected`. ② `isofix_left=true`에서 좌측 해제 명령 → 좌측 LOCK 유지. ③ `ignition_on=false`에서 잠금 명령 → 출력 RELEASE 유지. ④ 화재 입력 중 잠금 명령 → RELEASE 유지. ⑤ `side=all` 해제 명령에서 좌측만 ISOFIX이면 우측만 RELEASE. |
| 출처 | OEM-FR-001("일반 해제 허용조건"), D-01 |
| 관련 IF | OEM-IF-004 |

### SWR-005 접근위험 도어 잠금과 해제 억제

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 `rear_left_approach_risk`(또는 `rear_right_approach_risk`)가 `true`인 평가주기마다 해당 도어 출력을 `LOCK`으로 하고, 그 도어에 대한 운전자 해제 명령과 하위 우선순위(4~8순위)의 해제를 적용하지 않아야 한다. 잠금 또는 해제 억제 시 `reason_code=approach_risk_<side>`를 기록해야 한다. |
| 검증 기준 | ① 좌측 접근위험 true가 된 다음 평가주기에 `lock_left=LOCK`, `approach_risk_left`. ② 그 상태에서 좌측 해제 명령 → LOCK 유지, `approach_risk_left`가 이벤트로 기록. ③ 접근위험 true와 `ignition_on=false` 동시 → 해당 도어 LOCK 유지. |
| 출처 | OEM-SR-002, D-01 |
| 관련 IF | OEM-IF-003, OEM-IF-004, OEM-IF-005 |

### SWR-006 접근위험 억제 후 재입력 override

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 SWR-005로 어떤 도어의 운전자 해제 명령을 처음 억제한 시각부터 10.0 s 이하에 같은 도어에 대한 해제 명령이 다시 들어오면, `state=OVERRIDE`와 `reason_code=approach_override_<side>`를 생성해야 한다. 이때 해당 도어의 접근위험이 `true`인 동안 출력은 `LOCK`을 유지해야 한다. 10.0 s를 초과한 재입력은 새로운 첫 억제로 처리해야 한다. `state=OVERRIDE`는 그 도어의 접근위험이 `false`가 되면 끝난다. |
| 검증 기준 | ① 첫 억제 후 10.0 s에 재입력 → OVERRIDE, `approach_override_left`, 출력 LOCK. ② 10.1 s에 재입력 → OVERRIDE 아님, `approach_risk_left`(새 첫 억제). ③ 우측 억제 후 좌측 재입력 → override 아님. ④ 접근위험 false가 된 평가주기에 OVERRIDE 종료. |
| 출처 | OEM-FR-003, OEM-SR-002, D-02 |
| 관련 IF | OEM-IF-003, OEM-IF-004, OEM-IF-006 |

### SWR-007 충돌 확정 긴급 해제

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 유효 입력의 `crash_status`가 `CONFIRMED`가 되면 다른 모든 규칙보다 우선하여 300 ms 이내에 두 출력을 `RELEASE`로 하고 `state=CRASH_RELEASE`, `reason_code=crash_confirmed`로 해야 한다. 이후 `crash_status`가 바뀌어도 `ignition_on=false`가 될 때까지 두 출력의 RELEASE를 유지해야 한다. |
| 검증 기준 | ① 모든 출력 LOCK·접근위험 true·차속 50 km/h에서 CONFIRMED 입력 → 300 ms 이내 두 출력 RELEASE. ② 이후 `crash_status=NONE`, 잠금 명령, 차속 50 km/h 입력에도 RELEASE 유지. ③ `ignition_on=false` 후 CRASH_RELEASE 해제(SWR-020 적용). ④ `sensor_fault=true`와 동시에 CONFIRMED → RELEASE. |
| 출처 | OEM-SR-001, D-01, D-12(해제 유지 기간) |
| 관련 IF | OEM-IF-002, OEM-IF-005, OEM-IF-006 |

### SWR-008 충돌 판정 대기(PENDING) 처리

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 `crash_status=PENDING`이면 긴급 해제를 하지 않고, 다른 규칙으로 출력을 판정하며, 그 평가주기에 1~3순위 규칙(SWR-022)이 적용되지 않으면 `reason_code=crash_pending`을 기록해야 한다. 1~3순위 규칙이 적용되면 그 규칙의 이유 코드를 기록한다. |
| 검증 기준 | ① 모든 출력 LOCK·정지에서 PENDING → 출력 LOCK 유지, `crash_pending`. ② PENDING 다음 CONFIRMED → SWR-007 적용. ③ PENDING 다음 NONE → 출력 변화 없음. |
| 출처 | OEM-SR-001(추적 계획 "PENDING 처리"), D-05 |
| 관련 IF | OEM-IF-002 |

### SWR-009 좌·우 독립 판정

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 좌·우 출력을 도어별 입력(접근위험, ISOFIX)과 `side` 지정에 따라 독립적으로 판정해야 한다. 한쪽 도어에만 해당하는 입력은 반대쪽 출력을 바꾸지 않아야 한다. |
| 검증 기준 | ① 좌측 접근위험 true, 우측 false에서 `side=all` 해제 → 좌측 LOCK, 우측 RELEASE. ② 우측 접근위험만 true → 좌측 출력 변화 없음. |
| 출처 | OEM-SR-002(추적 계획 "좌우 독립") |
| 관련 IF | OEM-IF-003, OEM-IF-005 |

### SWR-010 결정 이벤트 ID 부여

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 평가주기마다 결정 이벤트 1건을 만들고, 프로세스 기동 후 1부터 1씩 증가하는 `event_id`를 부여해야 한다. |
| 검증 기준 | 평가 5회 후 이벤트 `event_id`가 1, 2, 3, 4, 5 순서다. 재기동 후 첫 이벤트는 다시 1이다. |
| 출처 | OEM-NFR-002(추적 계획 "이벤트 ID") |
| 관련 IF | SWIF 6장 |

### SWR-011 결정 이벤트 허용 필드

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 결정 이벤트에 SWIF 6장의 허용 필드만 저장해야 한다. 영상, 음성, 개인 식별자(이름, 전화번호, 계정, 기기 ID 등)는 저장하지 않아야 한다. DriverCommand의 `source`도 저장하지 않는다. |
| 검증 기준 | 모든 입력 종류를 넣은 뒤 조회한 각 이벤트의 필드 집합이 허용 필드 8개와 정확히 같다. |
| 출처 | OEM-NFR-002(추적 계획 "스키마, 금지정보"), D-06 |
| 관련 IF | SWIF 6장 |

### SWR-012 결정 이력 용량과 휘발성

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 결정 이벤트를 메모리에만 보존하고, 최신 100건을 넘으면 가장 오래된 이벤트부터 버려야 한다. 이력은 `event_id` 오름차순으로 조회되어야 한다. 파일, DB 등 영구 저장소에 기록하지 않아야 한다. |
| 검증 기준 | ① 101건 생성 후 조회 결과가 `event_id` 2~101의 100건, 오름차순. ② 100건 생성 후 조회 결과 100건. ③ 프로세스 재기동 후 조회 결과 0건. ④ 실행 중 작업 폴더에 새 파일이 생기지 않음. |
| 출처 | OEM-NFR-002(추적 계획 "휘발성") |
| 관련 IF | SWIF 6장 |

### SWR-013 입력 유효성·freshness 감시

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 VehicleSnapshot과 DriverCommand를 판정 전에 SWIF 1·2장 규칙으로 검증해야 한다. ① 유효하지 않은 VehicleSnapshot은 판정에 쓰지 않고, 출력을 유지하며, `input_validity=INVALID`, `reason_code=input_invalid`로 해야 한다(D-13). ② 유효하지 않은 DriverCommand는 적용하지 않고 `reason_code=command_invalid`로 해야 한다. ③ 최신 유효 VehicleSnapshot이 200 ms를 초과해 갱신되지 않으면 100 ms 이내에 `state=DEGRADED`, `input_validity=STALE`이 되고 출력을 유지해야 한다. ④ DEGRADED 중에는 운전자 명령을 적용하지 않아야 한다(D-04). ⑤ 새 유효 VehicleSnapshot이 들어오면 DEGRADED를 끝내고 정상 판정으로 돌아가야 한다. |
| 검증 기준 | ① 차속 300.1, −0.1, 누락, 문자열, `crash_status=UNKNOWN` 각각 → INVALID, 출력 유지. 차속 0.0, 300.0 → 유효. ② 미등록 `source`·`side`·`action` 명령 → 적용 안 됨. ③ 마지막 유효 입력 후 200 ms까지는 VALID, 200 ms 초과 후 100 ms 이내 DEGRADED. ④ DEGRADED 중 해제 명령 → 출력 유지. ⑤ 유효 입력 재수신 시 DEGRADED 종료. |
| 출처 | OEM-SR-003, D-04, D-13 |
| 관련 IF | OEM-IF-001~004, OEM-IF-007~009 |

### SWR-014 상태 조회

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 상태 조회 요청에 SWIF 4장의 필드(`lock_left`, `lock_right`, `state`, `input_validity`, `priority_reason`, `reason_code`, `warning_code`)를 담아 최신 평가 결과로 응답해야 한다. |
| 검증 기준 | 평가 후 상태 조회 응답에 7개 필드가 모두 있고 값이 직전 평가 결과와 같다. |
| 출처 | OEM-FR-004 |
| 관련 IF | OEM-IF-006 |

### SWR-015 상태 표시와 직렬화 오류 응답

| 속성 | 내용 |
|---|---|
| 요구사항 | Web 시뮬레이터는 SWR-014의 상태(좌·우 출력, state, 입력 유효성, 최근 결정 이유)를 화면에 표시해야 한다. `priority_reason`은 `reason_code`로도 표시해야 한다. 상태를 직렬화하지 못하면 HTTP 500으로 응답해야 한다. |
| 검증 기준 | ① 입력 주입 후 화면에 좌·우 출력, state, 입력 유효성, 이유 코드가 표시된다. ② 직렬화 실패를 주입하면 상태 조회 응답이 HTTP 500이다. |
| 출처 | OEM-FR-004, OEM-IF-006, D-09 |
| 관련 IF | OEM-IF-006 |

### SWR-016 결정론적 재생

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 같은 초기 상태와 같은 입력 순서(입력 값과 입력 시각)를 고정 시계로 재생하면 항상 같은 공개 결과(평가마다의 상태와 이벤트 목록)를 만들어야 한다. 판정에 실제 시계, 난수, 실행 환경에 따라 달라지는 값을 쓰지 않아야 한다. |
| 검증 기준 | 모든 규칙을 거치는 입력 벡터를 고정 시계로 1,000회 재생했을 때 공개 결과 해시(SHA-256)가 모두 같다. |
| 출처 | OEM-NFR-001 |
| 관련 IF | SWIF 4·6장 |

### SWR-017 화재·과온·성인 탑승 강제 해제

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 유효 입력의 `fire_detected`, `overtemperature_detected`, `adult_present` 중 하나라도 `true`이면 다음 평가주기에 두 출력을 `RELEASE`로 하고, 입력별 이유 코드(`fire`, `overtemperature`, `adult_present`)를 기록해야 한다. 여러 개가 동시에 `true`이면 `fire` > `overtemperature` > `adult_present` 순서로 하나를 기록한다(D-15). 해당 입력이 `true`인 동안 하위 우선순위(6~8순위)의 잠금을 적용하지 않아야 한다. 단, 상위 규칙(1~4순위)이 적용되는 출력은 그 규칙을 따른다. |
| 검증 기준 | ① 각 입력을 단독 주입 → 다음 평가주기에 두 출력 RELEASE, 해당 이유 코드. ② 차속 50 km/h에서 `adult_present=true` → RELEASE. ③ 화재와 ISOFIX 동시 → RELEASE. ④ 화재와 좌측 접근위험 동시 → 좌측 LOCK, 우측 RELEASE. ⑤ 세 입력 동시 → `fire`. |
| 출처 | OEM-FR-005, D-01, D-15 |
| 관련 IF | OEM-IF-007, OEM-IF-005 |

### SWR-018 ISOFIX 강제 잠금

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 `isofix_left`(또는 `isofix_right`)가 `true`인 평가주기마다 해당 도어 출력을 `LOCK`으로 하고 `reason_code=isofix_<side>`를 기록해야 한다. 반대쪽 출력은 바꾸지 않아야 한다. 상위 규칙(1~5순위)이 적용되는 출력은 그 규칙을 따른다. |
| 검증 기준 | ① 모든 출력 RELEASE에서 `isofix_left=true`만 → 다음 평가주기에 좌측 LOCK, 우측 RELEASE 유지. ② ISOFIX 좌측 true 중 좌측 해제 명령 → 좌측 LOCK 유지. ③ `isofix_left=true`와 `ignition_on=false` 동시 → 좌측 RELEASE. |
| 출처 | OEM-FR-006, D-01 |
| 관련 IF | OEM-IF-008, OEM-IF-005 |

### SWR-020 시동 꺼짐 해제

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 유효 입력의 `ignition_on`이 `false`인 첫 평가주기에 두 출력을 `RELEASE`로 하고 `state=OFF`, `reason_code=ignition_off`로 해야 한다. `ignition_on=false`인 동안 하위 우선순위(5~8순위)를 적용하지 않아야 한다. 상위 규칙(1~3순위)이 적용되는 출력은 그 규칙을 따른다. |
| 검증 기준 | ① 두 출력 LOCK에서 `ignition_on=false` → 첫 평가주기에 두 출력 RELEASE, OFF, `ignition_off`. ② 좌측 접근위험 true와 동시 → 좌측 LOCK, 우측 RELEASE. ③ `ignition_on=true` 복귀 후 출력 RELEASE 유지, state NORMAL. |
| 출처 | OEM-FR-007, D-01 |
| 관련 IF | OEM-IF-009, OEM-IF-005, OEM-IF-006 |

### SWR-021 센서 고장 출력 유지

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 유효 입력의 `sensor_fault`가 `true`인 첫 평가주기부터 새 명령과 하위 우선순위(3~8순위) 규칙을 적용하지 않고 확정 출력을 유지해야 한다. 이때 `state=FAULT`, `warning_code=W_SENSOR_FAULT`, `reason_code=sensor_fault`를 제공해야 한다. 충돌 확정(1순위)은 적용한다. `sensor_fault=false`가 된 평가주기부터 정상 판정으로 돌아가야 한다. |
| 검증 기준 | ① 좌 LOCK·우 RELEASE에서 `sensor_fault=true` → 첫 평가주기에 좌 LOCK·우 RELEASE 유지, FAULT, `W_SENSOR_FAULT`. ② FAULT 중 해제 명령, 차속 50 km/h, ISOFIX true → 출력 유지. ③ FAULT 중 충돌 CONFIRMED → RELEASE. ④ `sensor_fault=false` 복귀 후 정상 판정. |
| 출처 | OEM-SR-004, D-01 |
| 관련 IF | OEM-IF-009, OEM-IF-005, OEM-IF-006 |

### SWR-022 판정 우선순위

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 평가주기마다 좌·우 출력을 아래 우선순위로 각각 판정해야 한다. 한 출력에 여러 규칙이 해당하면 가장 높은 순위의 규칙만 적용하고, 그 규칙을 `priority_reason`으로 제공해야 한다. ① 충돌 확정 해제(SWR-007) ② 센서 고장(SWR-021) 또는 freshness 상실(SWR-013) 시 출력 유지 ③ 접근위험 잠금(SWR-005) ④ 시동 꺼짐 해제(SWR-020) ⑤ 화재·과온·성인 탑승 해제(SWR-017) ⑥ ISOFIX 잠금(SWR-018) ⑦ 주행 자동 잠금(SWR-003) ⑧ 운전자 명령(SWR-001, SWR-002). 해당 규칙이 없으면 출력을 유지하고 `priority_reason=hold`로 한다. 좌·우가 서로 다른 규칙으로 판정되면 그 평가의 `priority_reason`과 `reason_code`는 둘 중 높은 순위 규칙의 것으로 하고, 순위가 같으면 좌측 것으로 한다. |
| 검증 기준 | 인접한 두 순위 규칙을 동시에 만족시키는 입력 7쌍(①+②, ②+③, ③+④, ④+⑤, ⑤+⑥, ⑥+⑦, ⑦+⑧) 각각에서 높은 순위 규칙의 출력과 `priority_reason`이 나온다. 규칙이 없을 때 출력 유지, `hold`. 좌측 ISOFIX(⑥)·우측 운전자 해제(⑧)가 함께 적용되면 `priority_reason=isofix`, `reason_code=isofix_left`. |
| 출처 | OEM-SR-001("다른 명령보다 우선"), OEM-SR-002, SR-004, FR-002, FR-005, FR-006, FR-007, D-01 |
| 관련 IF | OEM-IF-005, OEM-IF-006 |

### SWR-023 평가 주기

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 50 ms 고정 주기로 평가해야 한다. 각 평가는 그 시점의 최신 유효 VehicleSnapshot과 직전 평가 이후 받은 DriverCommand(받은 순서대로)를 사용해야 한다. |
| 검증 기준 | ① 고정 시계로 1.0 s 동안 평가 횟수가 20회. ② 한 주기에 받은 명령 2건(좌측 잠금, 좌측 해제)이 받은 순서대로 적용되어 최종 좌측 RELEASE. ③ SWR-007(300 ms), SWR-013(100 ms) 시간 요구를 주기 단위로 만족. |
| 출처 | OEM-SR-001, OEM-SR-003, D-03 |
| 관련 IF | — |

### SWR-024 기동 시 초기 상태

| 속성 | 내용 |
|---|---|
| 요구사항 | SW는 기동 직후 두 출력을 `RELEASE`, `state=OFF`, `input_validity=NO_DATA`로 해야 한다. 첫 유효 VehicleSnapshot이 들어오기 전에는 운전자 명령을 적용하지 않아야 한다. |
| 검증 기준 | ① 기동 직후 상태 조회 → RELEASE/RELEASE, OFF, NO_DATA. ② 유효 입력 전 잠금 명령 → 출력 RELEASE 유지. ③ 첫 유효 입력(`ignition_on=true`) 후 state NORMAL. |
| 출처 | OEM-FR-007("초기 해제 상태"), D-14 |
| 관련 IF | OEM-IF-005, OEM-IF-006 |
