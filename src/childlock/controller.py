"""!
@brief 평가 조율 (ASIL B, SWD 9장, SWR-013·023·024).
@details 평가 1회(step): 입력 검증 → freshness → 판정 → override 주석(QM)
    → 상태 확정 → 이력 기록(QM).
    출력은 판정(decide) 결과로 확정되며 QM 단계는 출력을 바꿀 수 없다(AD-02).
    QM 컴포넌트는 주입된 프로토콜 객체로만 호출하고 구현 모듈을 import하지 않는다(SWA 4.2).
"""

import logging
from typing import Protocol

from childlock.clock import Clock
from childlock.decision import decide
from childlock.freshness import is_stale
from childlock.model import (
    INITIAL_STATE,
    INITIAL_STATUS,
    ControllerState,
    Decision,
    DriverCommand,
    InputValidity,
    PriorityReason,
    State,
    Status,
    Valid,
    VehicleSnapshot,
)
from childlock.validation import parse_command, parse_snapshot

_log = logging.getLogger(__name__)


class AnnotationLike(Protocol):
    """!@brief override 주석 형태: state와 reason_code만 가진다."""

    state: State | None
    reason_code: str | None


class OverrideAnnotator(Protocol):
    """!@brief override 주석 인터페이스 (QM 구현: override.OverrideTracker)."""

    def annotate(
        self, decision: Decision, now_s: float, risk_left: bool, risk_right: bool
    ) -> AnnotationLike:
        """!@brief 판정 결과에 대한 주석을 돌려준다."""
        ...  # pragma: no cover - 프로토콜 선언, 실행되지 않음


class EventSink(Protocol):
    """!@brief 결정 이력 기록 인터페이스 (QM 구현: event_store.EventStore)."""

    def record(self, status: Status, timestamp_s: float) -> None:
        """!@brief 상태 한 건을 기록한다."""
        ...  # pragma: no cover - 프로토콜 선언, 실행되지 않음


class ChildLockController:
    """!@brief 50 ms마다 step()이 호출되는 차일드락 제어기."""

    def __init__(self, clock: Clock, annotator: OverrideAnnotator, sink: EventSink) -> None:
        """!
        @brief 초기 상태(RELEASE, OFF, NO_DATA)로 만든다 (SWR-024).
        @param clock 시계
        @param annotator override 주석기(QM)
        @param sink 결정 이력 기록기(QM)
        """
        self._clock = clock
        self._annotator = annotator
        self._sink = sink
        self._state: ControllerState = INITIAL_STATE
        self._status: Status = INITIAL_STATUS
        self._last_valid: VehicleSnapshot | None = None
        self._pending_snapshots: list[object] = []
        self._pending_commands: list[object] = []

    def submit_snapshot(self, raw: object) -> None:
        """!@brief 차량 입력을 접수한다. 검증은 다음 step에서 한다. @param raw 원시 입력"""
        self._pending_snapshots.append(raw)

    def submit_command(self, raw: object) -> None:
        """!@brief 운전자 명령을 접수한다. 검증은 다음 step에서 한다. @param raw 원시 입력"""
        self._pending_commands.append(raw)

    def status(self) -> Status:
        """!@brief 최신 평가 결과 (SWR-014). @return 상태"""
        return self._status

    def _ingest_snapshots(self) -> bool:
        """!
        @brief 이번 주기 차량 입력을 받은 순서대로 검증하고 마지막 유효 입력을 보관한다.
        @return 마지막으로 받은 입력이 무효였으면 True (REV-D-03)
        """
        last_invalid = False
        for raw in self._pending_snapshots:
            result = parse_snapshot(raw)
            last_invalid = not isinstance(result, Valid)
            if isinstance(result, Valid):
                self._last_valid = result.value
        self._pending_snapshots.clear()
        return last_invalid

    def _ingest_commands(self) -> tuple[tuple[DriverCommand, ...], bool]:
        """!
        @brief 이번 주기 운전자 명령을 검증한다. 무효 명령은 버린다 (SWR-013 ②).
        @return (유효 명령 목록, 무효 명령 존재 여부)
        """
        results = [parse_command(raw) for raw in self._pending_commands]
        self._pending_commands.clear()
        valid = tuple(r.value for r in results if isinstance(r, Valid))
        return valid, len(valid) != len(results)

    def _validity(self, now_s: float, cycle_invalid: bool) -> InputValidity:
        """!
        @brief 이번 주기 입력 유효성을 정한다 (SWD 9 표).
        @param now_s 평가 시각
        @param cycle_invalid 이번 주기 마지막 입력이 무효였는지
        @return INVALID > NO_DATA > STALE > VALID 중 첫 일치
        """
        if cycle_invalid:
            return InputValidity.INVALID
        if self._last_valid is None:
            return InputValidity.NO_DATA
        if is_stale(now_s, self._last_valid.source_timestamp_s):
            return InputValidity.STALE
        return InputValidity.VALID

    def _annotate(self, decision: Decision, now_s: float) -> AnnotationLike | None:
        """!
        @brief override 주석을 얻는다. QM 예외는 기록만 하고 무시한다 (SWA 10장).
        @return 주석, 실패하면 None
        """
        snap = self._last_valid
        risk_left = bool(snap and snap.rear_left_approach_risk)
        risk_right = bool(snap and snap.rear_right_approach_risk)
        try:
            return self._annotator.annotate(decision, now_s, risk_left, risk_right)
        except Exception:  # QM 고장이 안전 판정을 멈추지 않게 한다
            _log.exception("override 주석 실패: 판정 출력은 유지")
            return None

    def _record(self, status: Status, now_s: float) -> None:
        """!@brief 이력을 기록한다. QM 예외는 기록만 하고 무시한다 (SWA 10장)."""
        timestamp = self._last_valid.source_timestamp_s if self._last_valid else now_s
        try:
            self._sink.record(status, timestamp)
        except Exception:  # QM 고장이 평가 주기를 멈추지 않게 한다
            _log.exception("이력 기록 실패: 평가 결과는 유지")

    def step(self) -> Status:
        """!
        @brief 평가 1회를 실행한다 (SWR-023).
        @return 이번 평가의 상태
        """
        now = self._clock.now()
        cycle_invalid = self._ingest_snapshots()
        commands, command_invalid = self._ingest_commands()
        validity = self._validity(now, cycle_invalid)
        decision = decide(self._last_valid, commands, self._state, validity)
        annotation = self._annotate(decision, now)
        reason = decision.reason_code
        if command_invalid and decision.priority_reason is PriorityReason.HOLD:
            reason = "command_invalid"
        status = Status(
            lock_left=decision.lock_left,  # 출력은 판정 값 그대로 (AD-02)
            lock_right=decision.lock_right,
            state=(annotation and annotation.state) or decision.state,
            input_validity=validity,
            priority_reason=decision.priority_reason,
            reason_code=(annotation and annotation.reason_code) or reason,
            warning_code=decision.warning_code,
        )
        self._state = ControllerState(
            decision.lock_left, decision.lock_right, decision.state, decision.crash_latched
        )
        self._status = status
        self._record(status, now)
        return status
