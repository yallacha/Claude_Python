# SAP 정적 분석 계획

| 항목 | 내용 |
|---|---|
| 문서 ID | SAP-001 |
| 대상 | `src/childlock/`, `tools/` (제품 코드와 품질 도구) |
| 베이스라인 | BL-SWA-1.0 (G2 승인 대기) |
| 관련 문서 | `../../CLAUDE.md` 소스코드 품질, `SWA_SW아키텍처명세.md` |

## 1. 목적

코드 품질 기준(CLAUDE.md)과 아키텍처 의존 규칙(SWA 4.2)을 자동으로 검사해, 기준 미달 코드가 `main`에 병합되지 않게 한다.

## 2. 검사 항목과 기준

| 항목 | 도구 / 설정 | 기준 | 실패 시 |
|---|---|---|---|
| 코딩 규칙·잠재 결함 | Ruff `E`, `W`, `F`, `B`, `UP` | 위반 0건 | 수정 후 재검사. 규칙 비활성화(`noqa`)는 사유를 같은 줄에 적은 경우만 허용 |
| import 정렬 | Ruff `I` | 위반 0건 | `ruff check --fix` |
| 명명 규칙 (Google Python Style Guide) | Ruff `N` | 위반 0건 | 수정 |
| 포맷 | `ruff format --check` | 차이 0건 | `ruff format` |
| 순환 복잡도 | Ruff `C901`(10), lizard CCN | 함수당 10 이하 | 함수 분리 |
| 함수 길이 | lizard NLOC | 함수당 50 이하 | 함수 분리 |
| 주석률 | `tools.comment_ratio` | 파일당 20% 이상 | Doxygen docstring 보강 |
| 아키텍처 의존 규칙 | 아키텍처 시험(`tests/unit/test_architecture.py`, `ast`로 import 분석) | ASIL B 모듈이 QM 모듈을 import하지 않음. `decision`·`validation`·`freshness`는 `model`과 표준 라이브러리만 import | 의존 제거 |
| 금지 API (판정 코어) | 아키텍처 시험 | ASIL B 판정 모듈(`decision`, `validation`, `freshness`)에서 `time`, `datetime`, `random`, `open`, `os` 사용 금지 | 시계 주입(AD-03)으로 대체 |

## 3. 아키텍처 시험 상세

정적 분석 도구만으로는 프로젝트 고유의 의존 규칙을 검사할 수 없으므로 pytest 시험으로 만든다. 단위 시험과 함께 실행되므로 Jenkins 품질 검사에 자동 포함된다.

| 시험 | 검사 내용 | 근거 |
|---|---|---|
| ASIL B → QM import 금지 | `model`, `validation`, `freshness`, `decision`, `controller`, `clock`의 import 대상에 `override`, `event_store`, `replay`, `web`이 없음 | SWA 4.2 규칙 1, 2 |
| 순수 판정 모듈 의존 제한 | `decision`, `validation`, `freshness`의 import 대상이 `childlock.model`과 표준 라이브러리 중 허용 목록뿐 | SWA 4.2 규칙 3 |
| 금지 API | 위 세 모듈에 금지 이름(`time`, `datetime`, `random`, `open`, `os`) 사용 없음 | AD-01, AD-03 |

## 4. 실행 시점

| 시점 | 방법 |
|---|---|
| 구현 중 (TDD 각 사이클 후) | `python -m ruff check .`, `python -m pytest` |
| PR 생성 전 | CLAUDE.md 품질 기준 표의 명령 전부 |
| PR 브랜치 push 후 | Jenkins `Claude_Python-quality`가 전체 실행. 실패하면 병합하지 않음 |

## 5. 결과 기록

- PR 설명에 품질 기준 측정 결과 표를 남긴다.
- Jenkins 빌드 결과(SUCCESS/FAILURE)를 PR 댓글로 남긴다.
- G3 증거(BL-CODE-UT-1.0)로 마지막 Jenkins 빌드 로그와 커버리지 보고서를 보관한다.
