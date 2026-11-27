"""!
@brief SW 시스템 시험 자동 실행기 (SWE.6, PC/SIL).
@details 사양서 입력(docs/06_system_test/stc_testcases.json)의 실행 벡터를 케이스마다
    새 시스템(고정 시계)으로 재생하고 기대 상태를 확인한다.
    벡터가 없는 케이스는 test_system_special.py가 케이스 ID별로 실행한다.
"""

import pytest
from vector_runner import SPEC, load_cases, run_vector

CASES = [case for case in load_cases() if case.get("vector")]


def test_specification_has_executable_cases():
    """!@brief 사양서 입력 파일이 있고 자동 실행 가능한 케이스가 있다."""
    assert SPEC.exists()
    assert CASES


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_system_case(case):
    """!@brief 시스템 시험 케이스 1건을 PC/SIL에서 실행하고 단계별 기대 상태를 확인한다."""
    mismatches = []
    for index, expect, actual in run_vector(case["vector"]):
        for field, value in expect.items():
            if actual.get(field) != value:
                mismatches.append(
                    f"step {index} {field}: 기대 {value!r}, 실제 {actual.get(field)!r}"
                )

    assert not mismatches, f"{case['id']} ({', '.join(case['basis_ids'])}): " + "; ".join(
        mismatches
    )
