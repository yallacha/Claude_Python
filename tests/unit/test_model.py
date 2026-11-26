"""!
@brief childlock.model 단위 시험 (SWD 1.1, 2장).
"""

import dataclasses

import pytest

from childlock.model import (
    INITIAL_STATE,
    INITIAL_STATUS,
    ControllerState,
    Door,
    InputValidity,
    Lock,
    PriorityReason,
    State,
    door_lock,
    to_ms,
)


def test_to_ms_absorbs_float_accumulation_error():
    """!@brief 0.05 s를 200번 더한 값도 정확히 10000 ms로 바꾼다 (DD-C02)."""
    total = 0.0
    for _ in range(200):
        total += 0.05

    assert total != 10.0  # 부동소수 오차가 실제로 있음을 전제로 확인
    assert to_ms(total) == 10000


def test_to_ms_rounds_to_nearest_millisecond():
    """!@brief 0.2004 s는 200 ms, 0.2006 s는 201 ms다."""
    assert to_ms(0.2004) == 200
    assert to_ms(0.2006) == 201


def test_priority_ranks_follow_swr_022_order():
    """!@brief 판정 우선순위 순서가 SWR-022의 1~8순위와 같다."""
    ordered = [
        PriorityReason.CRASH,
        PriorityReason.SENSOR_FAULT,
        PriorityReason.APPROACH_RISK,
        PriorityReason.IGNITION_OFF,
        PriorityReason.FORCED_RELEASE,
        PriorityReason.ISOFIX,
        PriorityReason.AUTO_LOCK,
        PriorityReason.DRIVER_COMMAND,
        PriorityReason.HOLD,
    ]
    ranks = [reason.rank for reason in ordered]

    assert ranks == sorted(ranks)
    assert len(set(ranks)) == len(ranks)


def test_sensor_fault_and_input_stale_share_rank_2():
    """!@brief 센서 고장과 freshness 상실은 같은 2순위다 (SWR-022 ②)."""
    assert PriorityReason.SENSOR_FAULT.rank == PriorityReason.INPUT_STALE.rank == 2


def test_hold_and_input_invalid_rank_below_every_rule():
    """!@brief 규칙 없음(hold)과 입력 거절은 모든 규칙보다 순위가 낮다."""
    assert PriorityReason.HOLD.rank > PriorityReason.DRIVER_COMMAND.rank
    assert PriorityReason.INPUT_INVALID.rank == PriorityReason.HOLD.rank


def test_door_lock_selects_output_of_each_door():
    """!@brief 도어별 출력 선택이 좌·우를 바꾸지 않는다 (SWR-009)."""
    state = ControllerState(Lock.LOCK, Lock.RELEASE, State.NORMAL, False)

    assert door_lock(state, Door.LEFT) is Lock.LOCK
    assert door_lock(state, Door.RIGHT) is Lock.RELEASE


def test_initial_state_and_status_are_released_off_no_data():
    """!@brief 기동 시 두 출력 RELEASE, OFF, NO_DATA다 (SWR-024 ①)."""
    assert (INITIAL_STATE.lock_left, INITIAL_STATE.lock_right) == (Lock.RELEASE, Lock.RELEASE)
    assert INITIAL_STATE.state is State.OFF
    assert INITIAL_STATE.crash_latched is False
    assert INITIAL_STATUS.input_validity is InputValidity.NO_DATA
    assert INITIAL_STATUS.state is State.OFF
    assert INITIAL_STATUS.priority_reason is PriorityReason.HOLD
    assert INITIAL_STATUS.reason_code == "no_change"
    assert INITIAL_STATUS.warning_code is None


def test_data_objects_are_immutable():
    """!@brief 데이터 객체는 생성 후 바꿀 수 없다 (AD-04)."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        INITIAL_STATE.lock_left = Lock.LOCK  # type: ignore[misc]
