"""!
@brief childlock.decision 단위 시험 (SWD 5장).
@details SWR-001~005, 007~009, 013, 017, 018, 020~022, 024의 판정 규칙을 검증한다.
"""

import dataclasses

import pytest

from childlock.decision import decide
from childlock.model import (
    INITIAL_STATE,
    Action,
    ControllerState,
    CrashStatus,
    Door,
    DriverCommand,
    Gear,
    InputValidity,
    Lock,
    PriorityReason,
    Side,
    Source,
    State,
    VehicleSnapshot,
)

L, R = Lock.LOCK, Lock.RELEASE
BASE = VehicleSnapshot(
    source_timestamp_s=1.0,
    vehicle_speed_kph=0.0,
    gear=Gear.P,
    crash_status=CrashStatus.NONE,
    rear_left_approach_risk=False,
    rear_right_approach_risk=False,
    fire_detected=False,
    overtemperature_detected=False,
    adult_present=False,
    isofix_left=False,
    isofix_right=False,
    ignition_on=True,
    sensor_fault=False,
)


def snap(**changes):
    """!@brief 정지·시동 ON·이상 없음 기본 입력에서 일부를 바꾼다."""
    return dataclasses.replace(BASE, **changes)


def prev(left=R, right=R, state=State.NORMAL, latched=False):
    """!@brief 이전 확정 상태를 만든다."""
    return ControllerState(left, right, state, latched)


def cmd(side, action, source=Source.PHYSICAL_BUTTON):
    """!@brief 운전자 명령을 만든다."""
    return DriverCommand(Side(side), Action(action), source)


def run(snapshot=BASE, commands=(), previous=None, validity=InputValidity.VALID):
    """!@brief 기본값을 채워 decide를 호출한다."""
    return decide(snapshot, tuple(commands), previous or prev(), validity)


def outputs(decision):
    """!@brief (좌, 우) 출력 쌍."""
    return decision.lock_left, decision.lock_right


# ---- 1순위: 충돌 (SWR-007) ----


def test_crash_confirmed_releases_both_over_risk_speed_and_fault():
    """!@brief 접근위험·50 km/h·센서 고장 중에도 CONFIRMED면 두 출력 RELEASE (SWR-007 ①④)."""
    d = run(
        snap(
            crash_status=CrashStatus.CONFIRMED,
            rear_left_approach_risk=True,
            vehicle_speed_kph=50.0,
            sensor_fault=True,
        ),
        previous=prev(L, L),
    )

    assert outputs(d) == (R, R)
    assert d.state is State.CRASH_RELEASE
    assert d.priority_reason is PriorityReason.CRASH
    assert d.reason_code == "crash_confirmed"
    assert d.crash_latched is True


def test_crash_release_is_latched_after_status_returns_to_none():
    """!@brief 확정 후 NONE·잠금 명령·50 km/h에도 RELEASE 유지 (SWR-007 ②, D-12)."""
    d = run(
        snap(vehicle_speed_kph=50.0),
        [cmd("all", "lock")],
        prev(R, R, State.CRASH_RELEASE, latched=True),
    )

    assert outputs(d) == (R, R)
    assert d.state is State.CRASH_RELEASE
    assert d.reason_code == "crash_confirmed"


def test_crash_latch_is_cleared_by_ignition_off():
    """!@brief 시동 꺼짐에서 latch가 풀리고 시동 꺼짐 규칙이 적용된다 (SWR-007 ③)."""
    d = run(snap(ignition_on=False), previous=prev(R, R, State.CRASH_RELEASE, latched=True))

    assert d.crash_latched is False
    assert d.state is State.OFF
    assert d.reason_code == "ignition_off"


def test_crash_confirmed_with_ignition_off_still_latches():
    """!@brief CONFIRMED가 계속 들어오면 시동 꺼짐과 함께여도 긴급 해제 상태다."""
    d = run(snap(crash_status=CrashStatus.CONFIRMED, ignition_on=False))

    assert d.crash_latched is True
    assert d.state is State.CRASH_RELEASE


def test_latched_crash_applies_even_when_input_is_invalid():
    """!@brief 무효 입력 주기에도 latch 중이면 1순위 해제를 유지한다."""
    d = run(previous=prev(R, R, State.CRASH_RELEASE, True), validity=InputValidity.INVALID)

    assert outputs(d) == (R, R)
    assert d.priority_reason is PriorityReason.CRASH


# ---- 2순위: 센서 고장, freshness 상실 (SWR-021, SWR-013) ----


def test_sensor_fault_holds_outputs_and_reports_fault():
    """!@brief 센서 고장 첫 주기에 좌 LOCK·우 RELEASE 유지, FAULT, 경고 코드 (SWR-021 ①)."""
    d = run(snap(sensor_fault=True), previous=prev(L, R))

    assert outputs(d) == (L, R)
    assert d.state is State.FAULT
    assert d.warning_code == "W_SENSOR_FAULT"
    assert d.reason_code == "sensor_fault"


def test_sensor_fault_ignores_speed_isofix_and_driver_with_fault_reason():
    """!@brief 고장 중 50 km/h·ISOFIX·해제 명령 무시, 이유는 sensor_fault (SWR-021 ②, CR-01)."""
    d = run(
        snap(sensor_fault=True, vehicle_speed_kph=50.0, isofix_right=True),
        [cmd("left", "unlock")],
        prev(L, R),
    )

    assert outputs(d) == (L, R)
    assert d.reason_code == "sensor_fault"


def test_sensor_fault_blocks_approach_risk_lock():
    """!@brief 인접 순위 ②+③: 고장 중 접근위험이 와도 출력 유지 (SWR-022)."""
    d = run(snap(sensor_fault=True, rear_left_approach_risk=True), previous=prev(R, R))

    assert outputs(d) == (R, R)
    assert d.priority_reason is PriorityReason.SENSOR_FAULT


def test_stale_input_holds_outputs_as_degraded():
    """!@brief freshness 상실 시 출력 유지, DEGRADED, 명령 미적용 (SWR-013 ③④, CR-01)."""
    d = run(
        snap(vehicle_speed_kph=50.0),
        [cmd("all", "unlock")],
        prev(L, L),
        InputValidity.STALE,
    )

    assert outputs(d) == (L, L)
    assert d.state is State.DEGRADED
    assert d.priority_reason is PriorityReason.INPUT_STALE
    assert d.reason_code == "input_stale"


def test_sensor_fault_is_reported_before_stale():
    """!@brief 고장과 freshness 상실이 함께면 고장을 먼저 보고한다 (REV-D-05)."""
    d = run(snap(sensor_fault=True), validity=InputValidity.STALE)

    assert d.priority_reason is PriorityReason.SENSOR_FAULT
    assert d.state is State.FAULT


# ---- 3순위: 접근위험 (SWR-005, SWR-009) ----


def test_approach_risk_locks_only_that_door():
    """!@brief 좌측 접근위험은 좌측만 LOCK, 우측은 그대로 (SWR-005 ①, SWR-009 ②)."""
    d = run(snap(rear_left_approach_risk=True))

    assert outputs(d) == (L, R)
    assert d.reason_code == "approach_risk_left"


def test_right_approach_risk_does_not_touch_left():
    """!@brief 우측 접근위험만 true면 좌측 출력 변화 없음 (SWR-009 ②)."""
    d = run(snap(rear_right_approach_risk=True), previous=prev(R, R))

    assert outputs(d) == (R, L)
    assert d.reason_code == "approach_risk_right"


def test_unlock_request_on_risky_door_is_suppressed():
    """!@brief 접근위험 도어 해제 요청은 억제·기록 (SWR-005 ②, SWR-006 입력)."""
    d = run(snap(rear_left_approach_risk=True), [cmd("left", "unlock")], prev(L, R))

    assert outputs(d) == (L, R)
    assert d.suppressed_unlocks == (Door.LEFT,)
    assert d.reason_code == "approach_risk_left"


def test_all_unlock_with_left_risk_releases_only_right():
    """!@brief side=all 해제에서 좌측만 접근위험이면 우측만 RELEASE (SWR-009 ①)."""
    d = run(snap(rear_left_approach_risk=True), [cmd("all", "unlock")], prev(L, L))

    assert outputs(d) == (L, R)
    assert d.suppressed_unlocks == (Door.LEFT,)


def test_lock_request_on_risky_door_is_not_suppression():
    """!@brief 접근위험 도어 잠금 요청은 억제가 아니다."""
    d = run(snap(rear_left_approach_risk=True), [cmd("left", "lock")])

    assert d.suppressed_unlocks == ()


def test_approach_risk_keeps_lock_when_ignition_off():
    """!@brief 인접 순위 ③+④: 시동 꺼짐에도 접근위험 도어는 LOCK (SWR-005 ③)."""
    d = run(snap(rear_left_approach_risk=True, ignition_on=False), previous=prev(L, L))

    assert outputs(d) == (L, R)
    assert d.priority_reason is PriorityReason.APPROACH_RISK
    assert d.state is State.OFF


# ---- 4순위: 시동 꺼짐 (SWR-020) ----


def test_ignition_off_releases_both_as_off():
    """!@brief 시동 꺼짐 첫 주기에 두 출력 RELEASE, OFF (SWR-020 ①)."""
    d = run(snap(ignition_on=False), previous=prev(L, L))

    assert outputs(d) == (R, R)
    assert d.state is State.OFF
    assert d.reason_code == "ignition_off"


def test_ignition_off_rejects_lock_command():
    """!@brief 시동 꺼짐 중 잠금 명령은 거절 (SWR-004 ③)."""
    d = run(snap(ignition_on=False), [cmd("all", "lock")])

    assert outputs(d) == (R, R)
    assert d.reason_code == "driver_rejected"


def test_ignition_off_outranks_fire():
    """!@brief 인접 순위 ④+⑤: 시동 꺼짐과 화재가 함께면 판정 근거는 시동 꺼짐."""
    d = run(snap(ignition_on=False, fire_detected=True), previous=prev(L, L))

    assert outputs(d) == (R, R)
    assert d.priority_reason is PriorityReason.IGNITION_OFF


# ---- 5순위: 강제 해제 (SWR-017) ----


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("fire_detected", "fire"),
        ("overtemperature_detected", "overtemperature"),
        ("adult_present", "adult_present"),
    ],
)
def test_each_forced_release_input_releases_both(field, reason):
    """!@brief 화재·과온·성인 각각 단독으로 두 출력 RELEASE와 입력별 이유 (SWR-017 ①)."""
    d = run(snap(**{field: True}), previous=prev(L, L))

    assert outputs(d) == (R, R)
    assert d.reason_code == reason


@pytest.mark.parametrize(
    ("fields", "reason"),
    [
        (("fire_detected", "overtemperature_detected", "adult_present"), "fire"),
        (("overtemperature_detected", "adult_present"), "overtemperature"),
    ],
)
def test_simultaneous_forced_release_reports_highest_cause(fields, reason):
    """!@brief 동시 입력은 화재 > 과온 > 성인 순으로 하나를 기록 (SWR-017 ⑤, D-15)."""
    d = run(snap(**{name: True for name in fields}))

    assert d.reason_code == reason


def test_adult_present_releases_while_driving():
    """!@brief 50 km/h 주행 중에도 성인 탑승이면 RELEASE (SWR-017 ②)."""
    d = run(snap(adult_present=True, vehicle_speed_kph=50.0), previous=prev(L, L))

    assert outputs(d) == (R, R)


def test_fire_outranks_isofix():
    """!@brief 인접 순위 ⑤+⑥: 화재와 ISOFIX가 함께면 RELEASE (SWR-017 ③)."""
    d = run(snap(fire_detected=True, isofix_left=True), previous=prev(L, L))

    assert outputs(d) == (R, R)
    assert d.priority_reason is PriorityReason.FORCED_RELEASE


def test_fire_with_left_risk_keeps_left_locked():
    """!@brief 화재와 좌측 접근위험: 좌 LOCK, 우 RELEASE (SWR-017 ④)."""
    d = run(snap(fire_detected=True, rear_left_approach_risk=True), previous=prev(L, L))

    assert outputs(d) == (L, R)


def test_lock_command_during_fire_is_rejected():
    """!@brief 화재 중 잠금 명령은 거절 (SWR-004 ④)."""
    d = run(snap(fire_detected=True), [cmd("all", "lock")])

    assert outputs(d) == (R, R)
    assert d.reason_code == "driver_rejected"


# ---- 6순위: ISOFIX (SWR-018) ----


def test_isofix_left_locks_only_left():
    """!@brief 좌측 ISOFIX만 true면 좌측만 LOCK (SWR-018 ①)."""
    d = run(snap(isofix_left=True))

    assert outputs(d) == (L, R)
    assert d.reason_code == "isofix_left"


def test_isofix_rejects_unlock_on_that_door():
    """!@brief ISOFIX 도어 해제 명령은 거절 (SWR-018 ②, SWR-004 ②)."""
    d = run(snap(isofix_left=True), [cmd("left", "unlock")], prev(L, R))

    assert outputs(d) == (L, R)
    assert d.reason_code == "driver_rejected"


def test_isofix_door_released_when_ignition_off():
    """!@brief ISOFIX와 시동 꺼짐이 함께면 RELEASE (SWR-018 ③)."""
    d = run(snap(isofix_left=True, ignition_on=False), previous=prev(L, R))

    assert outputs(d) == (R, R)


def test_isofix_outranks_auto_lock_in_combined_reason():
    """!@brief 인접 순위 ⑥+⑦: 좌 ISOFIX·우 자동잠금이면 판정 근거는 ISOFIX."""
    d = run(snap(isofix_left=True, vehicle_speed_kph=10.0))

    assert outputs(d) == (L, L)
    assert d.priority_reason is PriorityReason.ISOFIX
    assert d.reason_code == "isofix_left"


def test_all_unlock_with_left_isofix_releases_only_right():
    """!@brief side=all 해제에서 좌측만 ISOFIX면 우측만 RELEASE (SWR-004 ⑤)."""
    d = run(snap(isofix_left=True), [cmd("all", "unlock")], prev(L, L))

    assert outputs(d) == (L, R)


def test_right_driver_unlock_with_left_isofix_reports_isofix():
    """!@brief 좌 ISOFIX(⑥)·우 운전자 해제(⑧)면 isofix_left로 보고 (SWR-022 동률 예시)."""
    d = run(snap(isofix_left=True), [cmd("right", "unlock")], prev(L, L))

    assert outputs(d) == (L, R)
    assert d.priority_reason is PriorityReason.ISOFIX
    assert d.reason_code == "isofix_left"


# ---- 7순위: 주행 자동 잠금 (SWR-003) ----


def test_auto_lock_at_exactly_3_kph():
    """!@brief 차속 3.0 km/h(경계값)에서 두 출력 LOCK (SWR-003 ①)."""
    d = run(snap(vehicle_speed_kph=3.0))

    assert outputs(d) == (L, L)
    assert d.reason_code == "auto_lock_speed"


def test_no_auto_lock_at_2_9_kph():
    """!@brief 차속 2.9 km/h(경계 바로 아래)에서는 자동 잠금하지 않음 (SWR-003 ②)."""
    d = run(snap(vehicle_speed_kph=2.9))

    assert outputs(d) == (R, R)
    assert d.priority_reason is PriorityReason.HOLD


def test_lock_is_kept_after_speed_drops_below_threshold():
    """!@brief 3.0 이상 후 2.9로 내려가도 LOCK 유지 (SWR-003 ③)."""
    d = run(snap(vehicle_speed_kph=2.9), previous=prev(L, L))

    assert outputs(d) == (L, L)


def test_unlock_while_driving_is_rejected():
    """!@brief 인접 순위 ⑦+⑧: 주행 중 해제 명령은 거절 (SWR-004 ①)."""
    d = run(snap(vehicle_speed_kph=3.0), [cmd("all", "unlock")], prev(L, L))

    assert outputs(d) == (L, L)
    assert d.priority_reason is PriorityReason.AUTO_LOCK
    assert d.reason_code == "driver_rejected"


# ---- 8순위: 운전자 명령 (SWR-001, SWR-002) ----


@pytest.mark.parametrize("source", list(Source))
@pytest.mark.parametrize(
    ("side", "expected"),
    [("left", (L, R)), ("right", (R, L)), ("all", (L, L))],
)
def test_lock_command_applies_only_to_selected_doors(source, side, expected):
    """!@brief 4개 경로 × 3개 대상 잠금 명령이 지정 출력에만 적용 (SWR-001)."""
    d = run(commands=[cmd(side, "lock", source)], previous=prev(R, R))

    assert outputs(d) == expected
    assert d.reason_code == "driver_lock"


@pytest.mark.parametrize("source", list(Source))
@pytest.mark.parametrize(
    ("side", "expected"),
    [("left", (R, L)), ("right", (L, R)), ("all", (R, R))],
)
def test_unlock_command_applies_only_to_selected_doors(source, side, expected):
    """!@brief 4개 경로 × 3개 대상 해제 명령이 지정 출력에만 적용 (SWR-002)."""
    d = run(commands=[cmd(side, "unlock", source)], previous=prev(L, L))

    assert outputs(d) == expected
    assert d.reason_code == "driver_unlock"


def test_last_command_for_a_door_wins_within_a_cycle():
    """!@brief 한 주기의 좌측 잠금 → 좌측 해제는 받은 순서대로 적용되어 RELEASE (SWR-023 ②)."""
    d = run(commands=[cmd("left", "lock"), cmd("left", "unlock")], previous=prev(R, R))

    assert d.lock_left is R


# ---- 규칙 없음, 결합, 입력 없음 (SWR-008, SWR-022, SWR-013, SWR-024) ----


def test_no_rule_holds_outputs_as_normal():
    """!@brief 적용할 규칙이 없으면 출력 유지, hold, no_change, NORMAL."""
    d = run(previous=prev(L, R))

    assert outputs(d) == (L, R)
    assert d.priority_reason is PriorityReason.HOLD
    assert d.reason_code == "no_change"
    assert d.state is State.NORMAL
    assert d.warning_code is None


def test_crash_pending_is_recorded_when_no_high_priority_rule():
    """!@brief PENDING이고 1~3순위가 없으면 crash_pending, 해제 안 함 (SWR-008 ①)."""
    d = run(snap(crash_status=CrashStatus.PENDING), previous=prev(L, L))

    assert outputs(d) == (L, L)
    assert d.reason_code == "crash_pending"
    assert d.crash_latched is False


def test_crash_pending_with_auto_lock_still_reports_pending():
    """!@brief PENDING과 7순위 자동잠금이면 crash_pending을 기록한다 (순위 3 초과)."""
    d = run(snap(crash_status=CrashStatus.PENDING, vehicle_speed_kph=10.0))

    assert d.reason_code == "crash_pending"
    assert d.priority_reason is PriorityReason.AUTO_LOCK


def test_crash_pending_yields_to_approach_risk_reason():
    """!@brief PENDING이어도 3순위 접근위험이면 그 이유를 기록 (SWR-008)."""
    d = run(snap(crash_status=CrashStatus.PENDING, rear_left_approach_risk=True))

    assert d.reason_code == "approach_risk_left"


def test_no_data_holds_initial_state_and_ignores_commands():
    """!@brief 유효 입력 전에는 명령을 적용하지 않고 초기 상태 유지 (SWR-024 ②)."""
    d = decide(None, (cmd("all", "lock"),), INITIAL_STATE, InputValidity.NO_DATA)

    assert outputs(d) == (R, R)
    assert d.state is State.OFF
    assert d.priority_reason is PriorityReason.HOLD
    assert d.reason_code == "no_change"


def test_invalid_input_holds_outputs_and_previous_state():
    """!@brief 무효 입력 주기는 출력·state 유지, 명령 미적용 (SWR-013 ①, D-13)."""
    d = run(
        snap(vehicle_speed_kph=50.0),
        [cmd("all", "unlock")],
        prev(L, L, State.OVERRIDE),
        InputValidity.INVALID,
    )

    assert outputs(d) == (L, L)
    assert d.state is State.OVERRIDE
    assert d.priority_reason is PriorityReason.INPUT_INVALID
    assert d.reason_code == "input_invalid"
