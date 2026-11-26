"""!
@brief 판정 엔진 (ASIL B, SWD 5장, SWR-022).
@details 입력과 이전 상태로 새 판정을 만드는 순수 함수다(AD-01). 시계·I/O·전역 상태를 쓰지 않는다.
    도어마다 우선순위 1~8 규칙을 순서대로 적용하고, 처음 적용되는 규칙 하나만 쓴다.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace

from childlock.model import (
    AUTO_LOCK_SPEED_KPH,
    WARNING_SENSOR_FAULT,
    Action,
    ControllerState,
    CrashStatus,
    Decision,
    Door,
    DoorVerdict,
    DriverCommand,
    InputValidity,
    Lock,
    PriorityReason,
    Side,
    State,
    VehicleSnapshot,
    door_lock,
)


@dataclass(frozen=True)
class RuleContext:
    """!@brief 규칙 함수가 공유하는 판정 입력 (SWD 5.1)."""

    snapshot: VehicleSnapshot
    commands: tuple[DriverCommand, ...]
    previous: ControllerState
    latched: bool
    stale: bool


Rule = Callable[[Door, RuleContext], DoorVerdict | None]


def _command_for(door: Door, commands: tuple[DriverCommand, ...]) -> DriverCommand | None:
    """!
    @brief 이번 주기 명령 중 그 도어를 대상으로 하는 마지막 명령을 찾는다.
    @param door 대상 도어
    @param commands 받은 순서대로의 유효 명령
    @return 마지막 명령, 없으면 None
    """
    targeting = [c for c in commands if c.side is Side.ALL or c.side.value == door.value]
    return targeting[-1] if targeting else None


def _risk(snapshot: VehicleSnapshot, door: Door) -> bool:
    """!@brief 도어의 후측방 접근위험 입력. @return 접근위험 여부"""
    if door is Door.LEFT:
        return snapshot.rear_left_approach_risk
    return snapshot.rear_right_approach_risk


def _isofix(snapshot: VehicleSnapshot, door: Door) -> bool:
    """!@brief 도어의 ISOFIX 연결 입력. @return 연결 여부"""
    return snapshot.isofix_left if door is Door.LEFT else snapshot.isofix_right


# ---- 우선순위 규칙 (SWD 5.3 결정 테이블) ----


def _rule_crash(door: Door, ctx: RuleContext) -> DoorVerdict | None:
    """!@brief 1순위: 충돌 확정 또는 유지 중이면 RELEASE (SWR-007)."""
    if ctx.latched:
        return DoorVerdict(Lock.RELEASE, PriorityReason.CRASH, "crash_confirmed")
    return None


def _rule_fault_or_stale(door: Door, ctx: RuleContext) -> DoorVerdict | None:
    """!@brief 2순위: 센서 고장 또는 freshness 상실이면 출력 유지 (SWR-021, SWR-013)."""
    held = door_lock(ctx.previous, door)
    if ctx.snapshot.sensor_fault:
        return DoorVerdict(held, PriorityReason.SENSOR_FAULT, "sensor_fault")
    if ctx.stale:
        return DoorVerdict(held, PriorityReason.INPUT_STALE, "input_stale")
    return None


def _rule_approach_risk(door: Door, ctx: RuleContext) -> DoorVerdict | None:
    """!@brief 3순위: 그 도어 접근위험이면 LOCK (SWR-005)."""
    if _risk(ctx.snapshot, door):
        return DoorVerdict(Lock.LOCK, PriorityReason.APPROACH_RISK, f"approach_risk_{door.value}")
    return None


def _rule_ignition_off(door: Door, ctx: RuleContext) -> DoorVerdict | None:
    """!@brief 4순위: 시동 꺼짐이면 RELEASE (SWR-020)."""
    if not ctx.snapshot.ignition_on:
        return DoorVerdict(Lock.RELEASE, PriorityReason.IGNITION_OFF, "ignition_off")
    return None


def _rule_forced_release(door: Door, ctx: RuleContext) -> DoorVerdict | None:
    """!@brief 5순위: 화재 > 과온 > 성인 탑승 중 첫 원인으로 RELEASE (SWR-017, D-15)."""
    s = ctx.snapshot
    causes = (
        (s.fire_detected, "fire"),
        (s.overtemperature_detected, "overtemperature"),
        (s.adult_present, "adult_present"),
    )
    for active, reason in causes:
        if active:
            return DoorVerdict(Lock.RELEASE, PriorityReason.FORCED_RELEASE, reason)
    return None


def _rule_isofix(door: Door, ctx: RuleContext) -> DoorVerdict | None:
    """!@brief 6순위: 그 도어 ISOFIX면 LOCK (SWR-018)."""
    if _isofix(ctx.snapshot, door):
        return DoorVerdict(Lock.LOCK, PriorityReason.ISOFIX, f"isofix_{door.value}")
    return None


def _rule_auto_lock(door: Door, ctx: RuleContext) -> DoorVerdict | None:
    """!@brief 7순위: 차속 3.0 km/h 이상이면 LOCK (SWR-003)."""
    if ctx.snapshot.vehicle_speed_kph >= AUTO_LOCK_SPEED_KPH:
        return DoorVerdict(Lock.LOCK, PriorityReason.AUTO_LOCK, "auto_lock_speed")
    return None


def _rule_driver(door: Door, ctx: RuleContext) -> DoorVerdict | None:
    """!@brief 8순위: 그 도어 대상 명령을 적용 (SWR-001, SWR-002)."""
    command = _command_for(door, ctx.commands)
    if command is None:
        return None
    if command.action is Action.LOCK:
        return DoorVerdict(Lock.LOCK, PriorityReason.DRIVER_COMMAND, "driver_lock")
    return DoorVerdict(Lock.RELEASE, PriorityReason.DRIVER_COMMAND, "driver_unlock")


RULES: tuple[Rule, ...] = (
    _rule_crash,
    _rule_fault_or_stale,
    _rule_approach_risk,
    _rule_ignition_off,
    _rule_forced_release,
    _rule_isofix,
    _rule_auto_lock,
    _rule_driver,
)


def _with_command_effect(door: Door, verdict: DoorVerdict, ctx: RuleContext) -> DoorVerdict:
    """!
    @brief 상위 규칙이 막은 운전자 명령의 효과를 반영한다 (SWD 5.3, SWR-004, CR-01).
    @param door 대상 도어
    @param verdict 적용된 규칙의 판정
    @param ctx 판정 입력
    @return 3순위+해제 명령이면 억제 표시, 4~7순위면 driver_rejected, 그 밖은 그대로
    """
    command = _command_for(door, ctx.commands)
    rank = verdict.priority.rank
    if command is None or rank <= 2 or rank == PriorityReason.DRIVER_COMMAND.rank:
        return verdict
    if rank == PriorityReason.APPROACH_RISK.rank:
        return replace(verdict, suppressed_unlock=command.action is Action.UNLOCK)
    return replace(verdict, reason_code="driver_rejected")


def _decide_door(door: Door, ctx: RuleContext) -> DoorVerdict:
    """!
    @brief 도어 하나를 우선순위 규칙으로 판정한다 (SWD 5.2).
    @param door 대상 도어
    @param ctx 판정 입력
    @return 처음 적용된 규칙의 판정. 없으면 출력 유지(hold)
    """
    for rule in RULES:
        verdict = rule(door, ctx)
        if verdict is not None:
            return _with_command_effect(door, verdict, ctx)
    return DoorVerdict(door_lock(ctx.previous, door), PriorityReason.HOLD, "no_change")


def _combine(
    left: DoorVerdict, right: DoorVerdict, snapshot: VehicleSnapshot
) -> tuple[PriorityReason, str]:
    """!
    @brief 두 도어 판정에서 평가 전체의 근거와 이유 코드를 고른다 (SWD 5.4, SWR-022, SWR-008).
    @param left 좌측 판정
    @param right 우측 판정
    @param snapshot 판정 입력
    @return (priority_reason, reason_code). 순위가 같으면 좌측
    """
    best = left if left.priority.rank <= right.priority.rank else right
    reason = best.reason_code
    if snapshot.crash_status is CrashStatus.PENDING and best.priority.rank > 3:
        reason = "crash_pending"
    return best.priority, reason


def _state_of(ctx: RuleContext) -> State:
    """!
    @brief 유효 입력이 있는 주기의 state를 정한다 (SWD 5.5).
    @param ctx 판정 입력
    @return CRASH_RELEASE > FAULT > DEGRADED > OFF > NORMAL 중 첫 일치
    """
    if ctx.latched:
        return State.CRASH_RELEASE
    if ctx.snapshot.sensor_fault:
        return State.FAULT
    if ctx.stale:
        return State.DEGRADED
    if not ctx.snapshot.ignition_on:
        return State.OFF
    return State.NORMAL


def _decide_without_input(previous: ControllerState, validity: InputValidity) -> Decision:
    """!
    @brief 입력이 없거나 무효인 주기: 출력·state를 유지한다 (SWR-024, SWR-013 ①).
    @param previous 이전 확정 상태
    @param validity NO_DATA 또는 INVALID
    @return 출력 유지 판정. 운전자 명령은 적용하지 않는다
    """
    if validity is InputValidity.NO_DATA:
        priority, reason = PriorityReason.HOLD, "no_change"
    else:
        priority, reason = PriorityReason.INPUT_INVALID, "input_invalid"
    return Decision(
        lock_left=previous.lock_left,
        lock_right=previous.lock_right,
        state=previous.state,
        priority_reason=priority,
        reason_code=reason,
        warning_code=None,
        crash_latched=previous.crash_latched,
    )


def _latched(snapshot: VehicleSnapshot, previous: ControllerState) -> bool:
    """!
    @brief 충돌 해제 유지 여부를 갱신한다 (SWR-007, D-12).
    @return 이전 유지 중이고 시동 ON이거나, 이번 입력이 CONFIRMED이면 True
    """
    confirmed = snapshot.crash_status is CrashStatus.CONFIRMED
    return (previous.crash_latched and snapshot.ignition_on) or confirmed


def decide(
    snapshot: VehicleSnapshot | None,
    commands: tuple[DriverCommand, ...],
    previous: ControllerState,
    validity: InputValidity,
) -> Decision:
    """!
    @brief 평가 1회의 판정을 만든다 (SWD 5.1).
    @param snapshot 최신 유효 입력. 아직 없으면 None
    @param commands 이번 주기 유효 운전자 명령(받은 순서)
    @param previous 이전 확정 상태
    @param validity 이번 주기 입력 유효성
    @return 좌·우 출력, state, 판정 근거, 이유 코드, 경고 코드, 충돌 유지, 억제된 해제 도어
    """
    no_input = snapshot is None or validity in (InputValidity.NO_DATA, InputValidity.INVALID)
    if snapshot is None or (no_input and not previous.crash_latched):
        return _decide_without_input(previous, validity)
    latched = previous.crash_latched if no_input else _latched(snapshot, previous)
    ctx = RuleContext(
        snapshot=snapshot,
        commands=() if no_input else commands,
        previous=previous,
        latched=latched,
        stale=validity is InputValidity.STALE,
    )
    left = _decide_door(Door.LEFT, ctx)
    right = _decide_door(Door.RIGHT, ctx)
    priority, reason = _combine(left, right, snapshot)
    return Decision(
        lock_left=left.lock,
        lock_right=right.lock,
        state=_state_of(ctx),
        priority_reason=priority,
        reason_code=reason,
        warning_code=WARNING_SENSOR_FAULT if snapshot.sensor_fault else None,
        crash_latched=latched,
        suppressed_unlocks=tuple(
            door for door, v in ((Door.LEFT, left), (Door.RIGHT, right)) if v.suppressed_unlock
        ),
    )
