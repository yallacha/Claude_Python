# SBOM 소프트웨어 구성

| 항목 | 내용 |
|---|---|
| 문서 ID | SBOM-001 |
| 대상 | 전자식 차일드락 제어 SW `childlock` 0.1.0 |
| 베이스라인 | BL-CODE-UT-1.0 |
| 기준 파일 | `requirements.txt`(제품), `requirements-dev.txt`(개발·시험) |
| 확인 환경 | Windows 11, Python 3.12.10 |

## 1. 자체 개발 구성 요소

| 구성 요소 | 경로 | ASIL | 외부 의존 |
|---|---|---|---|
| model, validation, freshness, decision, clock, controller | `src/childlock/*.py` | B | 표준 라이브러리만 |
| override, event_store, replay | `src/childlock/*.py` | QM | 표준 라이브러리만 |
| web (Web 시뮬레이터) | `src/childlock/web/` | QM | FastAPI, uvicorn |
| 주석률 측정 도구 | `tools/comment_ratio.py` | — (개발 도구) | 표준 라이브러리만 |

ASIL B 모듈이 외부 패키지를 로드하지 않는 것은 아키텍처 시험(`tests/unit/test_architecture.py`)으로 확인한다.

## 2. 제품 의존성 (Web 시뮬레이터, 전이 의존성 포함)

| 패키지 | 버전 | 라이선스 | 직접/전이 |
|---|---|---|---|
| fastapi | 0.165.0 | MIT | 직접 |
| uvicorn | 0.54.0 | BSD-3-Clause | 직접 |
| starlette | 1.10.0 | BSD-3-Clause | 전이 (fastapi) |
| pydantic | 2.14.4 | MIT | 전이 (fastapi) |
| pydantic_core | 2.50.5 | MIT | 전이 (pydantic) |
| annotated-types | 0.8.0 | MIT | 전이 (pydantic) |
| typing-inspection | 0.4.5 | MIT | 전이 (pydantic) |
| typing_extensions | 4.16.0 | PSF-2.0 | 전이 |
| annotated-doc | 0.0.7 | MIT | 전이 (fastapi) |
| anyio | 4.16.0 | MIT | 전이 (starlette) |
| idna | 3.20 | BSD-3-Clause | 전이 (anyio) |
| opentelemetry-api | 1.45.2 | Apache-2.0 | 전이 |
| click | 8.5.1 | BSD-3-Clause | 전이 (uvicorn) |
| h11 | 0.16.0 | MIT | 전이 (uvicorn) |

모두 허용형(permissive) 라이선스다. 복사 의무가 있는 라이선스(GPL 계열)는 없다.

## 3. 개발·시험 의존성 (제품에 포함되지 않음)

| 패키지 | 버전 | 용도 |
|---|---|---|
| pytest | 9.2.0 | 단위 시험 |
| pytest-cov, coverage | 7.1.0, 7.17.5 | 브랜치 커버리지 |
| ruff | 0.17.6 | 정적 분석·포맷 |
| lizard | 1.26.1 | 함수 길이·순환 복잡도 |
| httpx | 0.28.1 | FastAPI 시험 클라이언트 |
| Microsoft PICT | 3.7.4 | 시스템 시험 조합 도출(7단계) |

## 4. 알려진 사항

- `httpx`를 Starlette 시험 클라이언트와 함께 쓰면 `StarletteDeprecationWarning`(httpx2 권장)이 출력된다. 시험 결과에는 영향이 없다. `httpx2`로 교체하는 작업은 이 환경의 권한 정책으로 수행하지 못해 미결로 둔다(UTR 5장).
