# TRACE SWR ↔ 아키텍처 추적성

| 항목 | 내용 |
|---|---|
| 문서 ID | TRACE-SWA-001 |
| 범위 | SWR(BL-SWR-1.0) ↔ 아키텍처 컴포넌트·결정(BL-SWA-1.0) |
| 상위 추적 | `../01_requirements/TRACE_추적성.md` (OEM ↔ SWR) |

## 1. 순방향: SWR → 컴포넌트

| SWR | ASIL | 할당 컴포넌트 | 아키텍처 결정 | SWA 위치 |
|---|---|---|---|---|
| SWR-001 | QM | `decision`(8순위), `controller`(명령 큐) | AD-01 | 6.1, 6.2 |
| SWR-002 | QM | `decision`(8순위), `controller` | AD-01 | 6.1, 6.2 |
| SWR-003 | QM | `decision`(7순위) | AD-01 | 6.2 |
| SWR-004 | QM | `decision` | AD-01 | 6.2 |
| SWR-005 | B | `decision`(3순위, `suppressed_unlocks` 생성) | AD-01, AD-02 | 6.2, 10 |
| SWR-006 | QM | `override`, `controller`(주석 적용) | AD-02, AD-03 | 6.1, 6.3, 10 |
| SWR-007 | B | `decision`(1순위, `crash_latched`) | AD-01 | 6.2, 6.3, 7 |
| SWR-008 | B | `decision` | AD-01 | 6.2 |
| SWR-009 | B | `decision`(도어별 판정) | AD-01 | 6.2 |
| SWR-010 | QM | `event_store` | AD-06 | 4.1 |
| SWR-011 | QM | `event_store`, `model.Event` | AD-04, AD-06 | 4.3 |
| SWR-012 | QM | `event_store` | AD-06 | 4.1, 7 |
| SWR-013 | B | `validation`, `freshness`, `controller`, `decision`(출력 유지) | AD-03, AD-05 | 5, 6.1, 7, 8 |
| SWR-014 | QM | `controller.status()`, `web`(`GET /api/status`) | AD-07 | 5 |
| SWR-015 | QM | `web` | AD-07 | 5, 8 |
| SWR-016 | QM | `decision`(순수 함수), `clock`, `replay` | AD-01, AD-03 | 2 |
| SWR-017 | QM | `decision`(5순위) | AD-01 | 6.2 |
| SWR-018 | QM | `decision`(6순위) | AD-01 | 6.2 |
| SWR-020 | QM | `decision`(4순위) | AD-01 | 6.2, 6.3 |
| SWR-021 | B | `decision`(2순위) | AD-01 | 6.2, 6.3 |
| SWR-022 | B | `decision` | AD-01 | 6.2 |
| SWR-023 | B | `controller.step`, `clock`, `web`(50 ms 루프) | AD-03, AD-08 | 6.1, 7 |
| SWR-024 | QM | `controller`(초기 상태), `decision`(NO_DATA 유지) | AD-01 | 6.3 |

SWR 23건 모두 1개 이상의 컴포넌트에 할당됐다(23/23).

**ASIL 할당 일관성**: ASIL B SWR(005, 007, 008, 009, 013, 021, 022, 023)은 모두 ASIL B 컴포넌트에 할당됐다. QM 컴포넌트(`override`, `event_store`, `replay`, `web`)에 할당된 SWR은 모두 QM이다. 단, SWR-023의 50 ms 루프 구동은 `web`(QM)에서 하지만, 주기 판정 자체(`step`)는 ASIL B `controller`가 수행하며 시험에서는 `web` 없이 검증한다.

## 2. 역방향: 컴포넌트 → SWR

| 컴포넌트 | ASIL | SWR |
|---|---|---|
| `model` | B | 전체 (SWIF 데이터 정의) |
| `validation` | B | SWR-013 |
| `freshness` | B | SWR-013 |
| `decision` | B | SWR-001~005, 007~009, 013, 016~018, 020~022, 024 |
| `controller` | B | SWR-001, 002, 006, 013, 014, 023, 024 |
| `clock` | B | SWR-016, SWR-023 |
| `override` | QM | SWR-006 |
| `event_store` | QM | SWR-010, SWR-011, SWR-012 |
| `replay` | QM | SWR-016 |
| `web` | QM | SWR-014, SWR-015, SWR-023 |

상위 SWR이 없는 컴포넌트는 없다(10/10).
