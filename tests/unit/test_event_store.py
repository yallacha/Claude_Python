"""!
@brief childlock.event_store 단위 시험 (SWD 7장, SWR-010~012).
"""

import dataclasses

from childlock.event_store import EventStore
from childlock.model import InputValidity, Lock, PriorityReason, State, Status

STATUS = Status(
    Lock.LOCK,
    Lock.RELEASE,
    State.FAULT,
    InputValidity.VALID,
    PriorityReason.SENSOR_FAULT,
    "sensor_fault",
    "W_SENSOR_FAULT",
)
ALLOWED_FIELDS = {
    "event_id",
    "timestamp_s",
    "state",
    "lock_left",
    "lock_right",
    "priority_reason",
    "reason_code",
    "input_validity",
}


def filled(count, capacity=100):
    """!@brief count건을 기록한 저장소. timestamp는 event 순번과 같게 둔다."""
    store = EventStore(capacity)
    for i in range(count):
        store.record(STATUS, float(i + 1))
    return store


def test_event_ids_start_at_1_and_increase_by_1():
    """!@brief 평가 5회 후 event_id는 1~5 순서 (SWR-010)."""
    assert [e.event_id for e in filled(5).list_events()] == [1, 2, 3, 4, 5]


def test_new_store_is_empty_and_restarts_ids():
    """!@brief 새 저장소(재기동)는 비어 있고 ID가 1부터 다시 시작 (SWR-010, SWR-012 ③)."""
    store = EventStore()

    assert store.list_events() == ()
    store.record(STATUS, 0.0)
    assert store.list_events()[0].event_id == 1


def test_exactly_100_events_are_all_kept():
    """!@brief 100건(경계값)은 모두 보존 (SWR-012 ②)."""
    assert len(filled(100).list_events()) == 100


def test_101st_event_drops_the_oldest():
    """!@brief 101건 후 event_id 2~101의 100건이 오름차순 (SWR-012 ①)."""
    ids = [e.event_id for e in filled(101).list_events()]

    assert ids == list(range(2, 102))


def test_event_has_only_allowed_fields_with_status_values():
    """!@brief 이벤트 필드는 허용 8개뿐이고 warning_code 등은 없다 (SWR-011, D-06)."""
    event = filled(1).list_events()[0]

    assert {f.name for f in dataclasses.fields(event)} == ALLOWED_FIELDS
    assert (event.lock_left, event.lock_right, event.state) == (
        Lock.LOCK,
        Lock.RELEASE,
        State.FAULT,
    )
    assert event.timestamp_s == 1.0
    assert event.reason_code == "sensor_fault"
