"""!
@brief childlock.web 단위 시험 (SWD 11장, SWR-014·015·023).
"""

import time

import pytest
from fastapi.testclient import TestClient

from childlock.clock import ManualClock, MonotonicClock
from childlock.controller import ChildLockController
from childlock.event_store import EventStore
from childlock.override import OverrideTracker
from childlock.web import __main__ as web_main
from childlock.web import create_app

STATUS_FIELDS = {
    "lock_left",
    "lock_right",
    "state",
    "input_validity",
    "priority_reason",
    "reason_code",
    "warning_code",
}
SNAPSHOT = {
    "source_timestamp_s": 0.0,
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
    "sensor_fault": True,
}


def make_app(clock=None, run_loop=False):
    """!@brief 실제 컴포넌트(controller와 같은 시계·이력 저장소)로 앱을 만든다."""
    clock = clock or ManualClock()
    store = EventStore()
    controller = ChildLockController(clock, OverrideTracker(), store)
    return create_app(controller, store, clock, run_loop=run_loop)


def test_stamped_snapshot_uses_server_receive_time():
    """!@brief 화면 입력(?stamp=true)은 서버 수신 시각으로 시각을 채워 fresh로 판정된다."""
    clock = ManualClock(start_ms=5000)
    with TestClient(make_app(clock)) as c:
        body = {k: v for k, v in SNAPSHOT.items() if k != "source_timestamp_s"}
        c.post("/api/snapshot?stamp=true", json=body)
        clock.advance_ms(50)
        status = c.post("/api/step").json()
        events = c.get("/api/events").json()

    assert status["input_validity"] == "VALID"
    assert events[-1]["timestamp_s"] == 5.0


def test_stamp_requires_json_object():
    """!@brief stamp 요청 본문이 객체가 아니면 422로 거절한다."""
    with TestClient(make_app()) as c:
        assert c.post("/api/snapshot?stamp=true", json=[1, 2]).status_code == 422


@pytest.fixture
def client():
    """!@brief 주기 루프 없이(수동 평가) 동작하는 시험 클라이언트."""
    with TestClient(make_app()) as c:
        yield c


def test_status_has_all_display_fields_as_plain_values(client):
    """!@brief 상태 조회 응답에 7개 필드가 문자열 값으로 있다 (SWR-014)."""
    response = client.get("/api/status")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == STATUS_FIELDS
    assert (body["lock_left"], body["state"], body["input_validity"]) == (
        "RELEASE",
        "OFF",
        "NO_DATA",
    )


def test_submitted_inputs_are_reflected_after_manual_step(client):
    """!@brief 입력 제출 → 평가 → 상태 조회 결과가 직전 평가와 같다 (SWR-014)."""
    assert client.post("/api/snapshot", json=SNAPSHOT).status_code == 202
    assert (
        client.post(
            "/api/command", json={"side": "all", "action": "lock", "source": "avn"}
        ).status_code
        == 202
    )

    stepped = client.post("/api/step").json()

    assert stepped == client.get("/api/status").json()
    assert stepped["state"] == "FAULT"
    assert stepped["warning_code"] == "W_SENSOR_FAULT"
    assert stepped["priority_reason"] == "sensor_fault"


def test_events_are_listed_in_ascending_id_order(client):
    """!@brief 이력 조회는 event_id 오름차순 JSON 목록이다 (SWR-012)."""
    client.post("/api/step")
    client.post("/api/step")

    events = client.get("/api/events").json()

    assert [e["event_id"] for e in events] == [1, 2]
    assert events[0]["state"] == "OFF"


def test_malformed_json_is_rejected_with_422(client):
    """!@brief JSON 구문 오류 본문은 422로 거절하고 controller에 넘기지 않는다 (SWA 8장)."""
    response = client.post(
        "/api/snapshot", content=b"{not json", headers={"content-type": "application/json"}
    )

    assert response.status_code == 422
    client.post("/api/step")
    assert client.get("/api/status").json()["input_validity"] == "NO_DATA"


def test_malformed_command_json_is_rejected_with_422(client):
    """!@brief 명령 본문 JSON 구문 오류도 422로 거절하고 controller에 넘기지 않는다."""
    response = client.post(
        "/api/command", content=b"{side:", headers={"content-type": "application/json"}
    )

    assert response.status_code == 422
    assert client.post("/api/step").json()["reason_code"] == "no_change"


class BrokenStatusController:
    """!@brief 직렬화할 수 없는 상태를 돌려주는 대역 (SWR-015 오류 주입)."""

    def status(self):
        """!@brief 상태 대신 직렬화 불가 객체."""
        return object()


def test_serialization_failure_returns_http_500():
    """!@brief 상태를 직렬화하지 못하면 HTTP 500 (SWR-015 ②)."""
    app = create_app(BrokenStatusController(), EventStore(), ManualClock(), run_loop=False)
    with TestClient(app) as c:
        response = c.get("/api/status")

    assert response.status_code == 500
    assert response.json() == {"error": "serialization_failed"}


def test_index_page_shows_every_status_field(client):
    """!@brief 화면에 상태 7개 필드 표시 영역이 있다 (SWR-015 ①)."""
    page = client.get("/")

    assert page.status_code == 200
    for field in STATUS_FIELDS:
        assert f'id="{field}"' in page.text


def test_manual_step_is_refused_while_cycle_loop_runs():
    """!@brief 주기 루프가 도는 동안 수동 평가는 409로 거절한다."""
    with TestClient(make_app(MonotonicClock(), run_loop=True)) as c:
        assert c.post("/api/step").status_code == 409


def test_cycle_loop_evaluates_periodically():
    """!@brief 주기 루프가 50 ms마다 평가한다 (SWR-023, 실제 시계·느슨한 하한)."""
    with TestClient(make_app(MonotonicClock(), run_loop=True)) as c:
        time.sleep(0.3)
        count = len(c.get("/api/events").json())

    assert 3 <= count <= 8


def test_main_serves_app_on_localhost(monkeypatch):
    """!@brief 실행 진입점은 127.0.0.1:8000에서 앱을 띄운다."""
    calls = {}
    monkeypatch.setattr(web_main.uvicorn, "run", lambda app, **kw: calls.update(app=app, **kw))

    web_main.main()

    assert (calls["host"], calls["port"]) == ("127.0.0.1", 8000)
    assert calls["app"].title == "Childlock PC/SIL Simulator"
