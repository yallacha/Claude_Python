"""!
@brief childlock.freshness 단위 시험 (SWD 4장, SWR-013 ③).
"""

import pytest

from childlock.freshness import is_stale


@pytest.mark.parametrize(
    ("now_s", "last_s", "expected"),
    [
        (1.200, 1.000, False),  # 정확히 200 ms: 초과가 아니므로 fresh
        (1.201, 1.000, True),  # 201 ms: 초과
        (1.000, 1.000, False),  # 방금 받은 입력
    ],
)
def test_stale_only_when_age_exceeds_200_ms(now_s, last_s, expected):
    """!@brief 마지막 유효 입력 후 200 ms 초과일 때만 stale이다."""
    assert is_stale(now_s, last_s) is expected


def test_accumulated_float_time_at_exactly_200_ms_is_not_stale():
    """!@brief 0.05 s를 4번 더한 시각(부동소수 오차 포함)도 200 ms로 판정한다 (DD-C02)."""
    now = 0.0
    for _ in range(4):
        now += 0.05

    assert is_stale(now + 0.1, 0.1) is False


def test_no_valid_input_yet_is_not_stale():
    """!@brief 유효 입력을 받은 적 없으면 stale이 아니다(NO_DATA는 controller가 처리)."""
    assert is_stale(5.0, None) is False
