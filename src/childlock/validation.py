"""!
@brief 입력 검증 (ASIL B, SWD 3장, SWR-013).
@details 원시 입력(dict)을 검사해 Valid 또는 Invalid를 돌려준다. 예외를 던지지 않는다(AD-05).
"""

import math
from collections.abc import Callable, Mapping
from enum import Enum

from childlock.model import (
    SPEED_MAX_KPH,
    SPEED_MIN_KPH,
    Action,
    CrashStatus,
    DriverCommand,
    Gear,
    Invalid,
    Side,
    Source,
    Valid,
    VehicleSnapshot,
)

# 검사기: 원시 값 → (변환 값, 오류 코드 또는 None)
Checker = Callable[[object], tuple[object, str | None]]


def _number(low: float, high: float) -> Checker:
    """!
    @brief 범위가 있는 숫자 검사기를 만든다.
    @param low 하한(포함)
    @param high 상한(포함)
    @return 검사기. bool은 숫자로 보지 않고, NaN·무한대는 범위 오류다.
    """

    def check(value: object) -> tuple[object, str | None]:
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None, "type"
        if not math.isfinite(value) or not low <= value <= high:
            return None, "range"
        return float(value), None

    return check


def _boolean(value: object) -> tuple[object, str | None]:
    """!
    @brief 불리언 검사기. JSON true/false만 허용한다.
    @param value 원시 값
    @return (값, 오류 코드)
    """
    if type(value) is not bool:
        return None, "type"
    return value, None


def _enum(enum_type: type[Enum]) -> Checker:
    """!
    @brief 열거 검사기를 만든다.
    @param enum_type 허용 값을 가진 Enum 타입
    @return 검사기. 문자열이 아니면 형식 오류, 등록되지 않은 값이면 값 오류다.
    """

    def check(value: object) -> tuple[object, str | None]:
        if not isinstance(value, str):
            return None, "type"
        try:
            return enum_type(value), None
        except ValueError:
            return None, "value"

    return check


_BOOL_FIELDS = (
    "rear_left_approach_risk",
    "rear_right_approach_risk",
    "fire_detected",
    "overtemperature_detected",
    "adult_present",
    "isofix_left",
    "isofix_right",
    "ignition_on",
    "sensor_fault",
)

# VehicleSnapshot 필드별 검사기 (SWIF 1장). 순서가 오류 보고 순서다.
_SNAPSHOT_FIELDS: tuple[tuple[str, Checker], ...] = (
    ("source_timestamp_s", _number(0.0, math.inf)),
    ("vehicle_speed_kph", _number(SPEED_MIN_KPH, SPEED_MAX_KPH)),
    ("gear", _enum(Gear)),
    ("crash_status", _enum(CrashStatus)),
    *((name, _boolean) for name in _BOOL_FIELDS),
)

# DriverCommand 필드별 검사기 (SWIF 2장)
_COMMAND_FIELDS: tuple[tuple[str, Checker], ...] = (
    ("side", _enum(Side)),
    ("action", _enum(Action)),
    ("source", _enum(Source)),
)


def _check_fields(
    raw: object, fields: tuple[tuple[str, Checker], ...]
) -> dict[str, object] | Invalid:
    """!
    @brief 필드 표에 따라 원시 입력을 검사한다. 여분 필드는 무시한다.
    @param raw 원시 입력
    @param fields (필드 이름, 검사기) 목록
    @return 변환된 값 사전, 또는 모든 오류를 모은 Invalid
    """
    if not isinstance(raw, Mapping):
        return Invalid(("not_object",))
    values: dict[str, object] = {}
    errors: list[str] = []
    for name, checker in fields:
        if name not in raw:
            errors.append(f"{name}:missing")
            continue
        value, error = checker(raw[name])
        if error:
            errors.append(f"{name}:{error}")
        else:
            values[name] = value
    return Invalid(tuple(errors)) if errors else values


def parse_snapshot(raw: object) -> Valid[VehicleSnapshot] | Invalid:
    """!
    @brief 차량 입력을 검증하고 VehicleSnapshot으로 바꾼다 (SWR-013 ①).
    @param raw 원시 입력(JSON 객체)
    @return Valid(VehicleSnapshot) 또는 Invalid(오류 목록)
    """
    checked = _check_fields(raw, _SNAPSHOT_FIELDS)
    if isinstance(checked, Invalid):
        return checked
    return Valid(VehicleSnapshot(**checked))


def parse_command(raw: object) -> Valid[DriverCommand] | Invalid:
    """!
    @brief 운전자 명령을 검증하고 DriverCommand로 바꾼다 (SWR-013 ②).
    @param raw 원시 입력(JSON 객체)
    @return Valid(DriverCommand) 또는 Invalid(오류 목록)
    """
    checked = _check_fields(raw, _COMMAND_FIELDS)
    if isinstance(checked, Invalid):
        return checked
    return Valid(DriverCommand(**checked))
