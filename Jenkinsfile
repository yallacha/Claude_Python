// 품질 검사 파이프라인 (CLAUDE.md "소스코드 품질" 기준)
// 모든 단계가 통과해야 PR을 병합할 수 있다.
pipeline {
    agent any
    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }
    environment {
        PYTHON = 'C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python312\\python.exe'
        PYTHONUTF8 = '1'
        VENV_PY = '.venv\\Scripts\\python.exe'
    }
    stages {
        stage('환경 준비') {
            steps {
                bat '''
chcp 65001 > nul
"%PYTHON%" -m venv .venv
"%VENV_PY%" -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt
'''
            }
        }
        stage('정적 분석 (Ruff)') {
            steps {
                bat '''
chcp 65001 > nul
"%VENV_PY%" -m ruff check .
"%VENV_PY%" -m ruff format --check .
'''
            }
        }
        stage('단위 테스트 + 브랜치 커버리지 100%') {
            steps {
                bat '''
chcp 65001 > nul
"%VENV_PY%" -m pytest --cov --cov-branch --cov-fail-under=100 --junitxml=reports\\junit.xml
'''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                }
            }
        }
        stage('함수 길이 50 / 순환 복잡도 10 (lizard)') {
            steps {
                bat '''
chcp 65001 > nul
"%VENV_PY%" -m lizard src tools -w -Tnloc=50 -Tcyclomatic_complexity=10
'''
            }
        }
        stage('주석률 20%') {
            steps {
                bat '''
chcp 65001 > nul
"%VENV_PY%" -m tools.comment_ratio src tools --min 20
'''
            }
        }
    }
}
