"""!
@brief 공용 데이터 타입과 상수 (ASIL B, SWD 1.1·2장, SWIF).
@details 모든 데이터 객체는 불변이다(AD-04). 열거 값 문자열은 SWIF의 외부 인터페이스 값이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# ---- 상수 (SWD 1.1) ----
CYCLE_MS = 50  # 평가 주기 (SWR-023, D-03)
STALE_THRESHOLD_MS = 200  # freshness 상실 기준, 초과 시 STALE (SWR-013)
OVERRIDE_WINDOW_MS = 10000  # override 재입력 허용 시간, 이하 (SWR-006)
AUTO_LOCK_SPEED_KPH = 3.0  # 자동 잠금 차속, 이상 (SWR-003)
SPEED_MIN_KPH = 0.0  # 차속 하한 (OEM-IF-001)
SPEED_MAX_KPH = 300.0  # 차속 상한 (OEM-IF-001)
EVENT_CAPACITY = 100  # 결정 이력 보존 건수 (SWR-012)
WARNING_SENSOR_FAULT = "W_SENSOR_FAULT"  # 센서 고장 경고 코드 (SWR-021)


class Lock(StrEnum):
    """!@brief 차일드락 논리 출력 (OEM-IF-005)."""

    LOCK = "LOCK"
    RELEASE = "RELEASE"


class State(StrEnum):
    """!@brief 제어 상태 (SWIF 5.1)."""

    OFF = "OFF"
    NORMAL = "NORMAL"
    CRASH_RELEASE = "CRASH_RELEASE"
    FAULT = "FAULT"
    DEGRADED = "DEGRADED"
    OVERRIDE = "OVERRIDE"


class InputValidity(StrEnum):
    """!@brief 입력 유효성 (SWIF 4장)."""

    VALID = "VALID"
    INVALID = "INVALID"
    STALE = "STALE"
    NO_DATA = "NO_DATA"


class PriorityReason(StrEnum):
    """!
    @brief 판정 근거와 우선순위 (SWIF 5.2, SWR-022).
    @details rank가 작을수록 우선한다. hold·input_invalid는 규칙이 아니므로 가장 낮다.
    """

    CRASH = "crash"
    SENSOR_FAULT = "sensor_fault"
    INPUT_STALE = "input_stale"
    APPROACH_RISK = "approach_risk"
    IGNITION_OFF = "ignition_off"
    FORCED_RELEASE = "forced_release"
    ISOFIX = "isofix"
    AUTO_LOCK = "auto_lock"
    DRIVER_COMMAND = "driver_command"
    HOLD = "hold"
    INPUT_INVALID = "input_invalid"

    @property
    def rank(self) -> int:
        """!
        @brief 우선순위 순위를 돌려준다.
        @return 1(가장 높음) ~ 9(규칙 없음)
        """
        return _RANKS[self]


_RANKS = {
    PriorityReason.CRASH: 1,
    PriorityReason.SENSOR_FAULT: 2,
    PriorityReason.INPUT_STALE: 2,
    PriorityReason.APPROACH_RISK: 3,
    PriorityReason.IGNITION_OFF: 4,
    PriorityReason.FORCED_RELEASE: 5,
    PriorityReason.ISOFIX: 6,
    PriorityReason.AUTO_LOCK: 7,
    PriorityReason.DRIVER_COMMAND: 8,
    PriorityReason.HOLD: 9,
    PriorityReason.INPUT_INVALID: 9,
}


class Side(StrEnum):
    """!@brief 운전자 명령 대상 (OEM-IF-004)."""

    LEFT = "left"
    RIGHT = "right"
    ALL = "all"


class Action(StrEnum):
    """!@brief 운전자 명령 동작 (OEM-IF-004)."""

    LOCK = "lock"
    UNLOCK = "unlock"


class Source(StrEnum):
    """!@brief 운전자 명령 경로 (OEM-IF-004)."""

    PHYSICAL_BUTTON = "physical_button"
    AVN = "avn"
    VOICE = "voice"
    MOBILE_APP = "mobile_app"


class Gear(StrEnum):
    """!@brief 기어 (OEM-IF-001). 검증만 하고 판정에는 쓰지 않는다."""

    P = "P"
    N = "N"
    D = "D"
    R = "R"


class CrashStatus(StrEnum):
    """!@brief 충돌 상태 (OEM-IF-002)."""

    NONE = "NONE"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"


class Door(StrEnum):
    """!@brief 후석 도어. 평가 순서는 LEFT, RIGHT."""

    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class VehicleSnapshot:
    """!@brief 차량 입력 묶음 (SWIF 1장)."""

    source_timestamp_s: float
    vehicle_speed_kph: float
    gear: Gear
    crash_status: CrashStatus
    rear_left_approach_risk: bool
    rear_right_approach_risk: bool
    fire_detected: bool
    overtemperature_detected: bool
    adult_present: bool
    isofix_left: bool
    isofix_right: bool
    ignition_on: bool
    sensor_fault: bool


@dataclass(frozen=True)
class DriverCommand:
    """!@brief 운전자 명령 (SWIF 2장)."""

    side: Side
    action: Action
    source: Source


@dataclass(frozen=True)
class ControllerState:
    """!@brief 평가 사이에 유지하는 확정 상태."""

    lock_left: Lock
    lock_right: Lock
    state: State
    crash_latched: bool


@dataclass(frozen=True)
class DoorVerdict:
    """!@brief 도어 하나의 판정 결과 (SWD 5.2)."""

    lock: Lock
    priority: PriorityReason
    reason_code: str
    suppressed_unlock: bool = False


@dataclass(frozen=True)
class Decision:
    """!@brief 평가 1회의 판정 결과 (SWD 5.1)."""

    lock_left: Lock
    lock_right: Lock
    state: State
    priority_reason: PriorityReason
    reason_code: str
    warning_code: str | None
    crash_latched: bool
    suppressed_unlocks: tuple[Door, ...] = ()


@dataclass(frozen=True)
class Status:
    """!@brief 표시 인터페이스로 제공하는 상태 (SWIF 4장, SWR-014)."""

    lock_left: Lock
    lock_right: Lock
    state: State
    input_validity: InputValidity
    priority_reason: PriorityReason
    reason_code: str
    warning_code: str | None


@dataclass(frozen=True)
class Event:
    """!@brief 결정 이력 한 건. 허용 필드만 가진다 (SWIF 6장, SWR-011)."""

    event_id: int
    timestamp_s: float
    state: State
    lock_left: Lock
    lock_right: Lock
    priority_reason: PriorityReason
    reason_code: str
    input_validity: InputValidity


@dataclass(frozen=True)
class Valid[T]:
    """!@brief 검증 통과 결과 (AD-05)."""

    value: T


@dataclass(frozen=True)
class Invalid:
    """!@brief 검증 실패 결과. errors는 '필드:사유' 문자열 목록이다."""

    errors: tuple[str, ...]


INITIAL_STATE = ControllerState(Lock.RELEASE, Lock.RELEASE, State.OFF, False)  # SWR-024
INITIAL_STATUS = Status(
    Lock.RELEASE,
    Lock.RELEASE,
    State.OFF,
    InputValidity.NO_DATA,
    PriorityReason.HOLD,
    "no_change",
    None,
)  # SWR-024


def to_ms(seconds: float) -> int:
    """!
    @brief 초를 정수 밀리초로 바꾼다. 시간 비교는 이 값으로 한다 (DD-C02).
    @param seconds 초 단위 시각 또는 간격
    @return 반올림한 밀리초
    """
    return round(seconds * 1000)


def door_lock(source: ControllerState | Decision, door: Door) -> Lock:
    """!
    @brief 도어에 해당하는 출력을 돌려준다.
    @param source 좌·우 출력을 가진 상태 또는 판정 결과
    @param door 대상 도어
    @return 그 도어의 출력
    """
    return source.lock_left if door is Door.LEFT else source.lock_right
