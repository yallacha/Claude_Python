"""!
@brief 접근위험 억제 후 재입력 override 판정 (QM, SWD 6장, SWR-006).
@details 출력(잠금)은 다루지 않고 state·reason_code 주석만 만든다(AD-02, D-02).
"""

from dataclasses import dataclass

from childlock.model import OVERRIDE_WINDOW_MS, Decision, Door, State, to_ms


@dataclass(frozen=True)
class Annotation:
    """!@brief override 주석. 출력 필드가 없어 안전 출력을 바꿀 수 없다."""

    state: State | None
    reason_code: str | None


@dataclass
class _DoorTrack:
    """!@brief 도어별 override 추적 상태."""

    first_suppressed_ms: int | None = None
    active: bool = False


class OverrideTracker:
    """!@brief 도어별 첫 억제 시각을 기억해 10.0 s 이하 재입력을 override로 판정한다."""

    def __init__(self) -> None:
        """!@brief 두 도어의 추적 상태를 비운다."""
        self._tracks = {Door.LEFT: _DoorTrack(), Door.RIGHT: _DoorTrack()}

    def _update_door(self, door: Door, suppressed: bool, now_ms: int) -> bool:
        """!
        @brief 접근위험 중인 도어의 억제 기록을 갱신한다.
        @param door 대상 도어
        @param suppressed 이번 주기에 그 도어 해제 요청이 억제됐는지
        @param now_ms 평가 시각(ms)
        @return 이번 주기에 override가 새로 성립했으면 True
        """
        track = self._tracks[door]
        if not suppressed:
            return False
        first = track.first_suppressed_ms
        if first is not None and now_ms - first <= OVERRIDE_WINDOW_MS:
            track.active = True
            return True
        track.first_suppressed_ms = now_ms  # 새 첫 억제
        return False

    def annotate(
        self, decision: Decision, now_s: float, risk_left: bool, risk_right: bool
    ) -> Annotation:
        """!
        @brief 판정 결과에 override 주석을 만든다.
        @param decision ASIL B 판정 결과(출력은 이미 확정)
        @param now_s 평가 시각(초)
        @param risk_left 좌측 접근위험
        @param risk_right 우측 접근위험
        @return OVERRIDE 주석. decision.state가 NORMAL이 아니면 빈 주석
        """
        now_ms = to_ms(now_s)
        reason = None
        for door, risk in ((Door.LEFT, risk_left), (Door.RIGHT, risk_right)):
            if not risk:
                self._tracks[door] = _DoorTrack()  # 접근위험 해제 시 초기화 (SWR-006 ④)
                continue
            new = self._update_door(door, door in decision.suppressed_unlocks, now_ms)
            if new and reason is None:
                reason = f"approach_override_{door.value}"
        active = any(track.active for track in self._tracks.values())
        if not active or decision.state is not State.NORMAL:
            return Annotation(None, None)
        return Annotation(State.OVERRIDE, reason)
