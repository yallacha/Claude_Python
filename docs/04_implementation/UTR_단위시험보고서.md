# UTR 구현·단위 시험 보고서

| 항목 | 내용 |
|---|---|
| 문서 ID | UTR-001 |
| 대상 | `src/childlock/` (BL-SWD-1.0 구현), `tools/` |
| 베이스라인 | BL-CODE-UT-1.0 |
| 방법 | TDD(`test-driven-development` 스킬): 시험 작성 → 실패 확인 → 최소 구현 → 통과 확인 |
| 시험 위치 | `tests/unit/` |

## 1. 결과 요약

| 기준 (CLAUDE.md) | 목표 | 결과 | 판정 |
|---|---|---|---|
| 단위 시험 성공률 | 100% | 216건 통과, 실패 0 | 충족 |
| 브랜치 커버리지 | 100% | 100.00% (문장 657, 분기 140) | 충족 |
| 함수 길이 | NLOC ≤ 50 | lizard 경고 0 | 충족 |
| 순환 복잡도 | CCN ≤ 10 | lizard 경고 0, Ruff C901 위반 0 | 충족 |
| 주석률 | 파일당 ≥ 20% | 미달 0 (최저 `model.py` 20.9%) | 충족 |
| 정적 분석 | 위반 0 | Ruff check·format 위반 0 | 충족 |
| 아키텍처 의존 규칙 | 위반 0 | 아키텍처 시험 14건 통과 | 충족 |
| skip / xfail | 사유 기록 | 없음 | — |

측정 명령은 CLAUDE.md "소스코드 품질" 표와 같고, Jenkins `Claude_Python-quality`가 같은 명령으로 재확인한다.

## 2. 단위별 시험 (SWD → 시험 추적)

| SWD 단위 | 시험 파일 | 시험 수 | 주요 검증 내용 |
|---|---|---|---|
| `model` (2장) | `test_model.py` | 8 | 정수 ms 변환(부동소수 누적), 우선순위 순서, 도어 출력 선택, 초기 상태, 불변성 |
| `validation` (3장) | `test_validation.py` | 55 | 필드별 누락·형식·범위·열거 오류, 경계값(0.0/300.0, −0.1/300.1), NaN·inf, bool-숫자 혼동, 명령 검증 |
| `freshness` (4장) | `test_freshness.py` | 5 | 200 ms(fresh)/201 ms(stale) 경계, 누적 오차, 입력 없음 |
| `decision` (5장) | `test_decision.py` | 69 | 결정 테이블 각 행, 인접 우선순위 7쌍, 명령 효과(CR-01), 결합 동률, PENDING, 4경로×3대상 명령, latch 조건 |
| `clock` (8장) | `test_clock.py` | 4 | 정수 ms 누적, 역행 거부, 단조 증가 |
| `override` (6장) | `test_override.py` | 9 | 10.000 s(성립)/10.001 s(불성립), 누적 오차, 도어 구분, 해제 시 초기화, 상위 state 보존, 출력 필드 없음 |
| `event_store` (7장) | `test_event_store.py` | 5 | ID 증가, 100/101건 경계, 허용 필드 8개, 재기동 |
| `controller` (9장) | `test_controller.py` | 17 | 초기 상태, 유효성 결정 표, 200/250 ms freshness, 명령 1회 소비, 무효 명령, override 연동, QM 예외·적대적 주석에도 출력 불변 |
| `replay` (10장) | `test_replay.py` | 5 | 순서 재생, 반복 해시 동일, 입력 변경 시 해시 변경, 벡터 파일 |
| `web` (11장) | `test_web.py` | 12 | 상태 7필드, 입력→평가→조회 일치, 이력 순서, JSON 오류 422, 직렬화 실패 500, 화면 표시 영역, 수동 평가 409, 50 ms 루프, 수신 시각 stamp, 진입점 |
| 아키텍처 규칙 (SAP 3장) | `test_architecture.py` | 14 | ASIL B→QM import 금지, 순수 모듈 의존 제한, 금지 API, 코어의 FastAPI 미로드 |
| `tools/comment_ratio` | `tools/test_comment_ratio.py` | 13 | 줄 분류, docstring 판별, 주석률, 명령줄 동작 (0단계) |

SWD 단위 10/10에 단위 시험이 있다.

## 3. 시험의 결함 검출력 확인 (돌연변이 점검)

시험이 실제 결함을 잡는지 일부러 코드를 망가뜨려 확인했다.

| 주입한 결함 | 결과 |
|---|---|
| `decision.py`에 `import time`, QM 모듈 import 추가 | 아키텍처 시험 3건 실패 |
| `web` 명령 API의 JSON 오류 처리 분기 삭제 | `test_malformed_command_json_is_rejected_with_422` 실패 |
| `comment_ratio`의 docstring 문자열 여부 검사 제거 (0단계) | 1건 실패 |

## 4. 구현 중 설계 대비 변경

| 항목 | 내용 | 근거 |
|---|---|---|
| `create_app(controller, events, clock, run_loop)` | SWD의 `create_app(controller, run_loop)`에서 이력 저장소와 시계를 인자로 추가 | 이력 조회가 controller 내부 속성에 의존하지 않게 함. 화면 입력에 서버 수신 시각을 채우는 `?stamp=true`에 시계 필요(브라우저는 서버 시계를 모름) |
| `POST /api/snapshot?stamp=true` | 시뮬레이터 화면 편의 기능 추가 | 위와 같음. 시각을 채우는 것 외 입력 내용은 바꾸지 않음 |
| 열거형 `StrEnum` | `(str, Enum)` 대신 Python 3.11+ `StrEnum` | Ruff UP042. 값·동작 같음 |

위 변경은 QM `web` 내부와 표기 방식에 한정되며 SWR·SWA 인터페이스(HTTP 경로, 데이터)를 바꾸지 않는다.

## 5. 미결 사항

| ID | 내용 | 영향 | 처리 |
|---|---|---|---|
| UT-O-01 | 시험 실행 시 `StarletteDeprecationWarning`(httpx 대신 httpx2 권장) 경고 1건 | 시험 결과 영향 없음 | httpx2 교체를 시도했으나 이 환경의 권한 정책으로 거부됨. 사용자 판단 대기 |

## 6. 실행 확인

`python -m childlock.web`으로 시뮬레이터를 실행해, 100 ms마다 입력을 보내는 동안 `VALID`/`NORMAL`(차속 10 km/h → 자동 잠금), 입력을 멈추고 350 ms 뒤 `STALE`/`DEGRADED`가 되는 것을 확인했다.
