"""!
@brief 시계 (ASIL B, SWD 8장, AD-03).
@details 판정 코드는 시간을 이 인터페이스로만 읽는다.
    시험은 ManualClock, Web은 MonotonicClock을 쓴다.
"""

import time
from typing import Protocol


class Clock(Protocol):
    """!@brief 시계 인터페이스."""

    def now(self) -> float:
        """!@brief 현재 시각(초)을 돌려준다."""
        ...  # pragma: no cover - 프로토콜 선언, 실행되지 않음


class ManualClock:
    """!@brief 시험용 수동 시계. 내부를 정수 ms로 보관해 누적 오차가 없다."""

    def __init__(self, start_ms: int = 0) -> None:
        """!
        @brief 시작 시각을 정한다.
        @param start_ms 시작 시각(ms)
        """
        self._ms = start_ms

    def now(self) -> float:
        """!@brief 현재 시각(초). @return 내부 ms / 1000"""
        return self._ms / 1000

    def advance_ms(self, delta_ms: int) -> None:
        """!
        @brief 시계를 앞으로 움직인다.
        @param delta_ms 전진량(ms), 0 이상
        @throws ValueError 음수일 때
        """
        if delta_ms < 0:
            raise ValueError("시계를 되돌릴 수 없습니다")
        self._ms += delta_ms


class MonotonicClock:
    """!@brief 실제 단조 시계. 생성 시각을 0초로 한다."""

    def __init__(self) -> None:
        """!@brief 기준 시각을 기록한다."""
        self._origin = time.monotonic()

    def now(self) -> float:
        """!@brief 생성 후 경과 시간(초). @return 0 이상, 감소하지 않음"""
        return time.monotonic() - self._origin
