# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code에게 주는 안내다.

## 프로젝트

- AI(Claude)를 이용해 Python 코드를 작성하는 저장소다.
- 원격 저장소: https://github.com/yallacha/Claude_Python (비공개, 기본 브랜치 `main`)
- 현재 과제: OEM-SWR-001 기반 전자식 차일드락 제어 SW (`src/childlock/`). 개발 계획과 결정 사항은 `docs/00_plan/개발계획.md`에 있다. 원본 사양서는 `OEM/`에 있고 저장소에 커밋하지 않는다.
- 단계(개발 계획 1장)가 끝날 때마다 사용자에게 보고하고 다음 단계로 넘어간다.

## 개발 환경

- 개발 언어는 Python 3.12를 사용한다.
- 단위 테스트 프레임워크는 pytest, 커버리지 측정은 pytest-cov를 사용한다.
- 정적 분석과 포매팅은 Ruff를 사용한다.
- 함수 길이와 순환 복잡도 측정은 lizard를 사용한다.
- 설치 경로 (이 PC에서 PATH에 잡히지 않을 수 있으므로 필요하면 전체 경로로 실행한다)
  - Python: `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`
  - Git: `C:\Program Files\Git\cmd\git.exe`
  - PICT: `%LOCALAPPDATA%\pict\pict.exe`

## 개발 절차

- 개발은 A-SPICE 절차를 기본으로 따른다. 단계와 산출물 위치는 다음과 같다.

  | 단계 | A-SPICE | 산출물 위치 |
  |---|---|---|
  | 요구사항 분석 | SWE.1 | `docs/01_requirements/` |
  | 아키텍처 설계 | SWE.2 | `docs/02_architecture/` |
  | 상세 설계 | SWE.3 | `docs/03_detailed_design/` |
  | 구현 | SWE.3 | `src/` |
  | 단위 테스트 | SWE.4 | `tests/unit/` |
  | 통합 테스트 | SWE.5 | `tests/integration/`, `docs/05_integration_test/` |
  | 시스템 테스트 | SWE.6 | `docs/06_system_test/` |

- 앞 단계 산출물이 없으면 다음 단계를 시작하지 않고 사용자에게 확인한다.
- 각 단계 산출물은 앞 단계 산출물 ID로 양방향 추적이 되도록 작성한다.
- 구현은 TDD로 한다. 코드를 쓰기 전에 `test-driven-development` 스킬(`.claude/skills/test-driven-development`)을 불러와 RED → GREEN → REFACTOR 절차를 따른다. 서브 에이전트에게 구현을 맡길 때도 이 스킬을 쓰라고 지시한다.
- 시스템 테스트 케이스는 `system-test-case` 서브 에이전트(`sw-system-test-cases` 스킬)로 만든다.

## 소스코드 품질

아래 기준을 모두 만족해야 PR을 병합할 수 있다. 측정 명령은 Jenkins 품질 검사와 같다.

| 기준 | 목표 | 측정 방법 |
|---|---|---|
| 단위 테스트 성공률 | 100% (실패 0건) | `python -m pytest` |
| 브랜치 커버리지 | **반드시** 100% (`src`, `tools`) | `python -m pytest --cov --cov-branch --cov-fail-under=100` |
| 주석률 | 20% 이상 (파일 단위) | `python -m tools.comment_ratio src tools --min 20`. (주석 줄 + docstring 줄) ÷ (코드 줄 + 주석 줄 + docstring 줄), 빈 줄 제외, 코드 뒤에 붙은 주석은 코드 줄 |
| 함수 길이 | 순수 코드 50줄 이하 | `python -m lizard src tools -w -Tnloc=50 -Tcyclomatic_complexity=10` (NLOC: 빈 줄·주석 제외) |
| 순환 복잡도 | 함수당 **반드시** 10 이하 | 위 lizard 명령(CCN), Ruff `C901`(max-complexity 10) |
| 정적 분석 | 경고 0건 | `python -m ruff check .`, `python -m ruff format --check .` |
| 명명 규칙 | Google Python Style Guide | Ruff `N`(pep8-naming) 규칙 |

- 도구 버전은 `requirements-dev.txt`, 설정은 `pyproject.toml`에 있다. `.claude/` 아래 스킬 보조 스크립트는 제품 코드가 아니므로 검사 대상에서 제외한다.

- 브랜치 커버리지 100%를 달성하지 못하면 달성할 때까지 테스트를 보강한다. 커버리지를 맞추려고 의미 없는 테스트를 만들지 않는다.
- 커버리지 측정 제외(`# pragma: no cover`)는 진입점(`if __name__ == "__main__":`)이나 실제로 만들 수 없는 방어 코드에만, 같은 줄에 사유를 적은 경우에 허용한다.
- `skip`·`xfail`은 사유를 적은 경우에만 허용하고, PR 설명에 목록을 남긴다.
- 주석은 Doxygen 스타일로 쓴다. 모듈·클래스·함수 docstring에 `@brief`, `@param`, `@return`, `@throws`를 사용한다.

## Git 브랜치 규칙 (GitHub Flow)

- `main`은 항상 품질 기준을 만족하는 상태로 유지한다. `main`에 직접 커밋·push하지 않는다.
- 모든 작업은 `main`에서 분기한 작업 브랜치에서 한다.
  - 이름: `<유형>/<이슈번호>-<짧은-설명>` (이슈가 없으면 번호 생략). 예: `feature/12-door-lock`, `fix/login-timeout`
  - 유형: `feature`(기능), `fix`(버그 수정), `refactor`(리팩터링), `test`(테스트), `docs`(문서), `chore`(빌드·설정)
- 커밋 메시지: `<유형>: <요약>` 형식으로 한글로 쓴다. 예: `feat: 도어 잠금 차속 조건 추가`
  - 유형: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
- 작업이 끝나면 PR을 만든다. PR 설명에는 변경 내용, 관련 요구사항 ID, 품질 기준 측정 결과를 적는다.
- 병합 조건: Jenkins 품질 검사 통과. 리뷰 승인은 필수가 아니다.
- 병합 방식: Squash merge. 병합 후 작업 브랜치를 삭제한다.
- 비공개 저장소라 GitHub 브랜치 보호로 병합을 강제할 수 없다. Claude는 병합 전에 Jenkins 결과와 품질 기준 통과를 직접 확인하고, 미달이면 병합하지 않는다.

## CI (Jenkins)

- Jenkins는 이 PC(172.16.7.124, http://localhost/)에서 서비스로 실행 중이다. 홈: `C:\ProgramData\Jenkins\.jenkins`
- 사설 IP라 GitHub webhook이 닿지 않는다. 변경은 SCM 폴링으로 감지한다.
- 품질 검사 job: `Claude_Python-quality` (Multibranch Pipeline). 5분마다 원격 브랜치를 검색해 저장소의 `Jenkinsfile`로 브랜치별 품질 검사를 실행한다.
- Windows batch 단계는 콘솔 한글 깨짐을 막기 위해 맨 앞에 `chcp 65001 > nul`과 `set PYTHONUTF8=1`을 넣는다.

## Claude Code 설정

- `.claude/settings.json`의 hook이 프롬프트와 답변을 `prompt.md`에 자동 기록한다. `prompt.md`는 직접 수정하지 않고, 저장소에 올리지 않는다(`.gitignore`).
- 비공개 저장소라 GitHub 인증은 Git Credential Manager를 쓴다. Claude Code 안에서는 로그인 창을 띄울 수 없으므로 인증이 필요하면 사용자에게 일반 터미널에서 처리해 달라고 요청한다.

## 기타

- CLAUDE.md, 문서, 주석, docstring, 커밋 메시지, PR 설명은 한글로 쓴다. 코드 식별자(변수, 함수, 클래스 이름)는 영어로 쓴다.
- 의미 없는 사과를 하지 않는다.
- 반말을 하지 않는다.
