"""!
@brief childlock.override 단위 시험 (SWD 6장, SWR-006).
"""

from childlock.model import Decision, Door, Lock, PriorityReason, State
from childlock.override import Annotation, OverrideTracker

NONE = Annotation(None, None)


def decision(suppressed=(), state=State.NORMAL):
    """!@brief 접근위험 판정 결과를 만든다. 출력은 annotate와 무관하다."""
    return Decision(
        lock_left=Lock.LOCK,
        lock_right=Lock.RELEASE,
        state=state,
        priority_reason=PriorityReason.APPROACH_RISK,
        reason_code="approach_risk_left",
        warning_code=None,
        crash_latched=False,
        suppressed_unlocks=tuple(suppressed),
    )


def press(tracker, now_s, door=Door.LEFT, risk_left=True, risk_right=False, state=State.NORMAL):
    """!@brief 해제 요청이 억제된 주기를 주석 처리한다."""
    return tracker.annotate(decision((door,), state), now_s, risk_left, risk_right)


def test_first_suppression_is_not_override():
    """!@brief 첫 억제는 override가 아니다."""
    assert press(OverrideTracker(), 1.0) == NONE


def test_second_request_at_exactly_10_s_is_override():
    """!@brief 첫 억제 후 10.0 s(경계값)에 재입력하면 override (SWR-006 ①)."""
    tracker = OverrideTracker()
    press(tracker, 1.0)

    assert press(tracker, 11.0) == Annotation(State.OVERRIDE, "approach_override_left")


def test_second_request_after_10_001_s_starts_new_window():
    """!@brief 10.001 s 후 재입력은 새 첫 억제다 (SWR-006 ②)."""
    tracker = OverrideTracker()
    press(tracker, 1.0)

    assert press(tracker, 11.001) == NONE
    assert press(tracker, 12.0) == Annotation(State.OVERRIDE, "approach_override_left")


def test_accumulated_float_time_at_10_s_is_override():
    """!@brief 0.05 s × 200 누적 시각(부동소수 오차)에서도 10.0 s 이하로 판정 (DD-C02)."""
    tracker = OverrideTracker()
    press(tracker, 0.0)
    now = 0.0
    for _ in range(200):
        now += 0.05

    assert press(tracker, now).state is State.OVERRIDE


def test_request_on_other_door_is_not_override():
    """!@brief 우측 억제 후 좌측 재입력은 override가 아니다 (SWR-006 ③)."""
    tracker = OverrideTracker()
    press(tracker, 1.0, Door.RIGHT, risk_left=True, risk_right=True)

    assert press(tracker, 2.0, Door.LEFT, risk_left=True, risk_right=True) == NONE


def test_override_state_persists_while_risk_and_ends_when_risk_clears():
    """!@brief override는 접근위험 동안 유지되고 false가 되면 끝난다 (SWR-006 ④)."""
    tracker = OverrideTracker()
    press(tracker, 1.0)
    press(tracker, 2.0)

    assert tracker.annotate(decision(), 2.05, True, False) == Annotation(State.OVERRIDE, None)
    assert tracker.annotate(decision(), 2.10, False, False) == NONE


def test_risk_clearing_resets_first_suppression():
    """!@brief 접근위험이 풀리면 이전 억제 기록을 지운다."""
    tracker = OverrideTracker()
    press(tracker, 1.0)
    tracker.annotate(decision(), 1.5, False, False)

    assert press(tracker, 2.0) == NONE


def test_higher_state_is_not_overwritten():
    """!@brief decision.state가 NORMAL이 아니면 주석을 붙이지 않는다 (SWA 6.1)."""
    tracker = OverrideTracker()
    press(tracker, 1.0)

    assert press(tracker, 2.0, state=State.OFF) == NONE


def test_annotation_has_no_output_fields():
    """!@brief 주석에는 출력(lock) 필드가 없다 (AD-02 간섭 배제)."""
    assert set(Annotation.__dataclass_fields__) == {"state", "reason_code"}
