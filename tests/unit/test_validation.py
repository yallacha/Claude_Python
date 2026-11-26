"""!
@brief childlock.validation 단위 시험 (SWD 3장, SWR-013 ①②).
"""

import math

import pytest

from childlock.model import (
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
from childlock.validation import parse_command, parse_snapshot

BOOL_FIELDS = (
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


def raw_snapshot(**overrides):
    """!@brief 모든 필드가 유효한 원시 입력을 만들고 일부를 바꾼다."""
    raw = {
        "source_timestamp_s": 1.25,
        "vehicle_speed_kph": 12.5,
        "gear": "D",
        "crash_status": "NONE",
        **{name: False for name in BOOL_FIELDS},
        "ignition_on": True,
    }
    raw.update(overrides)
    return raw


def test_valid_snapshot_is_converted_to_typed_object():
    """!@brief 유효 입력은 열거·불리언·실수 타입의 VehicleSnapshot이 된다."""
    result = parse_snapshot(raw_snapshot(isofix_left=True, crash_status="PENDING"))

    assert result == Valid(
        VehicleSnapshot(
            source_timestamp_s=1.25,
            vehicle_speed_kph=12.5,
            gear=Gear.D,
            crash_status=CrashStatus.PENDING,
            rear_left_approach_risk=False,
            rear_right_approach_risk=False,
            fire_detected=False,
            overtemperature_detected=False,
            adult_present=False,
            isofix_left=True,
            isofix_right=False,
            ignition_on=True,
            sensor_fault=False,
        )
    )


@pytest.mark.parametrize("speed", [0.0, 300.0, 0, 300])
def test_speed_range_boundaries_are_valid(speed):
    """!@brief 차속 0.0과 300.0(경계값, 정수 포함)은 유효하다."""
    assert isinstance(parse_snapshot(raw_snapshot(vehicle_speed_kph=speed)), Valid)


@pytest.mark.parametrize("speed", [-0.1, 300.1])
def test_speed_just_outside_range_is_rejected(speed):
    """!@brief 차속 -0.1, 300.1(경계 바로 바깥)은 범위 오류다."""
    assert parse_snapshot(raw_snapshot(vehicle_speed_kph=speed)) == Invalid(
        ("vehicle_speed_kph:range",)
    )


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_rejected(bad):
    """!@brief NaN, 무한대는 범위 비교를 통과하지 못하게 거절한다."""
    result = parse_snapshot(raw_snapshot(vehicle_speed_kph=bad, source_timestamp_s=bad))

    assert result == Invalid(("source_timestamp_s:range", "vehicle_speed_kph:range"))


def test_negative_timestamp_is_rejected():
    """!@brief 시각은 0.0 이상이어야 한다."""
    assert parse_snapshot(raw_snapshot(source_timestamp_s=-0.001)) == Invalid(
        ("source_timestamp_s:range",)
    )


@pytest.mark.parametrize("bad", [True, "12.5", None])
def test_non_number_speed_is_type_error(bad):
    """!@brief 불리언·문자열·None은 숫자 자리에서 형식 오류다."""
    assert parse_snapshot(raw_snapshot(vehicle_speed_kph=bad)) == Invalid(
        ("vehicle_speed_kph:type",)
    )


@pytest.mark.parametrize("field", BOOL_FIELDS)
@pytest.mark.parametrize("bad", [1, "true", None])
def test_boolean_fields_accept_only_real_booleans(field, bad):
    """!@brief 불리언 자리에 1, "true", None을 넣으면 형식 오류다."""
    assert parse_snapshot(raw_snapshot(**{field: bad})) == Invalid((f"{field}:type",))


def test_unknown_enum_value_is_rejected():
    """!@brief 정의되지 않은 충돌 상태 값은 거절한다 (OEM-IF-002)."""
    assert parse_snapshot(raw_snapshot(crash_status="UNKNOWN")) == Invalid(("crash_status:value",))


def test_enum_given_as_non_string_is_type_error():
    """!@brief 열거 자리에 숫자를 넣으면 형식 오류다."""
    assert parse_snapshot(raw_snapshot(gear=1)) == Invalid(("gear:type",))


def test_missing_field_is_reported_and_other_errors_still_collected():
    """!@brief 누락 필드와 다른 오류를 모두 모아 보고한다."""
    raw = raw_snapshot(gear="X")
    del raw["sensor_fault"]

    assert parse_snapshot(raw) == Invalid(("gear:value", "sensor_fault:missing"))


def test_extra_fields_are_ignored():
    """!@brief 정의되지 않은 여분 필드는 무시하고 유효 처리한다."""
    assert isinstance(parse_snapshot(raw_snapshot(debug="x")), Valid)


@pytest.mark.parametrize("bad", [None, [1, 2], "snapshot"])
def test_non_object_input_is_rejected(bad):
    """!@brief 객체(dict)가 아닌 입력은 거절한다."""
    assert parse_snapshot(bad) == Invalid(("not_object",))


def test_valid_command_is_converted():
    """!@brief 유효 운전자 명령은 DriverCommand가 된다."""
    result = parse_command({"side": "all", "action": "unlock", "source": "mobile_app"})

    assert result == Valid(DriverCommand(Side.ALL, Action.UNLOCK, Source.MOBILE_APP))


@pytest.mark.parametrize(
    ("raw", "errors"),
    [
        ({"side": "rear", "action": "lock", "source": "avn"}, ("side:value",)),
        ({"side": "left", "action": "open", "source": "avn"}, ("action:value",)),
        ({"side": "left", "action": "lock", "source": "key_fob"}, ("source:value",)),
        ({"side": "left", "action": "lock"}, ("source:missing",)),
        ({"side": 0, "action": "lock", "source": "avn"}, ("side:type",)),
    ],
)
def test_invalid_command_is_rejected_with_reason(raw, errors):
    """!@brief 미등록 값, 누락, 형식 오류 명령은 거절한다 (OEM-IF-004)."""
    assert parse_command(raw) == Invalid(errors)


def test_non_object_command_is_rejected():
    """!@brief 객체가 아닌 명령은 거절한다."""
    assert parse_command("lock") == Invalid(("not_object",))
