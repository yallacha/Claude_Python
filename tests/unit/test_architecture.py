"""!
@brief 아키텍처 의존 규칙 시험 (SAP 3장, SWA 4.2, AD-01·02·03).
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "childlock"
ASIL_B = ("model", "validation", "freshness", "decision", "controller", "clock")
QM = ("override", "event_store", "replay", "web")
PURE = ("validation", "freshness", "decision")
PURE_ALLOWED = {
    "childlock.model",
    "__future__",
    "collections.abc",
    "dataclasses",
    "enum",
    "math",
    "typing",
}
FORBIDDEN_NAMES = {"time", "datetime", "random", "open", "os"}


def imported_modules(source: str) -> set[str]:
    """!@brief 소스가 import하는 모듈 이름(점 경로)을 모은다."""
    modules = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def used_names(source: str) -> set[str]:
    """!@brief 소스에서 쓰는 이름과 import 별칭을 모은다."""
    tree = ast.parse(source)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    return names | {m.split(".")[0] for m in imported_modules(source)}


def module_source(name: str) -> str:
    """!@brief childlock 모듈 소스를 읽는다."""
    return (SRC / f"{name}.py").read_text(encoding="utf-8")


def test_checker_finds_qm_import_and_forbidden_api_in_sample():
    """!@brief 검사 함수가 위반(QM import, time 사용, open 호출)을 실제로 찾는다."""
    sample = "import time\nfrom childlock.event_store import EventStore\nopen('x')\n"

    assert "childlock.event_store" in imported_modules(sample)
    assert {"time", "open"} <= used_names(sample)


@pytest.mark.parametrize("name", ASIL_B)
def test_asil_b_modules_do_not_import_qm_modules(name):
    """!@brief ASIL B 모듈은 QM 모듈을 import하지 않는다 (SWA 4.2 규칙 1·2)."""
    qm = {f"childlock.{m}" for m in QM}
    imports = imported_modules(module_source(name))

    assert not {i for i in imports if any(i == q or i.startswith(q + ".") for q in qm)}


@pytest.mark.parametrize("name", PURE)
def test_pure_modules_import_only_model_and_allowed_stdlib(name):
    """!@brief 판정 순수 모듈은 model과 허용 표준 라이브러리만 import한다 (SWA 4.2 규칙 3)."""
    assert imported_modules(module_source(name)) <= PURE_ALLOWED


@pytest.mark.parametrize("name", PURE)
def test_pure_modules_do_not_use_clock_random_or_io(name):
    """!@brief 판정 순수 모듈은 시계·난수·파일·OS API를 쓰지 않는다 (AD-01, AD-03)."""
    assert not used_names(module_source(name)) & FORBIDDEN_NAMES


def test_asil_b_core_runtime_does_not_load_web_framework():
    """!@brief ASIL B 모듈만 import해도 FastAPI가 로드되지 않는다 (SWA 9장)."""
    code = "import sys, childlock.controller, childlock.clock; print('fastapi' in sys.modules)"

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env={
            "PYTHONPATH": str(SRC.parent),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        },
    )

    assert result.stdout.strip() == "False"
