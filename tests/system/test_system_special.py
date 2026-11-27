"""!
@brief 실행 벡터가 없는 시스템 시험 케이스 (SWE.6, 사양서 ID별).
@details TC-NF-003~014(이력·결정론), TC-F-093~096(Web). TC-F-095의 화면 육안 확인은 수동 항목이며
    여기서는 표시 영역과 API 값 일치만 자동 확인한다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from vector_runner import DEFAULT_SNAPSHOT, VectorSystem, combined_vector, replay_hash

import childlock.web as web
from childlock.clock import ManualClock
from childlock.controller import ChildLockController
from childlock.event_store import EventStore
from childlock.override import OverrideTracker

ROOT = Path(__file__).resolve().parents[2]
EVENT_FIELDS = {
    "event_id",
    "timestamp_s",
    "state",
    "lock_left",
    "lock_right",
    "priority_reason",
    "reason_code",
    "input_validity",
}
STATUS_FIELDS = {
    "lock_left",
    "lock_right",
    "state",
    "input_validity",
    "priority_reason",
    "reason_code",
    "warning_code",
}
CMD = {"side": "all", "action": "lock", "source": "avn"}


def events_of(system: VectorSystem) -> list[dict]:
    """!@brief 시스템의 이력을 JSON 값으로. @return 이벤트 목록"""
    return [web.serialize_event(e) for e in system.store.list_events()]


def evaluate(system: VectorSystem, count: int, **snapshot) -> None:
    """!@brief 50 ms 간격으로 기본값(+변경) 입력을 count번 평가한다."""
    for _ in range(count):
        system.play({"advance_ms": 50, "snapshot": snapshot})


def run_in_new_process(code: str, env_extra: dict | None = None) -> str:
    """!
    @brief 새 Python 프로세스에서 코드를 실행한다(재기동·환경 변수 시험용).
    @return 표준 출력
    """
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(Path(__file__).parent)]),
    }
    env.update(env_extra or {})
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, env=env
    )
    return result.stdout.strip()


# ---- SWR-010 결정 이벤트 ID ----


def test_tc_nf_003_event_ids_1_to_5_for_5_evaluations():
    """!@brief TC-NF-003: 입력 종류와 무관하게 평가 5회 → event_id 1~5."""
    s = VectorSystem()
    s.play({"advance_ms": 50})
    s.play({"advance_ms": 50, "snapshot": {}})
    s.play({"advance_ms": 50, "snapshot": {"vehicle_speed_kph": 300.1}})
    s.play({"advance_ms": 50, "snapshot": {}, "commands": [CMD]})
    s.play({"advance_ms": 50})

    assert [e["event_id"] for e in events_of(s)] == [1, 2, 3, 4, 5]


RESTART_CODE = """
import json, sys
from vector_runner import VectorSystem
import childlock.web as web
s = VectorSystem()
for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else {n}):
    s.play({{"advance_ms": 50, "snapshot": {{}}}})
print(json.dumps([web.serialize_event(e)["event_id"] for e in s.store.list_events()]))
"""


def test_tc_nf_004_event_id_restarts_at_1_after_process_restart():
    """!@brief TC-NF-004: 평가 3회 프로세스 종료 후 재기동, 평가 1회 → 이력 1건, id 1."""
    first = json.loads(run_in_new_process(RESTART_CODE.format(n=3)))
    second = json.loads(run_in_new_process(RESTART_CODE.format(n=1)))

    assert first == [1, 2, 3]
    assert second == [1]


def test_tc_nf_005_one_event_per_evaluation_regardless_of_command_count():
    """!@brief TC-NF-005: 한 주기 명령 3건 + 이후 평가 1회 → 이력 2건(id 1, 2)."""
    s = VectorSystem()
    commands = [
        {"side": "left", "action": "lock", "source": "avn"},
        {"side": "right", "action": "lock", "source": "avn"},
        {"side": "all", "action": "unlock", "source": "avn"},
    ]
    s.play({"advance_ms": 50, "snapshot": {}, "commands": commands})
    s.play({"advance_ms": 50})

    assert [e["event_id"] for e in events_of(s)] == [1, 2]


# ---- SWR-011 허용 필드 ----


def test_tc_nf_006_events_have_only_allowed_fields_and_input_timestamp():
    """!@brief TC-NF-006: 6종 입력 후 모든 이벤트 키 = 허용 8개, source 없음, 시각 = 입력 시각."""
    s = VectorSystem()
    for source in ("physical_button", "avn", "voice", "mobile_app"):
        command = {"side": "left", "action": "lock", "source": source}
        s.play({"advance_ms": 50, "snapshot": {"source_timestamp_s": 0.04}, "commands": [command]})
    s.play({"advance_ms": 50, "snapshot": {"vehicle_speed_kph": 300.1}})
    s.play({"advance_ms": 300})
    s.play({"advance_ms": 50, "snapshot": {"sensor_fault": True}})
    s.play({"advance_ms": 50, "snapshot": {"crash_status": "CONFIRMED"}})
    events = events_of(s)

    assert all(set(e) == EVENT_FIELDS for e in events)
    text = json.dumps(events)
    assert not any(src in text for src in ("physical_button", "avn", "voice", "mobile_app"))
    assert events[0]["timestamp_s"] == 0.04


def test_tc_nf_007_personal_data_in_extra_fields_is_never_stored():
    """!@brief TC-NF-007 [제안]: 입력 추가 필드의 개인정보 값이 이력에 없다."""
    s = VectorSystem()
    personal = {"user_name": "홍길동", "phone": "010-0000-0000", "device_id": "DEV-123"}
    command = {**CMD, "account": "user01"}
    s.play({"advance_ms": 50, "snapshot": personal, "commands": [command]})
    events = events_of(s)
    text = json.dumps(events, ensure_ascii=False)

    assert all(set(e) == EVENT_FIELDS for e in events)
    assert not any(v in text for v in ("홍길동", "010-0000-0000", "DEV-123", "user01"))


# ---- SWR-012 용량·휘발성 ----


def test_tc_nf_008_history_99_then_100_events():
    """!@brief TC-NF-008: 99회 → 99건(1~99), 100회 → 100건(1~100) 오름차순."""
    s = VectorSystem()
    evaluate(s, 99)
    assert [e["event_id"] for e in events_of(s)] == list(range(1, 100))
    evaluate(s, 1)

    assert [e["event_id"] for e in events_of(s)] == list(range(1, 101))


@pytest.mark.parametrize(("count", "first_id"), [(101, 2), (250, 151)])
def test_tc_nf_009_012_history_keeps_latest_100(count, first_id):
    """!@brief TC-NF-009(101회 → 2~101), TC-NF-012 [제안](250회 → 151~250)."""
    s = VectorSystem()
    evaluate(s, count)

    assert [e["event_id"] for e in events_of(s)] == list(range(first_id, count + 1))


def test_tc_nf_010_history_is_empty_after_process_restart():
    """!@brief TC-NF-010: 평가 5회 후 프로세스 재기동 → 이력 0건."""
    assert json.loads(run_in_new_process(RESTART_CODE.format(n=5))) == [1, 2, 3, 4, 5]
    assert json.loads(run_in_new_process(RESTART_CODE.format(n=0))) == []


def test_tc_nf_011_no_files_created_during_101_evaluations(tmp_path, monkeypatch):
    """!@brief TC-NF-011: 빈 작업 폴더에서 평가 101회 전후 파일 목록(재귀)이 같다."""
    monkeypatch.chdir(tmp_path)
    before = sorted(p for p in tmp_path.rglob("*") if "__pycache__" not in p.parts)
    evaluate(VectorSystem(), 101)
    after = sorted(p for p in tmp_path.rglob("*") if "__pycache__" not in p.parts)

    assert before == after == []


# ---- SWR-016 결정론 ----


def test_tc_nf_013_combined_vector_1000_replays_single_hash():
    """!@brief TC-NF-013: 사양서 기능 케이스 벡터를 이어 붙인 V를 1,000회 재생 → 고유 해시 1개."""
    steps = combined_vector()
    assert len(steps) > 300  # 모든 규칙을 거치는 충분한 길이

    assert len({replay_hash(steps) for _ in range(1000)}) == 1


HASH_CODE = (
    "from vector_runner import combined_vector, replay_hash; print(replay_hash(combined_vector()))"
)


@pytest.mark.parametrize("seed", ["0", "1", "random"])
@pytest.mark.parametrize("tz", ["UTC", "Asia/Seoul"])
def test_tc_nf_014_hash_independent_of_hashseed_and_timezone(seed, tz):
    """!@brief TC-NF-014 [제안]: PYTHONHASHSEED·TZ 6조합 별도 프로세스 해시 = 기준 해시."""
    expected = replay_hash(combined_vector())

    assert run_in_new_process(HASH_CODE, {"PYTHONHASHSEED": seed, "TZ": tz}) == expected


# ---- SWR-014, SWR-015 Web ----


def manual_client():
    """!@brief 수동 평가 Web 시험 대상. @return (TestClient, 시계)"""
    clock = ManualClock()
    store = EventStore()
    controller = ChildLockController(clock, OverrideTracker(), store)
    return TestClient(web.create_app(controller, store, clock, run_loop=False)), clock


def post_cycle(client, clock, **snapshot):
    """!@brief 50 ms 전진 후 기본값(+변경) 입력을 HTTP로 보내고 평가한다."""
    clock.advance_ms(50)
    client.post(
        "/api/snapshot", json={"source_timestamp_s": clock.now(), **DEFAULT_SNAPSHOT, **snapshot}
    )
    return client.post("/api/step").json()


def test_tc_f_093_status_query_reports_latest_evaluation():
    """!@brief TC-F-093: 기동 직후·정상·센서 고장·충돌 확정 후 상태 조회."""
    client, clock = manual_client()
    with client:
        initial = client.get("/api/status").json()
        post_cycle(client, clock)
        normal = client.get("/api/status").json()
        post_cycle(client, clock, sensor_fault=True)
        fault = client.get("/api/status").json()
        post_cycle(client, clock, crash_status="CONFIRMED")
        crash = client.get("/api/status").json()

    assert set(initial) == STATUS_FIELDS
    assert (initial["lock_left"], initial["state"], initial["input_validity"]) == (
        "RELEASE",
        "OFF",
        "NO_DATA",
    )
    assert initial["warning_code"] is None
    assert (normal["state"], normal["input_validity"], normal["warning_code"]) == (
        "NORMAL",
        "VALID",
        None,
    )
    assert (fault["state"], fault["warning_code"], fault["reason_code"]) == (
        "FAULT",
        "W_SENSOR_FAULT",
        "sensor_fault",
    )
    assert (crash["state"], crash["reason_code"]) == ("CRASH_RELEASE", "crash_confirmed")


def test_tc_f_094_status_query_has_no_side_effect():
    """!@brief TC-F-094 [제안]: 상태 조회 3회 응답 같음, 이력 건수 변화 없음."""
    client, clock = manual_client()
    with client:
        post_cycle(client, clock)
        before = len(client.get("/api/events").json())
        responses = [client.get("/api/status").json() for _ in range(3)]
        after = len(client.get("/api/events").json())

    assert responses[0] == responses[1] == responses[2]
    assert before == after == 1


def test_tc_f_095_display_fields_present_and_api_values_per_scenario():
    """!@brief TC-F-095(자동 부분): 표시 영역 7개, 세 시나리오 API 값. 육안 확인은 수동."""
    client, clock = manual_client()
    with client:
        page = client.get("/").text
        a = post_cycle(client, clock)
        b = post_cycle(client, clock, vehicle_speed_kph=50.0)
        c = post_cycle(client, clock, sensor_fault=True)

    assert all(f'id="{field}"' in page for field in STATUS_FIELDS)
    assert (a["lock_left"], a["lock_right"], a["state"], a["input_validity"]) == (
        "RELEASE",
        "RELEASE",
        "NORMAL",
        "VALID",
    )
    assert (b["lock_left"], b["lock_right"], b["reason_code"]) == (
        "LOCK",
        "LOCK",
        "auto_lock_speed",
    )
    assert (c["state"], c["reason_code"]) == ("FAULT", "sensor_fault")


def test_tc_f_096_serialization_failure_returns_500_then_recovers(monkeypatch):
    """!@brief TC-F-096: 직렬화기 고장 주입 → HTTP 500, 원복 후 200."""
    client, _ = manual_client()

    def broken(status):
        raise TypeError("직렬화 고장 주입")

    with client:
        monkeypatch.setattr(web, "serialize_status", broken)
        failed = client.get("/api/status")
        monkeypatch.undo()
        recovered = client.get("/api/status")

    assert failed.status_code == 500
    assert recovered.status_code == 200
