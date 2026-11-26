"""!
@brief 입력 freshness 판정 (ASIL B, SWD 4장, SWR-013).
"""

from childlock.model import STALE_THRESHOLD_MS, to_ms


def is_stale(now_s: float, last_timestamp_s: float | None) -> bool:
    """!
    @brief 최신 유효 입력이 200 ms를 초과해 갱신되지 않았는지 판정한다.
    @param now_s 평가 시각(초)
    @param last_timestamp_s 최신 유효 입력의 source_timestamp_s. 없으면 None
    @return 경과 시간 > 200 ms이면 True. 입력이 없으면 False(NO_DATA는 controller 처리)
    """
    if last_timestamp_s is None:
        return False
    # 정수 ms로 비교해 부동소수 누적 오차로 경계가 틀어지지 않게 한다 (DD-C02)
    return to_ms(now_s) - to_ms(last_timestamp_s) > STALE_THRESHOLD_MS
