"""!
@brief childlock.controller 단위 시험 (SWD 9장).
@details SWR-013(유효성·freshness), SWR-023(주기 입력 처리), SWR-024(초기 상태),
    AD-02(QM 간섭 배제).
"""

import pytest

from childlock.clock import ManualClock
from childlock.controller import ChildLockController
from childlock.event_store import EventStore
from childlock.model import INITIAL_STATUS, InputValidity, Lock, PriorityReason, State
from childlock.override import Annotation, OverrideTracker

L, R = Lock.LOCK, Lock.RELEASE


def raw(ts, **overrides):
    """!@brief 정지·시동 ON 유효 원시 입력."""
    data = {
        "source_timestamp_s": ts,
        "vehicle_speed_kph": 0.0,
        "gear": "P",
        "crash_status": "NONE",
        "rear_left_approach_risk": False,
        "rear_right_approach_risk": False,
        "fire_detected": False,
        "overtemperature_detected": False,
        "adult_present": False,
        "isofix_left": False,
        "isofix_right": False,
        "ignition_on": True,
        "sensor_fault": False,
    }
    data.update(overrides)
    return data


class Harness:
    """!@brief 수동 시계와 실제 QM 컴포넌트로 만든 controller 묶음."""

    def __init__(self, annotator=None, sink=None):
        """!@brief 시험 대상 controller를 만든다."""
        self.clock = ManualClock()
        self.store = sink or EventStore()
        self.ctl = ChildLockController(self.clock, annotator or OverrideTracker(), self.store)

    def cycle(self, snapshot=None, commands=(), advance_ms=50):
        """!@brief 시계를 전진하고 입력을 넣은 뒤 평가 1회."""
        self.clock.advance_ms(advance_ms)
        if snapshot is not None:
            self.ctl.submit_snapshot(snapshot)
        for command in commands:
            self.ctl.submit_command(command)
        return self.ctl.step()

    def now(self):
        """!@brief 현재 시각(초)."""
        return self.clock.now()


def unlock(side="left"):
    """!@brief 해제 명령 원시 입력."""
    return {"side": side, "action": "unlock", "source": "avn"}


def lock(side="all"):
    """!@brief 잠금 명령 원시 입력."""
    return {"side": side, "action": "lock", "source": "avn"}


def test_status_before_first_step_is_initial():
    """!@brief 기동 직후 RELEASE/RELEASE, OFF, NO_DATA (SWR-024 ①)."""
    assert Harness().ctl.status() == INITIAL_STATUS


def test_command_before_first_valid_input_is_not_applied():
    """!@brief 첫 유효 입력 전 잠금 명령은 적용하지 않는다 (SWR-024 ②)."""
    status = Harness().cycle(commands=[lock()])

    assert (status.lock_left, status.lock_right) == (R, R)
    assert status.input_validity is InputValidity.NO_DATA
    assert status.state is State.OFF


def test_first_valid_input_with_ignition_on_becomes_normal():
    """!@brief 첫 유효 입력(시동 ON) 후 NORMAL, VALID (SWR-024 ③)."""
    h = Harness()

    status = h.cycle(raw(0.05))

    assert status.state is State.NORMAL
    assert status.input_validity is InputValidity.VALID


def test_valid_command_is_applied_in_the_same_cycle():
    """!@brief 유효 입력과 같은 주기의 잠금 명령은 그 주기에 적용된다 (SWR-001)."""
    h = Harness()
    status = h.cycle(raw(0.05), [lock()])

    assert (status.lock_left, status.lock_right) == (L, L)
    assert status.reason_code == "driver_lock"


def test_commands_are_consumed_once():
    """!@brief 명령은 한 번만 처리되고 다음 주기에 다시 적용되지 않는다."""
    h = Harness()
    h.cycle(raw(0.05), [lock()])

    assert h.cycle(raw(0.10)).reason_code == "no_change"


def test_invalid_command_is_dropped_with_reason():
    """!@brief 무효 명령은 적용하지 않고 command_invalid를 보고한다 (SWR-013 ②)."""
    h = Harness()
    status = h.cycle(raw(0.05), [{"side": "rear", "action": "lock", "source": "avn"}])

    assert (status.lock_left, status.lock_right) == (R, R)
    assert status.reason_code == "command_invalid"


def test_invalid_command_does_not_hide_valid_one():
    """!@brief 같은 주기에 유효 명령이 적용되면 그 결과를 보고한다."""
    h = Harness()
    status = h.cycle(raw(0.05), [{"side": 1}, lock("left")])

    assert status.lock_left is L
    assert status.reason_code == "driver_lock"


def test_invalid_snapshot_holds_outputs_and_reports_invalid():
    """!@brief 무효 입력은 판정에 쓰지 않고 출력 유지, INVALID (SWR-013 ①)."""
    h = Harness()
    h.cycle(raw(0.05), [lock()])

    status = h.cycle(raw(0.10, vehicle_speed_kph=300.1, ignition_on=False))

    assert (status.lock_left, status.lock_right) == (L, L)
    assert status.input_validity is InputValidity.INVALID
    assert status.reason_code == "input_invalid"


def test_last_snapshot_in_cycle_decides_validity():
    """!@brief 한 주기의 마지막 입력이 무효면 INVALID, 앞선 유효 입력은 보관된다 (REV-D-03)."""
    h = Harness()
    h.clock.advance_ms(50)
    h.ctl.submit_snapshot(raw(0.05, ignition_on=False))
    h.ctl.submit_snapshot({"bad": True})

    assert h.ctl.step().input_validity is InputValidity.INVALID
    assert h.cycle().state is State.OFF  # 보관된 유효 입력(시동 꺼짐)으로 판정


def test_latest_valid_snapshot_in_cycle_is_used():
    """!@brief 한 주기에 유효 입력이 여럿이면 마지막 것을 쓴다."""
    h = Harness()
    h.clock.advance_ms(50)
    h.ctl.submit_snapshot(raw(0.04, vehicle_speed_kph=10.0))
    h.ctl.submit_snapshot(raw(0.05, ignition_on=False))

    assert h.ctl.step().state is State.OFF


def test_input_is_fresh_at_200_ms_and_degraded_within_100_ms_after():
    """!@brief 200 ms까지 VALID, 초과 후 다음 주기(≤100 ms)에 DEGRADED (SWR-013 ③, SWR-023 ③)."""
    h = Harness()
    h.cycle(raw(0.0, vehicle_speed_kph=10.0), advance_ms=0)

    assert h.cycle(advance_ms=200).input_validity is InputValidity.VALID  # 경과 200 ms
    status = h.cycle(advance_ms=50)  # 경과 250 ms: 200 ms 초과 후 50 ms
    assert status.state is State.DEGRADED
    assert status.input_validity is InputValidity.STALE
    assert (status.lock_left, status.lock_right) == (L, L)


def test_degraded_ignores_driver_and_recovers_on_fresh_input():
    """!@brief DEGRADED 중 해제 명령 무시, 유효 입력 재수신 시 복귀 (SWR-013 ④⑤)."""
    h = Harness()
    h.cycle(raw(0.0, vehicle_speed_kph=10.0), advance_ms=0)
    h.cycle(advance_ms=250)

    assert h.cycle(commands=[unlock("all")]).lock_left is L
    status = h.cycle(raw(h.now() + 0.05))
    assert status.state is State.NORMAL
    assert status.input_validity is InputValidity.VALID


def test_override_is_reported_on_second_unlock_within_10_s():
    """!@brief 접근위험 억제 후 10 s 이하 재입력 → OVERRIDE, 출력 LOCK 유지 (SWR-006 ①)."""
    h = Harness()
    h.cycle(raw(0.05, rear_left_approach_risk=True), [unlock()])
    h.cycle(raw(5.0, rear_left_approach_risk=True), advance_ms=4950)

    status = h.cycle(raw(5.05, rear_left_approach_risk=True), [unlock()])

    assert status.state is State.OVERRIDE
    assert status.reason_code == "approach_override_left"
    assert status.lock_left is L


def test_events_are_recorded_every_cycle_with_input_timestamp():
    """!@brief 평가마다 이벤트를 기록하고 시각은 판정에 쓴 입력 시각이다 (SWR-010)."""
    h = Harness()
    h.cycle()
    h.cycle(raw(0.07))

    events = h.store.list_events()
    assert [e.event_id for e in events] == [1, 2]
    assert events[0].timestamp_s == pytest.approx(0.05)  # 입력 없음: 평가 시각
    assert events[1].timestamp_s == pytest.approx(0.07)


class BrokenAnnotator:
    """!@brief 예외를 던지는 QM 대역 (간섭 시험용)."""

    def annotate(self, *args):
        """!@brief 항상 실패한다."""
        raise RuntimeError("override 고장")


class BrokenSink:
    """!@brief 기록에 실패하는 QM 대역."""

    def record(self, *args):
        """!@brief 항상 실패한다."""
        raise RuntimeError("저장소 고장")


class HostileAnnotator:
    """!@brief 항상 OVERRIDE를 주장하는 QM 대역."""

    def annotate(self, *args):
        """!@brief 출력과 무관한 주석만 돌려줄 수 있다."""
        return Annotation(State.OVERRIDE, "approach_override_left")


def test_qm_annotator_failure_does_not_change_safety_outputs():
    """!@brief override 예외에도 판정 출력이 그대로다 (SWA 10장)."""
    status = Harness(annotator=BrokenAnnotator()).cycle(raw(0.05), [lock()])

    assert (status.lock_left, status.lock_right) == (L, L)
    assert status.reason_code == "driver_lock"


def test_qm_sink_failure_does_not_stop_the_cycle():
    """!@brief 이력 저장 예외에도 평가 결과와 상태 조회가 갱신된다 (SWA 10장)."""
    h = Harness(sink=BrokenSink())
    status = h.cycle(raw(0.05), [lock()])

    assert h.ctl.status() == status
    assert status.lock_left is L


def test_annotation_cannot_change_outputs():
    """!@brief QM 주석은 state·reason만 바꾸고 출력은 판정 값 그대로다 (AD-02)."""
    status = Harness(annotator=HostileAnnotator()).cycle(raw(0.05), [unlock("all")])

    assert (status.lock_left, status.lock_right) == (R, R)
    assert status.state is State.OVERRIDE
    assert status.priority_reason is PriorityReason.DRIVER_COMMAND
