"""!
@brief SW 통합 시험 (SWE.5, docs/05_integration_test/ITS_통합시험명세및결과.md).
@details 실제 컴포넌트를 연결해 SWA 5장 인터페이스, 6장 동적 동작, 7장 타이밍,
    10장 간섭 배제를 검증한다.
    대역은 IT-06(QM 고장 주입)에만 쓴다.
"""

import time

import pytest
from fastapi.testclient import TestClient

from childlock.clock import ManualClock
from childlock.controller import ChildLockController
from childlock.event_store import EventStore
from childlock.model import Lock, State
from childlock.override import OverrideTracker
from childlock.replay import ReplayStep, result_hash, run
from childlock.web import create_app

L, R = Lock.LOCK, Lock.RELEASE


def snap(ts, **overrides):
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


def command(side, action, source="avn"):
    """!@brief 운전자 명령 원시 입력."""
    return {"side": side, "action": action, "source": source}


class System:
    """!@brief 실제 컴포넌트를 연결한 시험 대상(수동 시계, 수동 평가 Web)."""

    def __init__(self, sink=None):
        """!@brief controller·override·event_store·web을 연결한다."""
        self.clock = ManualClock()
        self.store = sink or EventStore()
        self.controller = ChildLockController(self.clock, OverrideTracker(), self.store)
        events = self.store if isinstance(self.store, EventStore) else EventStore()
        self.app = create_app(self.controller, events, self.clock, run_loop=False)

    def cycle(self, client, snapshot=None, commands=(), advance_ms=50):
        """!@brief HTTP로 입력을 보내고 평가 1회 후 상태(JSON)를 돌려준다."""
        self.clock.advance_ms(advance_ms)
        if snapshot is not None:
            assert client.post("/api/snapshot", json=snapshot).status_code == 202
        for c in commands:
            assert client.post("/api/command", json=c).status_code == 202
        return client.post("/api/step").json()


def test_it01_http_input_to_status_and_event_are_consistent():
    """!@brief IT-01: HTTP 입력 → 검증 → 판정 → 상태 → 이력이 한 주기에서 일치 (SWA 6.1)."""
    sys_ = System()
    with TestClient(sys_.app) as client:
        stepped = sys_.cycle(client, snap(0.05), [command("left", "lock", "voice")])
        status = client.get("/api/status").json()
        events = client.get("/api/events").json()

    assert stepped == status
    assert (status["lock_left"], status["lock_right"]) == ("LOCK", "RELEASE")
    assert events[-1]["reason_code"] == status["reason_code"] == "driver_lock"
    assert events[-1]["timestamp_s"] == 0.05


def test_it02_priority_flow_across_a_driving_scenario():
    """!@brief IT-02: 주행 자동잠금 → 성인 해제 → 접근위험 잠금 → 충돌 해제 흐름 (SWA 6.2)."""
    steps = (
        ReplayStep(50, (snap(0.05, vehicle_speed_kph=30.0),), ()),
        ReplayStep(50, (snap(0.10, vehicle_speed_kph=30.0, adult_present=True),), ()),
        ReplayStep(50, (snap(0.15, adult_present=True, rear_right_approach_risk=True),), ()),
        ReplayStep(50, (snap(0.20, rear_right_approach_risk=True, crash_status="CONFIRMED"),), ()),
    )
    statuses = run(steps).statuses

    assert [(s.lock_left, s.lock_right) for s in statuses] == [(L, L), (R, R), (R, L), (R, R)]
    assert [s.priority_reason.value for s in statuses] == [
        "auto_lock",
        "forced_release",
        "approach_risk",
        "crash",
    ]


def test_it03_state_transitions_follow_architecture_state_machine():
    """!
    @brief IT-03: state 전이 순서 (SWA 6.3).
    @details OFF→NORMAL→OVERRIDE→NORMAL→DEGRADED→NORMAL→FAULT→NORMAL→CRASH_RELEASE→OFF
    """
    risk = {"rear_left_approach_risk": True}
    steps = (
        ReplayStep(50, (), ()),
        ReplayStep(50, (snap(0.10),), ()),
        ReplayStep(50, (snap(0.15, **risk),), (command("left", "unlock"),)),
        ReplayStep(50, (snap(0.20, **risk),), (command("left", "unlock"),)),
        ReplayStep(50, (snap(0.25),), ()),
        ReplayStep(250, (), ()),
        ReplayStep(50, (snap(0.55),), ()),
        ReplayStep(50, (snap(0.60, sensor_fault=True),), ()),
        ReplayStep(50, (snap(0.65),), ()),
        ReplayStep(50, (snap(0.70, crash_status="CONFIRMED"),), ()),
        ReplayStep(50, (snap(0.75, ignition_on=False),), ()),
    )
    states = [s.state for s in run(steps).statuses]

    assert states == [
        State.OFF,
        State.NORMAL,
        State.NORMAL,
        State.OVERRIDE,
        State.NORMAL,
        State.DEGRADED,
        State.NORMAL,
        State.FAULT,
        State.NORMAL,
        State.CRASH_RELEASE,
        State.OFF,
    ]


def test_it04_override_annotation_flows_through_http_without_changing_outputs():
    """!@brief IT-04: controller↔override 연동, 재입력 시 OVERRIDE 표시·LOCK 유지 (SWA 5, 10장)."""
    sys_ = System()
    risky = snap(0.05, rear_right_approach_risk=True)
    with TestClient(sys_.app) as client:
        sys_.cycle(client, risky, [command("right", "unlock")])
        risky = snap(9.0, rear_right_approach_risk=True)
        sys_.cycle(client, risky, advance_ms=8950)
        status = sys_.cycle(
            client, snap(9.05, rear_right_approach_risk=True), [command("all", "unlock")]
        )

    assert status["state"] == "OVERRIDE"
    assert status["reason_code"] == "approach_override_right"
    assert (status["lock_left"], status["lock_right"]) == ("RELEASE", "LOCK")


def test_it05_event_history_through_http_keeps_latest_100():
    """!@brief IT-05: controller↔event_store↔web, 101주기 후 최신 100건 오름차순 (SWR-012)."""
    sys_ = System()
    with TestClient(sys_.app) as client:
        for i in range(101):
            sys_.cycle(client, snap(0.05 * (i + 1)))
        events = client.get("/api/events").json()

    assert [e["event_id"] for e in events] == list(range(2, 102))


class FailingSink:
    """!@brief 기록에 실패하는 QM 이력 저장소 대역 (IT-06)."""

    def record(self, *args):
        """!@brief 항상 실패한다."""
        raise OSError("저장소 고장 주입")


def test_it06_qm_store_failure_does_not_affect_safety_outputs_over_http(caplog):
    """!@brief IT-06: QM 저장소 고장에도 판정·상태 조회가 정상 (SWA 10장)."""
    sys_ = System(sink=FailingSink())
    with TestClient(sys_.app) as client:
        status = sys_.cycle(client, snap(0.05, crash_status="CONFIRMED"))

    assert (status["lock_left"], status["lock_right"], status["state"]) == (
        "RELEASE",
        "RELEASE",
        "CRASH_RELEASE",
    )
    assert "이력 기록 실패" in caplog.text


def test_it07_step_execution_time_within_5_ms_budget():
    """!@brief IT-07: 평가 1회 실행 시간 최대 5 ms 이하 (SWA 7장 자원 예산)."""
    clock = ManualClock()
    controller = ChildLockController(clock, OverrideTracker(), EventStore())
    durations = []
    for i in range(1000):
        clock.advance_ms(50)
        controller.submit_snapshot(snap(clock.now(), rear_left_approach_risk=i % 2 == 0))
        controller.submit_command(command("all", "unlock"))
        controller.submit_command(command("left", "lock"))
        start = time.perf_counter()
        controller.step()
        durations.append(time.perf_counter() - start)

    assert max(durations) <= 0.005


def test_it08_running_system_creates_no_files(tmp_path, monkeypatch):
    """!@brief IT-08: 실행 중 작업 폴더에 파일을 만들지 않는다 (SWR-012 ④, 휘발성)."""
    monkeypatch.chdir(tmp_path)
    sys_ = System()
    with TestClient(sys_.app) as client:
        for i in range(20):
            sys_.cycle(client, snap(0.05 * (i + 1), fire_detected=i == 5), [command("all", "lock")])
        client.get("/api/events")

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(("confirm_offset_ms", "max_release_ms"), [(0, 300), (10, 300), (49, 300)])
def test_it09_crash_release_meets_300_ms_at_any_phase_of_cycle(confirm_offset_ms, max_release_ms):
    """!@brief IT-09: 주기 안 어느 시점에 CONFIRMED가 와도 300 ms 이내 RELEASE (SWR-007)."""
    clock = ManualClock()
    controller = ChildLockController(clock, OverrideTracker(), EventStore())
    controller.submit_snapshot(snap(0.0, vehicle_speed_kph=50.0))
    controller.step()
    clock.advance_ms(confirm_offset_ms)
    arrival = clock.now()
    controller.submit_snapshot(snap(arrival, crash_status="CONFIRMED"))
    while True:
        clock.advance_ms(50 - confirm_offset_ms if clock.now() == arrival else 50)
        status = controller.step()
        if status.lock_left is R and status.lock_right is R:
            break

    assert (clock.now() - arrival) * 1000 <= max_release_ms


def test_it10_degraded_within_100_ms_after_200_ms_silence():
    """!@brief IT-10: 200 ms 초과 무입력 후 100 ms 이내 DEGRADED (SWA 7장, SWR-013 ③)."""
    clock = ManualClock()
    controller = ChildLockController(clock, OverrideTracker(), EventStore())
    controller.submit_snapshot(snap(0.0))
    controller.step()
    first_degraded_ms = None
    while first_degraded_ms is None:
        clock.advance_ms(50)
        if controller.step().state is State.DEGRADED:
            first_degraded_ms = round(clock.now() * 1000)

    assert 200 < first_degraded_ms <= 300


def test_it11_replay_of_full_scenario_is_deterministic_1000_times():
    """!@brief IT-11: 전 규칙 시나리오 1,000회 재생 해시 동일 (SWR-016, OEM-NFR-001)."""
    steps = (
        ReplayStep(50, (snap(0.05),), (command("all", "lock"),)),
        ReplayStep(50, (snap(0.10, vehicle_speed_kph=3.0),), ()),
        ReplayStep(50, (snap(0.15, isofix_left=True),), (command("left", "unlock"),)),
        ReplayStep(50, (snap(0.20, fire_detected=True),), ()),
        ReplayStep(50, (snap(0.25, ignition_on=False),), ()),
        ReplayStep(50, (snap(0.30, rear_left_approach_risk=True),), (command("left", "unlock"),)),
        ReplayStep(50, (snap(0.35, sensor_fault=True),), ()),
        ReplayStep(50, (snap(0.40, crash_status="PENDING"),), ()),
        ReplayStep(50, (snap(0.45, crash_status="CONFIRMED"),), ()),
        ReplayStep(300, (), ()),
        ReplayStep(50, ({"bad": 1},), ({"side": "x"},)),
    )
    hashes = {result_hash(run(steps)) for _ in range(1000)}

    assert len(hashes) == 1
