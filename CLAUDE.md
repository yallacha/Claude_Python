# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code에게 주는 안내입니다.

## 프로젝트

- AI(Claude)를 이용해 Python 코드를 작성하는 저장소입니다.
- 원격 저장소: https://github.com/yallacha/Claude_Python (비공개, 기본 브랜치 `main`)
- 아직 Python 코드는 없습니다. 코드가 생기면 실행·테스트 방법을 이 파일에 추가합니다.

## 소통

- 사용자와는 한국어로 대화합니다.
- 코드 주석과 커밋 메시지 언어는 사용자가 따로 정하지 않았다면 한국어로 씁니다.

## 환경

- Windows 11, PowerShell 5.1.
- Python 3.12는 `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`에 있습니다(openpyxl 설치됨). `python`이 Microsoft Store 바로가기로 잡히면 전체 경로로 실행합니다.
- Microsoft PICT는 `%LOCALAPPDATA%\pict\pict.exe`에 있습니다(v3.7.4).
- 프로젝트 스킬: `.claude/skills/sw-system-test-cases` — SW 요구사항에서 A-SPICE SWE.6 / ISO 26262-6 기준 시스템 테스트 케이스 엑셀을 만듭니다.
- 프로젝트 서브 에이전트: `.claude/agents/system-test-case.md` — SW 요구사항 분석이 끝난 뒤 위 스킬로 결함 발견 중심의 시스템 테스트 케이스를 만듭니다(Sonnet 5.5).
- Git은 `C:\Program Files\Git\cmd\git.exe`에 있습니다. `git`이 PATH에 없으면 전체 경로로 실행합니다.
- 비공개 저장소라 GitHub 인증은 Git Credential Manager에 저장된 자격 증명을 씁니다. Claude Code 안에서는 로그인 창을 띄울 수 없으므로, 인증이 필요하면 사용자에게 일반 터미널에서 처리해 달라고 요청합니다.

## 프롬프트 기록 (`prompt.md`)

- `.claude/settings.json`의 hook이 `.claude/hooks/log-prompt.ps1`을 실행해, 사용자 프롬프트(`UserPromptSubmit`)와 Claude의 답변(`Stop`)을 `prompt.md`에 시각과 함께 자동으로 덧붙입니다.
- `prompt.md`는 hook이 관리합니다. 직접 수정하거나 지우지 않습니다.
- hook 경로가 `D:/Repo/Claude_Python`으로 고정되어 있습니다. 저장소 위치를 옮기면 `.claude/settings.json`의 경로도 함께 바꿔야 합니다.

## Jenkins

- 로컬 Jenkins(http://localhost/)에 `Claude_Python` job이 있습니다. `main` 브랜치를 받아 Windows batch 명령을 실행하며, 매시 35분에 자동 실행됩니다.
- Jenkins 홈: `C:\ProgramData\Jenkins\.jenkins` (빌드 로그: `jobs\Claude_Python\builds\<번호>\log`)
- Windows batch 출력은 CP949라서 Jenkins 콘솔에서 한글이 깨집니다. batch 명령 맨 앞에 `chcp 65001 > nul`을, Python을 실행한다면 `set PYTHONUTF8=1`도 넣습니다.

## 구현 방식: TDD

- 기능 구현, 버그 수정, 리팩터링, 동작 변경을 할 때는 코드를 쓰기 전에 반드시 `test-driven-development` 스킬(`.claude/skills/test-driven-development`)을 불러와 그 절차를 따릅니다.
  - RED: 실패하는 테스트를 먼저 쓰고, 실행해서 기대한 이유로 실패하는지 확인합니다.
  - GREEN: 테스트를 통과하는 최소한의 코드를 씁니다.
  - REFACTOR: 테스트가 통과하는 상태를 유지하며 정리합니다.
- 서브 에이전트에게 구현을 맡길 때도 프롬프트에 이 스킬을 쓰라고 적습니다.
- 테스트 도구는 pytest입니다. 실행: `python -m pytest` (`python`이 PATH에 없으면 `%LOCALAPPDATA%\Programs\Python\Python312\python.exe -m pytest`). 완료 전에는 작성한 테스트 파일만이 아니라 전체 테스트를 실행합니다.
- 예외(일회성 프로토타입, 생성된 코드, 설정 파일)는 사용자에게 먼저 묻습니다.

## Python 코드 작성 규칙

- 소스 파일은 UTF-8로 저장합니다.
- 한글을 출력하는 스크립트는 Windows 콘솔과 Jenkins에서 모두 깨지지 않도록 UTF-8 출력을 전제로 작성합니다.
