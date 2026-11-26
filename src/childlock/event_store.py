"""!
@brief 결정 이력 저장소 (QM, SWD 7장, SWR-010~012).
@details 메모리(deque)에만 보존하고 파일·네트워크 I/O를 하지 않는다(AD-06).
"""

from collections import deque

from childlock.model import EVENT_CAPACITY, Event, Status


class EventStore:
    """!@brief 최신 capacity건의 결정 이벤트를 보존한다."""

    def __init__(self, capacity: int = EVENT_CAPACITY) -> None:
        """!
        @brief 빈 저장소를 만든다. ID는 1부터 시작한다.
        @param capacity 보존 건수. 넘으면 가장 오래된 이벤트부터 버린다
        """
        self._events: deque[Event] = deque(maxlen=capacity)
        self._next_id = 1

    def record(self, status: Status, timestamp_s: float) -> None:
        """!
        @brief 상태를 이벤트로 기록한다. 허용 필드만 복사한다 (SWR-011).
        @param status 평가 결과 상태
        @param timestamp_s 판정에 쓴 입력 시각
        """
        self._events.append(
            Event(
                event_id=self._next_id,
                timestamp_s=timestamp_s,
                state=status.state,
                lock_left=status.lock_left,
                lock_right=status.lock_right,
                priority_reason=status.priority_reason,
                reason_code=status.reason_code,
                input_validity=status.input_validity,
            )
        )
        self._next_id += 1

    def list_events(self) -> tuple[Event, ...]:
        """!@brief 보존 중인 이벤트. @return event_id 오름차순"""
        return tuple(self._events)
