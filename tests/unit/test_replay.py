"""!
@brief childlock.replay 단위 시험 (SWD 10장, SWR-016).
"""

import json

from childlock.model import Lock, State
from childlock.replay import ReplayStep, load_vector, result_hash, run


def snapshot(ts, **overrides):
    """!@brief 정지·시동 ON 원시 입력."""
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


VECTOR = (
    ReplayStep(50, (snapshot(0.05),), ({"side": "all", "action": "lock", "source": "avn"},)),
    ReplayStep(50, (snapshot(0.10, rear_left_approach_risk=True),), ()),
    ReplayStep(300, (), ()),  # 입력 끊김 → DEGRADED
)


def test_run_applies_steps_in_order_with_advancing_clock():
    """!@brief 단계마다 시계를 전진하고 평가해 상태와 이벤트를 돌려준다."""
    result = run(VECTOR)

    assert [s.lock_left for s in result.statuses] == [Lock.LOCK, Lock.LOCK, Lock.LOCK]
    assert result.statuses[-1].state is State.DEGRADED
    assert [e.event_id for e in result.events] == [1, 2, 3]


def test_same_vector_gives_same_hash_every_time():
    """!@brief 같은 벡터를 반복 재생하면 해시가 같다 (SWR-016)."""
    hashes = {result_hash(run(VECTOR)) for _ in range(20)}

    assert len(hashes) == 1


def test_changing_one_input_changes_the_hash():
    """!@brief 입력 하나가 달라지면 해시도 달라진다(해시가 결과를 반영함)."""
    changed = (VECTOR[0], ReplayStep(50, (snapshot(0.10, isofix_right=True),), ()), VECTOR[2])

    assert result_hash(run(changed)) != result_hash(run(VECTOR))


def test_hash_is_sha256_hex():
    """!@brief 해시는 SHA-256 16진 문자열(64자)이다."""
    digest = result_hash(run(VECTOR))

    assert len(digest) == 64
    assert int(digest, 16) >= 0


def test_load_vector_reads_json_file(tmp_path):
    """!@brief JSON 벡터 파일을 ReplayStep 목록으로 읽는다."""
    path = tmp_path / "vector.json"
    data = [
        {"advance_ms": 50, "snapshots": [snapshot(0.05)], "commands": []},
        {"advance_ms": 100},
    ]
    path.write_text(json.dumps(data), encoding="utf-8")

    steps = load_vector(path)

    assert steps == (
        ReplayStep(50, (snapshot(0.05),), ()),
        ReplayStep(100, (), ()),
    )
