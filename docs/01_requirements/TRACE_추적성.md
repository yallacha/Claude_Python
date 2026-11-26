# TRACE 요구사항 양방향 추적성

| 항목 | 내용 |
|---|---|
| 문서 ID | TRACE-SWR-001 |
| 범위 | OEM-SWR-001 (OEM 요구, 인터페이스) ↔ SWR ↔ UC |
| 베이스라인 | BL-SWR-1.0 (G1 승인 대기) |

설계(SWE.2/3), 시험(SWE.4~6) 산출물과의 추적은 각 단계에서 이 표에 열을 추가한다.

## 1. 순방향: OEM 요구 → SWR

| OEM 요구 | 분류 | OEM 추적 계획(9장) | 도출 SWR | 차이와 근거 |
|---|---|---|---|---|
| OEM-SR-001 | ASIL B | SWR-007, SWR-008 | SWR-007, SWR-008, SWR-022, SWR-023 | 우선순위(SWR-022), 300 ms 판정 주기(SWR-023) 추가 도출 |
| OEM-SR-002 | ASIL B | SWR-005, SWR-006, SWR-009 | SWR-005, SWR-006, SWR-009, SWR-022 | 우선순위 추가 도출 |
| OEM-SR-003 | ASIL B | SWR-013 | SWR-013, SWR-023 | 100 ms 판정 주기 추가 도출 |
| OEM-SR-004 | ASIL B | SWR-021 | SWR-021, SWR-022 | 우선순위 추가 도출 |
| OEM-FR-001 | QM | SWR-001, SWR-002, SWR-004 | SWR-001, SWR-002, SWR-004 | 계획과 같음 |
| OEM-FR-002 | QM | SWR-003 | SWR-003, SWR-022 | 우선순위 추가 도출 |
| OEM-FR-003 | QM | SWR-006 | SWR-006 | 계획과 같음 |
| OEM-FR-004 | QM | SWR-014, SWR-015 | SWR-014, SWR-015 | 계획과 같음 |
| OEM-FR-005 | QM | SWR-017 | SWR-017, SWR-022 | 우선순위 추가 도출 |
| OEM-FR-006 | QM | SWR-018 | SWR-018, SWR-022 | 우선순위 추가 도출 |
| OEM-FR-007 | QM | SWR-020 | SWR-020, SWR-022, SWR-024 | 우선순위, 기동 초기 상태 추가 도출 |
| OEM-NFR-001 | QM | SWR-016 | SWR-016 | 계획과 같음 |
| OEM-NFR-002 | QM | SWR-010, SWR-011, SWR-012 | SWR-010, SWR-011, SWR-012 | 계획과 같음 |

OEM 요구 13건 모두 1건 이상의 SWR로 도출됐다(13/13).

## 2. 순방향: OEM 인터페이스 → SWR

| OEM 인터페이스 | 데이터 | SWIF 위치 | 사용 SWR |
|---|---|---|---|
| OEM-IF-001 | 차속, 기어, 시각 | 1장 | SWR-003, SWR-013, SWR-023 |
| OEM-IF-002 | 충돌 상태 | 1장 | SWR-007, SWR-008, SWR-013 |
| OEM-IF-003 | 후측방 접근위험 | 1장 | SWR-005, SWR-006, SWR-009, SWR-013 |
| OEM-IF-004 | 운전자 명령 | 2장 | SWR-001, SWR-002, SWR-004, SWR-006, SWR-013 |
| OEM-IF-005 | 좌·우 논리 출력 | 3장 | SWR-001~009, SWR-017, SWR-018, SWR-020~022, SWR-024 |
| OEM-IF-006 | 표시 상태 | 4장 | SWR-006, SWR-007, SWR-014, SWR-015, SWR-020~022, SWR-024 |
| OEM-IF-007 | 화재, 과온, 성인 존재 | 1장 | SWR-013, SWR-017 |
| OEM-IF-008 | ISOFIX | 1장 | SWR-013, SWR-018 |
| OEM-IF-009 | 시동, 센서 고장 | 1장 | SWR-013, SWR-020, SWR-021 |

OEM 인터페이스 9건 모두 SWIF와 SWR에 반영됐다(9/9).

## 3. 역방향: SWR → 상위 요구, 공급자 가정, 유스케이스

| SWR | 상위 OEM 요구 | 공급자 가정 | UC |
|---|---|---|---|
| SWR-001 | OEM-FR-001 | — | UC-01 |
| SWR-002 | OEM-FR-001 | — | UC-01 |
| SWR-003 | OEM-FR-002 | D-07 | UC-02 |
| SWR-004 | OEM-FR-001 | D-01 | UC-01 |
| SWR-005 | OEM-SR-002 | D-01 | UC-03 |
| SWR-006 | OEM-FR-003, OEM-SR-002 | D-02 | UC-03 |
| SWR-007 | OEM-SR-001 | D-01, D-12 | UC-04 |
| SWR-008 | OEM-SR-001 | D-05 | UC-04 |
| SWR-009 | OEM-SR-002 | — | UC-01, UC-03, UC-06 |
| SWR-010 | OEM-NFR-002 | — | UC-10 |
| SWR-011 | OEM-NFR-002 | D-06 | UC-10 |
| SWR-012 | OEM-NFR-002 | — | UC-10 |
| SWR-013 | OEM-SR-003 | D-04, D-11, D-13 | UC-08 |
| SWR-014 | OEM-FR-004 | — | UC-09 |
| SWR-015 | OEM-FR-004 | D-09 | UC-09 |
| SWR-016 | OEM-NFR-001 | — | UC-10 |
| SWR-017 | OEM-FR-005 | D-01, D-15 | UC-05 |
| SWR-018 | OEM-FR-006 | D-01 | UC-06 |
| SWR-019 | (결번, D-08) | D-08 | — |
| SWR-020 | OEM-FR-007 | D-01 | UC-07 |
| SWR-021 | OEM-SR-004 | D-01 | UC-08 |
| SWR-022 | OEM-SR-001, SR-002, SR-004, FR-002, FR-005, FR-006, FR-007 | D-01 | UC-02, UC-04, UC-05 |
| SWR-023 | OEM-SR-001, OEM-SR-003 | D-03 | UC-01, UC-04 |
| SWR-024 | OEM-FR-007 | D-14 | UC-07 |

SWR 23건(결번 제외) 모두 상위 OEM 요구를 가진다. 상위 요구 없이 공급자 가정만으로 만든 SWR은 없다.

## 4. 수용기준 대응: OEM 수용기준 → SWR 검증 기준

| OEM 요구 | OEM 수용기준 핵심 | 대응 SWR 검증 기준 |
|---|---|---|
| OEM-SR-001 | 300 ms 이내 두 출력 RELEASE, 이후 유지 | SWR-007 ①② |
| OEM-SR-002 | 해당 출력 LOCK, 해제 요청에도 유지, 원인 기록 | SWR-005 ①② |
| OEM-SR-003 | 200 ms 초과 미갱신 시 100 ms 이내 DEGRADED, 형식·범위 오류 거절 | SWR-013 ①③ |
| OEM-SR-004 | 첫 평가주기 출력 유지, FAULT, 경고코드 | SWR-021 ① |
| OEM-FR-001 | source 4종, LEFT/RIGHT/ALL, 선택 출력에만 적용 | SWR-001, SWR-002 |
| OEM-FR-002 | 3 km/h 이상 첫 평가주기부터 LOCK | SWR-003 ① |
| OEM-FR-003 | 10초 이하 재입력 시 override 상태와 이유코드 | SWR-006 ① |
| OEM-FR-004 | 상태조회에 좌·우 출력, state, 입력유효성, 이유코드 | SWR-014 |
| OEM-FR-005 | 각 입력 단독 주입 시 다음 주기 RELEASE, 입력별 이유코드 | SWR-017 ① |
| OEM-FR-006 | 한쪽 ISOFIX만 TRUE면 해당 출력만 LOCK | SWR-018 ① |
| OEM-FR-007 | 첫 평가주기 RELEASE, OFF, ignition_off | SWR-020 ① |
| OEM-NFR-001 | 고정 시계 1,000회 재생 해시 동일 | SWR-016 |
| OEM-NFR-002 | 101건 후 최신 100건, 허용 필드만, 재기동 후 없음 | SWR-011, SWR-012 ①③ |
