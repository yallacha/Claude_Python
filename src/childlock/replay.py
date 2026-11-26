"""!
@brief 입력 벡터 재생과 결과 해시 (QM, SWD 10장, SWR-016).
@details 고정 시계(ManualClock)로 새 controller를 만들어 벡터를 재생한다.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from childlock.clock import ManualClock
from childlock.controller import ChildLockController
from childlock.event_store import EventStore
from childlock.model import Event, Status
from childlock.override import OverrideTracker


@dataclass(frozen=True)
class ReplayStep:
    """!@brief 재생 단계 하나: 시계 전진 후 입력 제출, 평가 1회."""

    advance_ms: int
    snapshots: tuple = ()
    commands: tuple = ()


@dataclass(frozen=True)
class ReplayResult:
    """!@brief 재생 결과: 평가마다의 상태와 최종 이벤트 이력."""

    statuses: tuple[Status, ...]
    events: tuple[Event, ...]


def run(steps: tuple[ReplayStep, ...]) -> ReplayResult:
    """!
    @brief 초기 상태에서 벡터를 재생한다.
    @param steps 재생 단계 목록
    @return 공개 결과(상태 목록, 이벤트 목록)
    """
    clock = ManualClock()
    store = EventStore()
    controller = ChildLockController(clock, OverrideTracker(), store)
    statuses = []
    for step in steps:
        clock.advance_ms(step.advance_ms)
        for raw in step.snapshots:
            controller.submit_snapshot(raw)
        for raw in step.commands:
            controller.submit_command(raw)
        statuses.append(controller.step())
    return ReplayResult(tuple(statuses), store.list_events())


def _plain(value: object) -> object:
    """!@brief JSON 직렬화용 변환: Enum은 값 문자열로. @return 변환 값"""
    return value.value if isinstance(value, Enum) else value


def result_hash(result: ReplayResult) -> str:
    """!
    @brief 공개 결과의 SHA-256 해시를 계산한다. 키 정렬 JSON으로 만들어 순서에 흔들리지 않는다.
    @param result 재생 결과
    @return 16진 문자열 64자
    """
    payload = {
        "statuses": [{k: _plain(v) for k, v in asdict(s).items()} for s in result.statuses],
        "events": [{k: _plain(v) for k, v in asdict(e).items()} for e in result.events],
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_vector(path: Path | str) -> tuple[ReplayStep, ...]:
    """!
    @brief JSON 벡터 파일을 읽는다. 각 항목은 advance_ms, snapshots(선택), commands(선택)를 가진다.
    @param path 파일 경로(UTF-8)
    @return 재생 단계 목록
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(
        ReplayStep(
            int(item["advance_ms"]),
            tuple(item.get("snapshots", ())),
            tuple(item.get("commands", ())),
        )
        for item in data
    )
