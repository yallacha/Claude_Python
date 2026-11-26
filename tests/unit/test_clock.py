"""!
@brief childlock.clock 단위 시험 (SWD 8장, AD-03).
"""

import pytest

from childlock.clock import ManualClock, MonotonicClock
from childlock.model import to_ms


def test_manual_clock_starts_at_given_ms_and_advances_exactly():
    """!@brief 수동 시계는 정수 ms로 누적해 200번 50 ms 전진하면 정확히 10.0 s다."""
    clock = ManualClock(start_ms=0)
    for _ in range(200):
        clock.advance_ms(50)

    assert clock.now() == 10.0


def test_manual_clock_start_offset():
    """!@brief 시작 시각을 ms로 줄 수 있다."""
    assert ManualClock(start_ms=1500).now() == 1.5


def test_manual_clock_rejects_going_backwards():
    """!@brief 시간을 되돌리는 전진은 거절한다(시험 벡터 오류 방지)."""
    clock = ManualClock()

    with pytest.raises(ValueError):
        clock.advance_ms(-1)
    assert clock.now() == 0.0


def test_monotonic_clock_starts_near_zero_and_never_decreases():
    """!@brief 실제 시계는 생성 시각을 0으로 하고 감소하지 않는다."""
    clock = MonotonicClock()
    first = clock.now()
    second = clock.now()

    assert 0 <= to_ms(first) < 1000
    assert second >= first
