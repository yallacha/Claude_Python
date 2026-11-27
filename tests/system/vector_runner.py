"""!
@brief 시스템 시험 실행 벡터 재생 도구 (SWE.6 시험 하네스).
@details 사양서 입력(docs/06_system_test/stc_testcases.json)의 vector를 고정 시계로 재생한다.
    별도 프로세스(TC-NF-004·010·014)에서도 쓰므로 pytest에 의존하지 않는다.
"""

import hashlib
import json
from pathlib import Path

from childlock.clock import ManualClock
from childlock.controller import ChildLockController
from childlock.event_store import EventStore
from childlock.override import OverrideTracker
from childlock.web import serialize_event, serialize_status

SPEC = Path(__file__).resolve().parents[2] / "docs" / "06_system_test" / "stc_testcases.json"
DEFAULT_SNAPSHOT = {
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


def load_cases() -> list[dict]:
    """!@brief 사양서 입력의 전체 시험 케이스. @return 케이스 목록(파일 없으면 빈 목록)"""
    if not SPEC.exists():
        return []
    return json.loads(SPEC.read_text(encoding="utf-8"))["test_cases"]


def snapshot_for(step: dict, now_s: float) -> dict | None:
    """!
    @brief 단계의 차량 입력을 만든다. snapshot은 기본값에 덮어쓰고, snapshot_raw는 그대로 쓴다.
    @param step 벡터 단계
    @param now_s 제출 시각(source_timestamp_s 생략 시 사용)
    @return 제출할 원시 입력, 없으면 None
    """
    if "snapshot_raw" in step:
        return step["snapshot_raw"]
    if "snapshot" not in step:
        return None
    return {"source_timestamp_s": now_s, **DEFAULT_SNAPSHOT, **step["snapshot"]}


class VectorSystem:
    """!@brief 고정 시계로 구동하는 시험 대상 시스템 하나."""

    def __init__(self) -> None:
        """!@brief 초기 상태 시스템을 만든다."""
        self.clock = ManualClock()
        self.store = EventStore()
        self.controller = ChildLockController(self.clock, OverrideTracker(), self.store)

    def play(self, step: dict) -> dict:
        """!
        @brief 벡터 단계 하나를 실행한다.
        @param step 벡터 단계
        @return 평가 후 상태(JSON 값)
        """
        self.clock.advance_ms(int(step.get("advance_ms", 0)))
        snapshot = snapshot_for(step, self.clock.now())
        if snapshot is not None:
            self.controller.submit_snapshot(snapshot)
        for command in step.get("commands", []):
            self.controller.submit_command(command)
        return serialize_status(self.controller.step())


def run_vector(vector: dict) -> list[tuple[int, dict, dict]]:
    """!
    @brief 벡터를 새 시스템에서 재생하고 기대값이 있는 단계의 (번호, 기대, 실제)를 돌려준다.
    @param vector {"steps": [...]}
    @return 비교 목록
    """
    system = VectorSystem()
    results = []
    for index, step in enumerate(vector["steps"], 1):
        actual = system.play(step)
        if step.get("expect"):
            results.append((index, step["expect"], actual))
    return results


def combined_vector() -> list[dict]:
    """!
    @brief 사양서의 기능 케이스 벡터를 모두 이어 붙인 결정론 시험 벡터 V (TC-NF-013·014).
    @return 단계 목록
    """
    steps: list[dict] = []
    for case in load_cases():
        if case["id"].startswith("TC-F-") and case.get("vector"):
            steps.extend(case["vector"]["steps"])
    return steps


def replay_hash(steps: list[dict]) -> str:
    """!
    @brief 한 시스템에서 단계들을 재생한 공개 결과(상태 목록+이력)의 SHA-256.
    @param steps 단계 목록
    @return 16진 해시
    """
    system = VectorSystem()
    statuses = [system.play(step) for step in steps]
    events = [serialize_event(e) for e in system.store.list_events()]
    text = json.dumps({"statuses": statuses, "events": events}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
