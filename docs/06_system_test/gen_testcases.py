# -*- coding: utf-8 -*-
"""stc_testcases.json 생성기 (SWR-SPEC-001 v1.1 -> SW 시스템 시험 케이스).

실행: python gen_testcases.py   (같은 폴더의 pict_result_SWR-022.tsv 를 읽는다)
기대값은 SWR 명세(우선순위 SWR-022, SWR-004 CR-01 포함)에서만 도출한다.
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK, REL = "LOCK", "RELEASE"
UNSET = object()
SRC4 = ["physical_button", "avn", "voice", "mobile_app"]
ENV_SIL = "PC/SIL (Python 3.12 childlock, 고정 시계, 평가 주기 50 ms)"
PRE_FRESH = "childlock 신규 기동 직후(시계 0 ms, 결정 이력 0건, 출력 RELEASE/RELEASE)"
DEFAULT_SNAP = {
    "vehicle_speed_kph": 0.0, "gear": "P", "crash_status": "NONE",
    "rear_left_approach_risk": False, "rear_right_approach_risk": False,
    "fire_detected": False, "overtemperature_detected": False, "adult_present": False,
    "isofix_left": False, "isofix_right": False, "ignition_on": True, "sensor_fault": False,
}
FIELD_ORDER = ["source_timestamp_s"] + list(DEFAULT_SNAP)


def C(side, action, source="avn"):
    return {"side": side, "action": action, "source": source}


def E(l=None, r=None, state=None, val=None, pr=None, rc=None, wc=UNSET):
    d = {}
    if l:
        d["lock_left"] = l
    if r:
        d["lock_right"] = r
    if state:
        d["state"] = state
    if val:
        d["input_validity"] = val
    if pr:
        d["priority_reason"] = pr
    if rc:
        d["reason_code"] = rc
    if wc is not UNSET:
        d["warning_code"] = wc
    return d


def fmt_val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, str):
        return f'"{v}"'
    return str(v)


class Seq:
    def __init__(self):
        self.t = 0
        self.steps = []
        self.lines = []
        self.exps = []

    def step(self, adv=50, snap=None, cmds=None, exp=None, bad=None, drop=None):
        """snap: 기본값에 덮어쓰는 부분 값. bad/drop: 기본값 병합 없이 보내는 원본(snapshot_raw)."""
        self.t += adv
        st = {"advance_ms": adv}
        parts = []
        if bad is not None or drop:
            raw = {"source_timestamp_s": round(self.t / 1000.0, 3)}
            raw.update(DEFAULT_SNAP)
            for k, v in (bad or {}).items():
                raw[k] = v
            for k in (drop or []):
                raw.pop(k, None)
            st["snapshot_raw"] = raw
            desc = []
            for k, v in (bad or {}).items():
                desc.append(f"{k}={fmt_val(v)}")
            for k in (drop or []):
                desc.append(f"{k} 필드 제거")
            parts.append("원본 VehicleSnapshot(기본값 기반, 병합 없이 그대로) 제출: " + ", ".join(desc))
        elif snap is not None:
            st["snapshot"] = dict(snap)
            if snap:
                parts.append("VehicleSnapshot(기본값 + " + ", ".join(f"{k}={fmt_val(v)}" for k, v in snap.items()) + ") 제출")
            else:
                parts.append("VehicleSnapshot(기본값: 0.0 km/h, gear P, 불리언 모두 false, ignition_on true) 제출")
        else:
            parts.append("VehicleSnapshot 제출 없음")
        if cmds:
            st["commands"] = cmds
            parts.append("DriverCommand 제출: " + "; ".join(json.dumps(c, ensure_ascii=False) for c in cmds))
        if exp:
            st["expect"] = exp
        n = len(self.steps) + 1
        line = f"{n}. 시계 +{adv} ms(누계 {self.t} ms) 전진 → " + " → ".join(parts) + " → 평가 1회"
        if exp:
            line += " → Status 확인: " + ", ".join(f"{k}={fmt_val(v)}" for k, v in exp.items())
            self.exps.append(f"단계 {n}: " + ", ".join(f"{k}={fmt_val(v)}" for k, v in exp.items()))
        else:
            line += " (판정 없음, 상태 진행용)"
        self.lines.append(line)
        self.steps.append(st)
        return self


def boot(sq, extra=None, **ov):
    exp = E(REL, REL, val="VALID")
    if ov.get("ignition_on", True):
        exp["state"] = "NORMAL"
    if extra:
        exp.update(extra)
    sq.step(50, dict(ov), exp=exp)
    return sq


def lock_all(sq):
    sq.step(50, {}, [C("all", "lock")], E(LOCK, LOCK, rc="driver_lock"))


def lock_left(sq):
    sq.step(50, {}, [C("left", "lock")], E(LOCK, REL, rc="driver_lock"))


def crash7(sq, snap, last_exp, **kw):
    """CONFIRMED를 최초 입력한 평가부터 300 ms(7번째 평가) 동안 유지, 마지막(+300 ms)에만 판정."""
    s = dict(snap)
    s["crash_status"] = "CONFIRMED"
    for i in range(7):
        sq.step(50, s, exp=last_exp if i == 6 else None)


CASES = []
KEYMAP = {}


def case(key, reqs, purpose, inputs, sq=None, techniques=None, priority="Medium", pre=PRE_FRESH,
         proposed=False, cat="functional", env=ENV_SIL, remarks="", expected_extra="", procedure=None,
         expected=None, pass_criteria=None):
    c = {
        "_key": key, "basis_ids": reqs, "category": cat,
        "source": "claude" if proposed else "basis", "proposed": proposed,
        "purpose": purpose, "preconditions": pre, "inputs": inputs,
        "techniques": techniques or ["요구사항 기반"], "priority": priority,
        "environment": env, "remarks": remarks,
    }
    if sq is not None:
        c["procedure"] = "\n".join(sq.lines)
        c["expected"] = "\n".join(sq.exps) + ((("\n" + expected_extra) if expected_extra else ""))
        c["pass_criteria"] = pass_criteria or "expect가 있는 모든 단계에서 Status 값이 기대값과 일치(하나라도 다르면 불합격)"
        c["vector"] = {"steps": sq.steps}
    else:
        c["procedure"] = procedure
        c["expected"] = expected
        c["pass_criteria"] = pass_criteria
    CASES.append(c)
    KEYMAP[key] = c
    return c


EP, BV, REQB, FI, WOW, ERR, ST, PW = ("동치 분할", "경계값 분석", "요구사항 기반", "고장 주입", "WoW(Worst-of-Worst)",
                                      "오류 추정", "상태 전이", "페어와이즈(PICT)")

# =====================================================================
# SWR-001 운전자 잠금 명령
# =====================================================================
for side, key, exp_l, exp_r in [("left", "s1_left", LOCK, REL), ("right", "s1_right", REL, LOCK), ("all", "s1_all", LOCK, LOCK)]:
    sq = Seq()
    boot(sq)
    for src in SRC4:
        sq.step(50, {}, [C(side, "lock", src)], E(exp_l, exp_r, pr="driver_command", rc="driver_lock"))
        sq.step(50, {}, [C("all", "unlock", "avn")], E(REL, REL, rc="driver_unlock"))
    tgt = {"left": "lock_left만", "right": "lock_right만", "all": "lock_left와 lock_right 모두"}[side]
    defect = {"left": "left가 right 출력에 매핑되거나 특정 source(voice 등)만 무시되는 결함",
              "right": "right가 left 출력에 매핑되거나 특정 source만 무시되는 결함",
              "all": "all이 한쪽 출력만 바꾸거나 특정 source에서 누락되는 결함"}[side]
    case(key, ["SWR-001"],
         f"side={side} 잠금 명령을 source 4종 각각으로 보내 {tgt} LOCK이 되는지 확인 — {defect} 검출 (검증 기준 4종×3종 조합 중 side={side} 4건)",
         f"정지 0.0 km/h, 정상 입력. DriverCommand(side={side}, action=lock, source={'/'.join(SRC4)} 순차). 각 시도 사이에 side=all unlock으로 RELEASE 복귀",
         sq, [REQB, EP], "Medium")

sq = Seq()
boot(sq)
sq.step(50, {}, [C("left", "lock")], E(LOCK, REL, rc="driver_lock"))
sq.step(50, {}, [C("right", "lock")], E(LOCK, LOCK, rc="driver_lock"))
case("s1_keep", ["SWR-001"],
     "지정하지 않은 출력은 바꾸지 않는다 — 좌측이 LOCK인 상태에서 right 잠금 시 좌측이 RELEASE로 되돌려지는(비지정 출력 덮어쓰기) 결함 검출",
     "DriverCommand(side=left, action=lock, source=avn) 후 DriverCommand(side=right, action=lock, source=avn). 정지 0.0 km/h",
     sq, [REQB, EP], "Medium")

# =====================================================================
# SWR-002 운전자 해제 명령
# =====================================================================
for side, key, exp_l, exp_r in [("left", "s2_left", REL, LOCK), ("right", "s2_right", LOCK, REL), ("all", "s2_all", REL, REL)]:
    sq = Seq()
    boot(sq)
    lock_all(sq)
    for src in SRC4:
        sq.step(50, {}, [C(side, "unlock", src)], E(exp_l, exp_r, pr="driver_command", rc="driver_unlock"))
        sq.step(50, {}, [C("all", "lock", "avn")], E(LOCK, LOCK, rc="driver_lock"))
    tgt = {"left": "lock_left만", "right": "lock_right만", "all": "lock_left와 lock_right 모두"}[side]
    case(key, ["SWR-002"],
         f"side={side} 해제 명령을 source 4종 각각으로 보내 {tgt} RELEASE가 되고 나머지는 LOCK 유지되는지 확인 — side 매핑 오류, 특정 source 무시 결함 검출",
         f"정지 0.0 km/h, 정상 입력, 초기 LOCK/LOCK. DriverCommand(side={side}, action=unlock, source={'/'.join(SRC4)} 순차). 각 시도 사이에 side=all lock으로 LOCK 복귀",
         sq, [REQB, EP], "Medium")

sq = Seq()
boot(sq)
lock_all(sq)
sq.step(50, {}, [C("left", "unlock")], E(REL, LOCK, rc="driver_unlock"))
sq.step(50, {}, [C("right", "unlock")], E(REL, REL, rc="driver_unlock"))
case("s2_keep", ["SWR-002"],
     "지정하지 않은 출력은 바꾸지 않는다 — 우측이 LOCK인 상태에서 left 해제 시 우측이 RELEASE로 바뀌는 결함 검출",
     "초기 LOCK/LOCK에서 DriverCommand(side=left, action=unlock) 후 DriverCommand(side=right, action=unlock). 정지 0.0 km/h",
     sq, [REQB, EP], "Medium")

# =====================================================================
# SWR-003 주행 자동 잠금
# =====================================================================
sq = Seq()
boot(sq)
sq.step(50, {"vehicle_speed_kph": 2.9}, exp=E(REL, REL, val="VALID", pr="hold", rc="no_change"))
sq.step(50, {"vehicle_speed_kph": 3.0}, exp=E(LOCK, LOCK, pr="auto_lock", rc="auto_lock_speed"))
case("s3_bound", ["SWR-003"],
     "자동 잠금 임계값 3.0 km/h 경계 — 2.9에서는 잠그지 않고 3.0인 첫 평가주기에 잠금. `>`(3.0 초과)로 잘못 구현된 경우와 임계값 오입력(예: 2.9 이상) 검출",
     "vehicle_speed_kph = 0.0 → 2.9(경계 직하) → 3.0(경계). 그 외 기본값, 명령 없음",
     sq, [BV, EP], "High")

sq = Seq()
boot(sq)
sq.step(50, {"vehicle_speed_kph": 3.0}, exp=E(LOCK, LOCK, rc="auto_lock_speed"))
sq.step(50, {"vehicle_speed_kph": 2.9}, exp=E(LOCK, LOCK, pr="hold", rc="no_change"))
sq.step(50, {"vehicle_speed_kph": 0.0}, exp=E(LOCK, LOCK, pr="hold", rc="no_change"))
case("s3_nounlock", ["SWR-003", "SWR-022"],
     "3.0 이상에서 3.0 미만으로 내려가도 자동으로 해제하지 않는다(규칙 없음 → hold) — 히스테리시스 없이 속도 미만 시 RELEASE로 되돌리는 결함 검출",
     "vehicle_speed_kph = 3.0 → 2.9 → 0.0, 명령 없음",
     sq, [BV, ST], "High")

sq = Seq()
sq.step(50, {"vehicle_speed_kph": 3.1}, exp=E(LOCK, LOCK, state="NORMAL", val="VALID", pr="auto_lock", rc="auto_lock_speed"))
case("s3_31", ["SWR-003"],
     "경계 바깥값 3.1 km/h가 기동 후 첫 유효 입력일 때 첫 평가주기에 잠금 — NO_DATA→VALID 전이 평가에서 자동 잠금이 누락되는 결함과 분해능 0.1 처리 오류 검출",
     "기동 직후 첫 VehicleSnapshot vehicle_speed_kph = 3.1 km/h, 명령 없음",
     sq, [BV, EP], "Medium")

# =====================================================================
# SWR-004 운전자 명령 적용 조건
# =====================================================================
sq = Seq()
sq.step(50, {"vehicle_speed_kph": 50.0}, exp=E(LOCK, LOCK, state="NORMAL", rc="auto_lock_speed"))
sq.step(50, {"vehicle_speed_kph": 50.0}, [C("all", "unlock")], E(LOCK, LOCK, pr="auto_lock", rc="driver_rejected"))
case("s4_speed", ["SWR-004", "SWR-003", "SWR-022"],
     "7순위(주행 자동 잠금)가 8순위 해제 명령을 막는다 — 차속 50.0 km/h에서 해제 명령이 적용되거나 이유가 driver_unlock으로 기록되는 결함 검출 (SWR-022 ⑦+⑧ 쌍)",
     "vehicle_speed_kph = 50.0(자동 잠금 유효 클래스 대표값), DriverCommand(side=all, action=unlock, source=avn)",
     sq, [EP, REQB], "High")

sq = Seq()
sq.step(50, {"isofix_left": True}, exp=E(LOCK, REL, state="NORMAL", pr="isofix", rc="isofix_left"))
sq.step(50, {"isofix_left": True}, [C("left", "unlock")], E(LOCK, REL, rc="driver_rejected"))
case("s4_isofix", ["SWR-004", "SWR-018"],
     "6순위 ISOFIX가 좌측 해제 명령을 막고 이유 driver_rejected를 기록 — ISOFIX 중 해제 허용 또는 이유 코드 오기록 검출",
     "isofix_left = true, DriverCommand(side=left, action=unlock, source=avn). 정지 0.0 km/h",
     sq, [EP, REQB], "Medium")

sq = Seq()
sq.step(50, {"isofix_left": True}, exp=E(LOCK, REL, state="NORMAL", rc="isofix_left"))
sq.step(50, {"isofix_left": True}, [C("right", "lock")], E(LOCK, LOCK, pr="isofix", rc="isofix_left"))
sq.step(50, {"isofix_left": True}, [C("all", "unlock")], E(LOCK, REL))
case("s4_all", ["SWR-004", "SWR-009"],
     "side=all 해제 명령에서 좌측만 ISOFIX이면 우측만 RELEASE — all을 한 덩어리로 거절/승인하는(출력별 판정 누락) 결함 검출",
     "isofix_left = true(우측 false), 우측 LOCK 후 DriverCommand(side=all, action=unlock, source=avn)",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq, {"state": "OFF", "reason_code": "ignition_off"}, ignition_on=False)
sq.step(50, {"ignition_on": False}, [C("all", "lock")], E(REL, REL, rc="driver_rejected"))
case("s4_ign", ["SWR-004", "SWR-020"],
     "4순위 시동 꺼짐이 8순위 잠금 명령을 막는다 — ignition_on=false에서 잠금 명령 적용 결함 검출",
     "ignition_on = false, DriverCommand(side=all, action=lock, source=avn). 정지 0.0 km/h",
     sq, [EP, REQB], "Medium")
sq = Seq()
boot(sq, {"reason_code": "fire"}, fire_detected=True)
sq.step(50, {"fire_detected": True}, [C("all", "lock")], E(REL, REL, rc="driver_rejected"))
case("s4_fire", ["SWR-004", "SWR-017"],
     "5순위 화재가 8순위 잠금 명령을 막는다 — 화재 중 잠금 명령 적용 결함 검출",
     "fire_detected = true, DriverCommand(side=all, action=lock, source=avn). 정지 0.0 km/h",
     sq, [EP, REQB], "Medium")
sq = Seq()
boot(sq)
lock_all(sq)
sq.step(50, {"sensor_fault": True}, [C("all", "unlock")],
        E(LOCK, LOCK, state="FAULT", pr="sensor_fault", rc="sensor_fault", wc="W_SENSOR_FAULT"))
case("s4_sensor", ["SWR-004", "SWR-021"],
     "CR-01: 2순위 센서 고장이 해제 명령을 막고 이유는 driver_rejected가 아니라 sensor_fault — 1.0판 코드 범위(1~2순위 코드 누락)로 구현된 결함 검출",
     "초기 LOCK/LOCK, sensor_fault = true, DriverCommand(side=all, action=unlock, source=avn)",
     sq, [EP, REQB, ERR], "High",
     remarks="CR-01(SWR-004 v1.1) 반영 확인 케이스")

sq = Seq()
boot(sq)
for i in range(7):
    sq.step(50, {"crash_status": "CONFIRMED"}, [C("all", "lock")], E(REL, REL, pr="crash", rc="crash_confirmed") if i == 6 else None)
case("s4_crash", ["SWR-004", "SWR-007"],
     "CR-01: 1순위 충돌 확정이 잠금 명령을 막고 이유는 crash_confirmed — 충돌 확정 중 매 주기 보낸 잠금 명령이 적용되어 LOCK이 되거나 driver_rejected로 기록되는 결함 검출 (초기 RELEASE에서 LOCK 적용 여부로 구분, 300 ms 시점 판정)",
     "crash_status = CONFIRMED 7회 평가(+300 ms) 유지 중 매 주기 DriverCommand(side=all, action=lock, source=avn), 초기 RELEASE/RELEASE",
     sq, [EP, REQB], "High")

# =====================================================================
# SWR-005 접근위험
# =====================================================================
sq = Seq()
boot(sq)
sq.step(50, {"rear_left_approach_risk": True}, exp=E(LOCK, REL, pr="approach_risk", rc="approach_risk_left"))
sq.step(50, {"rear_left_approach_risk": True}, [C("left", "unlock")], E(LOCK, REL, pr="approach_risk", rc="approach_risk_left"))
sq.step(50, {}, exp=E(LOCK, REL, pr="hold", rc="no_change"))
case("s5_left", ["SWR-005", "SWR-004"],
     "좌측 접근위험 true가 된 다음 평가주기에 좌측 LOCK(우측 불변), 해제 명령 억제 시에도 approach_risk_left, 접근위험이 false로 돌아가도 자동 해제하지 않음 — 지연 반영, 해제 허용, 위험 해소 시 자동 해제 결함 검출",
     "rear_left_approach_risk = true(RELEASE 상태에서), DriverCommand(side=left, action=unlock), 이어서 rear_left_approach_risk = false",
     sq, [EP, REQB, ST], "High")

sq = Seq()
boot(sq)
sq.step(50, {"rear_right_approach_risk": True}, exp=E(REL, LOCK, pr="approach_risk", rc="approach_risk_right"))
sq.step(50, {"rear_right_approach_risk": True}, [C("right", "unlock")], E(REL, LOCK, pr="approach_risk", rc="approach_risk_right"))
sq.step(50, {"rear_right_approach_risk": True}, [C("all", "unlock")], E(REL, LOCK, state="OVERRIDE", rc="approach_override_right"))
case("s5_right", ["SWR-005", "SWR-009", "SWR-006"],
     "우측 접근위험: 우측만 LOCK·좌측 불변, 우측 해제 명령 억제(approach_risk_right), 10 s 이내 side=all 해제 재입력은 우측 도어의 override(approach_override_right, 출력 LOCK 유지·좌측 RELEASE 유지) — 좌/우 신호 매핑 뒤바뀜, 우측 전용 이유 코드 오기록, side=all 재입력이 override 판정에서 빠지는 결함 검출",
     "rear_right_approach_risk = true, DriverCommand(side=right, action=unlock) 후 50 ms 뒤 (side=all, action=unlock)",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq)
lock_all(sq)
sq.step(50, {"rear_left_approach_risk": True, "ignition_on": False}, exp=E(LOCK, REL, pr="approach_risk", rc="approach_risk_left"))
case("s5_ign", ["SWR-005", "SWR-020", "SWR-022"],
     "접근위험(3순위)과 시동 꺼짐(4순위) 동시 — 좌측은 LOCK 유지, 우측만 RELEASE. 시동 꺼짐이 전체 출력을 해제하는(순위 역전) 결함 검출 (SWR-022 ③+④ 쌍, 우측 해제로 4순위 적용도 확인)",
     "초기 LOCK/LOCK, rear_left_approach_risk = true 와 ignition_on = false 동시 입력",
     sq, [EP, REQB], "High")

# =====================================================================
# SWR-006 override
# =====================================================================
def approach_first(sq, side="left"):
    risk = {"rear_left_approach_risk": True} if side == "left" else {"rear_right_approach_risk": True}
    boot(sq)
    sq.step(50, risk, exp=E(LOCK, REL, pr="approach_risk", rc="approach_risk_left") if side == "left" else E(REL, LOCK))
    sq.step(150, risk, [C(side, "unlock")], E(LOCK, REL, state="NORMAL", rc="approach_risk_left"))
    return risk


sq = Seq()
risk = approach_first(sq)   # 최초 억제 시각 t=250 ms
sq.step(10000, risk, [C("left", "unlock")], E(LOCK, REL, state="OVERRIDE", rc="approach_override_left"))
sq.step(50, risk, exp=E(LOCK, REL, state="OVERRIDE"))
sq.step(50, {}, exp=E(LOCK, REL, state="NORMAL"))
case("s6_100", ["SWR-006"],
     "재입력 간격 10.0 s(경계 포함) → OVERRIDE, approach_override_left, 출력 LOCK, 접근위험 유지 중 OVERRIDE 지속, 접근위험 false가 된 평가주기에 종료 — `<`로 구현(10.0 s 제외)된 결함, OVERRIDE 조기/지연 종료 검출",
     "최초 억제 t=250 ms(rear_left_approach_risk=true, 좌측 해제 명령), 재입력 t=10250 ms(간격 10.0 s), 이후 접근위험 true 유지 1회 → false",
     sq, [BV, ST], "High")

sq = Seq()
risk = approach_first(sq)
sq.step(10100, risk, [C("left", "unlock")], E(LOCK, REL, state="NORMAL", pr="approach_risk", rc="approach_risk_left"))
sq.step(5000, risk, [C("left", "unlock")], E(LOCK, REL, state="OVERRIDE", rc="approach_override_left"))
case("s6_101", ["SWR-006"],
     "재입력 간격 10.1 s(경계 바깥) → OVERRIDE 아님, 새 첫 억제(approach_risk_left)로 처리되고 그 시각부터 새 10 s 창이 시작되어 5.0 s 뒤 재입력은 OVERRIDE — 창이 갱신되지 않거나 10.1 s에서 override 되는 결함 검출",
     "최초 억제 t=250 ms, 재입력 t=10350 ms(간격 10.1 s), 다시 재입력 t=15350 ms(새 첫 억제 후 5.0 s)",
     sq, [BV, ST], "High")

sq = Seq()
boot(sq)
both = {"rear_left_approach_risk": True, "rear_right_approach_risk": True}
sq.step(50, both, exp=E(LOCK, LOCK, pr="approach_risk", rc="approach_risk_left"))
sq.step(50, both, [C("right", "unlock")], E(LOCK, LOCK, state="NORMAL", rc="approach_risk_left"))   # 좌·우 동순위 → 좌측 코드(SWR-022)
sq.step(1000, both, [C("left", "unlock")], E(LOCK, LOCK, state="NORMAL", rc="approach_risk_left"))
sq.step(1000, both, [C("right", "unlock")], E(LOCK, LOCK, state="OVERRIDE", rc="approach_override_right"))
case("s6_door", ["SWR-006", "SWR-009"],
     "도어별 override 창 — 우측 억제 후 좌측 해제 재입력은 override가 아니라 좌측의 첫 억제이고, 우측 재입력(2.0 s 뒤)은 우측 override — 두 도어가 하나의 창/카운터를 공유하는 결함 검출",
     "좌·우 접근위험 true 유지, 우측 해제 명령(t=150 ms) → 좌측 해제 명령(t=1150 ms) → 우측 해제 명령(t=2150 ms)",
     sq, [EP, ST], "High")

# =====================================================================
# SWR-007 충돌 확정
# =====================================================================
REL_CRASH = E(REL, REL, state="CRASH_RELEASE", pr="crash", rc="crash_confirmed")
sq = Seq()
boot(sq)
lock_all(sq)
sq.step(50, {"vehicle_speed_kph": 50.0, "rear_left_approach_risk": True}, exp=E(LOCK, LOCK))
crash7(sq, {"vehicle_speed_kph": 50.0, "rear_left_approach_risk": True}, REL_CRASH)
case("s7_basic", ["SWR-007", "SWR-023"],
     "CONFIRMED 입력 후 300 ms(7번째 평가) 이내 두 출력 RELEASE, CRASH_RELEASE, crash_confirmed — 접근위험·고속·LOCK 상태에서 충돌이 무시되는(순위 오류) 결함과 300 ms 초과 디바운스 결함 검출",
     "초기 LOCK/LOCK, vehicle_speed_kph = 50.0, rear_left_approach_risk = true 에서 crash_status = CONFIRMED (7회 평가(+300 ms까지) 유지)",
     sq, [REQB, BV], "High", remarks="시간 판정: 입력 후 300 ms(고정 시계) 시점의 평가에서 확인. 즉시 해제는 합격, 디바운스가 있어도 300 ms 이내면 합격")

sq = Seq()
boot(sq)
lock_all(sq)
crash7(sq, {}, REL_CRASH)
sq.step(50, {"crash_status": "NONE"}, exp=E(REL, REL, state="CRASH_RELEASE"))
sq.step(50, {"crash_status": "NONE", "vehicle_speed_kph": 50.0}, [C("all", "lock")], E(REL, REL, state="CRASH_RELEASE"))
sq.step(50, {"crash_status": "PENDING", "vehicle_speed_kph": 50.0, "rear_left_approach_risk": True, "isofix_left": True}, [C("all", "lock")],
        E(REL, REL, state="CRASH_RELEASE"))
for i in range(5):
    sq.step(50, {"crash_status": "NONE", "vehicle_speed_kph": 50.0}, exp=E(REL, REL, state="CRASH_RELEASE") if i == 4 else None)
case("s7_latch", ["SWR-007"],
     "충돌 해제 유지 — crash_status가 NONE/PENDING으로 바뀌고 잠금 명령·차속 50 km/h·접근위험·ISOFIX가 들어와도 ignition_on=true인 동안 RELEASE 유지 (래치가 한 주기만 유지되거나 자동 잠금이 재개되는 결함 검출)",
     "CONFIRMED로 해제 후 crash_status = NONE(+잠금 명령, 50.0 km/h), PENDING(+접근위험·ISOFIX 좌측·잠금 명령), NONE 5회 유지",
     sq, [REQB, ST], "High")

sq = Seq()
boot(sq)
lock_all(sq)
crash7(sq, {}, REL_CRASH)
sq.step(50, {"ignition_on": False}, exp=E(REL, REL, state="OFF", pr="ignition_off", rc="ignition_off"))
sq.step(50, {"ignition_on": True}, exp=E(REL, REL, state="NORMAL"))
sq.step(50, {}, [C("all", "lock")], E(LOCK, LOCK, state="NORMAL", rc="driver_lock"))
case("s7_ign", ["SWR-007", "SWR-020"],
     "ignition_on=false로 CRASH_RELEASE 종료(state OFF) 후 ignition_on=true 복귀 시 NORMAL이며 잠금 명령이 다시 적용 — 래치가 점화 사이클 후에도 남는 결함 검출",
     "CONFIRMED 해제 후 ignition_on = false → true, 이어서 DriverCommand(side=all, action=lock). crash_status는 NONE",
     sq, [REQB, ST], "High")

sq = Seq()
boot(sq)
lock_all(sq)
crash7(sq, {"sensor_fault": True}, E(REL, REL, pr="crash", rc="crash_confirmed"))
case("s7_sensor", ["SWR-007", "SWR-021", "SWR-022"],
     "충돌 확정(1순위)과 센서 고장(2순위)이 같은 평가에 동시 입력 — 두 출력 RELEASE, crash_confirmed. 센서 고장의 출력 유지가 충돌 해제를 막는 결함 검출 (SWR-022 ①+② 쌍)",
     "초기 LOCK/LOCK, sensor_fault = true 와 crash_status = CONFIRMED 동시 입력(7회 평가, +300 ms까지 유지)",
     sq, [REQB, EP], "High")

sq = Seq()
crash7(sq, {}, REL_CRASH)
sq.step(50, {"crash_status": "NONE"}, [C("all", "lock")], E(REL, REL, state="CRASH_RELEASE"))
case("s7_first", ["SWR-007"],
     "기동 후 첫 유효 입력이 CONFIRMED이고 출력이 이미 RELEASE인 경우에도 state=CRASH_RELEASE·crash_confirmed 기록 및 래치 — 출력이 바뀔 때만 동작하거나 NO_DATA 전이 평가에서 누락되는 결함 검출",
     "기동 직후 첫 VehicleSnapshot부터 crash_status = CONFIRMED 유지(7회), 이후 crash_status = NONE + DriverCommand(side=all, action=lock)",
     sq, [REQB, EP], "High")

sq = Seq()
boot(sq)
lock_all(sq)
wow = {"vehicle_speed_kph": 300.0, "rear_left_approach_risk": True, "rear_right_approach_risk": True,
       "isofix_left": True, "isofix_right": True, "sensor_fault": True}
for i in range(7):
    s = dict(wow)
    s["crash_status"] = "CONFIRMED"
    sq.step(50, s, [C("all", "lock")], E(REL, REL, pr="crash", rc="crash_confirmed") if i == 6 else None)
case("s7_wow", ["SWR-007", "SWR-022"],
     "WoW: 충돌 확정 + 속도 300.0 km/h(최대) + 좌·우 접근위험 + 좌·우 ISOFIX + 센서 고장 + 잠금 명령 매 주기 + 초기 LOCK/LOCK을 동시에 걸어도 300 ms 이내 두 출력 RELEASE — 다른 모든 규칙이 최대로 걸려 있을 때만 드러나는 순위 오류 검출",
     "vehicle_speed_kph = 300.0, 좌·우 접근위험 true, 좌·우 ISOFIX true, sensor_fault = true, crash_status = CONFIRMED, 매 주기 DriverCommand(side=all, action=lock), 초기 LOCK/LOCK",
     sq, [WOW, REQB], "High")

# =====================================================================
# SWR-008 PENDING
# =====================================================================
sq = Seq()
boot(sq)
lock_all(sq)
for i in range(7):
    sq.step(50, {"crash_status": "PENDING"}, exp=E(LOCK, LOCK, val="VALID", rc="crash_pending"))
case("s8_hold", ["SWR-008"],
     "PENDING에서는 긴급 해제하지 않고 출력 LOCK 유지, reason_code=crash_pending (7회 평가 = 300 ms 이상 유지해도 해제 안 함) — PENDING을 CONFIRMED처럼 처리하거나 타임아웃 후 해제하는 결함 검출",
     "초기 LOCK/LOCK, crash_status = PENDING 7회 유지, 정지 0.0 km/h",
     sq, [REQB, EP], "High")

sq = Seq()
boot(sq)
lock_all(sq)
sq.step(50, {"crash_status": "PENDING"}, exp=E(LOCK, LOCK, rc="crash_pending"))
sq.step(50, {"crash_status": "PENDING"}, exp=E(LOCK, LOCK, rc="crash_pending"))
crash7(sq, {}, REL_CRASH)
case("s8_confirm", ["SWR-008", "SWR-007"],
     "PENDING 다음 CONFIRMED → SWR-007 적용(300 ms 이내 RELEASE) — PENDING 이후 상태 전이에서 CONFIRMED 처리가 무시되는 결함 검출",
     "초기 LOCK/LOCK, crash_status = PENDING 2회 → CONFIRMED 7회",
     sq, [ST, REQB], "High")

sq = Seq()
boot(sq)
lock_left(sq)
sq.step(50, {"crash_status": "PENDING"}, exp=E(LOCK, REL, rc="crash_pending"))
sq.step(50, {"crash_status": "NONE"}, exp=E(LOCK, REL, state="NORMAL", pr="hold", rc="no_change"))
case("s8_none", ["SWR-008"],
     "PENDING 다음 NONE → 출력 변화 없음(LOCK/RELEASE 그대로), NORMAL 복귀, no_change — PENDING 해소 시 잘못 해제/잠금하거나 crash_pending 이유가 남는 결함 검출",
     "좌측 LOCK/우측 RELEASE, crash_status = PENDING → NONE",
     sq, [ST, REQB], "High")

sq = Seq()
boot(sq)
sq.step(50, {"crash_status": "PENDING", "rear_left_approach_risk": True}, exp=E(LOCK, REL, rc="approach_risk_left"))
sq.step(50, {"crash_status": "PENDING", "sensor_fault": True}, exp=E(LOCK, REL, rc="sensor_fault"))
sq.step(50, {"crash_status": "PENDING", "vehicle_speed_kph": 50.0}, exp=E(LOCK, LOCK, rc="crash_pending"))
sq.step(50, {"crash_status": "PENDING", "ignition_on": False}, exp=E(REL, REL, rc="crash_pending"))
sq.step(50, {"crash_status": "PENDING"}, [C("all", "lock")], E(LOCK, LOCK, rc="crash_pending"))
case("s8_rules", ["SWR-008", "SWR-022"],
     "PENDING 중 이유 코드 단일화 — 1~3순위 규칙(접근위험·센서 고장)이 있으면 그 규칙 코드, 4~8순위(자동 잠금·시동 꺼짐·명령)만 있으면 crash_pending — PENDING이 항상 이유를 덮어쓰거나 항상 양보하는 결함 검출",
     "crash_status = PENDING과 (a) 좌측 접근위험 (b) sensor_fault (c) 50.0 km/h (d) ignition_on=false (e) 잠금 명령을 각각 단독 결합(각 단계 독립)",
     sq, [EP, REQB, "결정 테이블"], "High")

# =====================================================================
# SWR-009 좌우 독립
# =====================================================================
sq = Seq()
boot(sq)
lock_all(sq)
sq.step(50, {"rear_left_approach_risk": True}, [C("all", "unlock")], E(LOCK, REL, pr="approach_risk", rc="approach_risk_left"))
case("s9_mixed", ["SWR-009", "SWR-005"],
     "좌측 접근위험 true·우측 false에서 side=all 해제 → 좌측 LOCK, 우측 RELEASE — 한쪽 접근위험이 all 명령 전체를 거절하는 결함 검출",
     "초기 LOCK/LOCK, rear_left_approach_risk = true(우측 false), DriverCommand(side=all, action=unlock)",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq)
sq.step(50, {"rear_right_approach_risk": True}, exp=E(REL, LOCK, rc="approach_risk_right"))
sq.step(50, {"rear_right_approach_risk": False, "isofix_right": True}, exp=E(REL, LOCK, rc="isofix_right"))
case("s9_right", ["SWR-009", "SWR-018"],
     "우측 전용 입력(우측 접근위험, 우측 ISOFIX)만 true — 좌측 출력은 RELEASE 그대로 — 도어별 입력이 반대쪽 출력에 새는(전체 출력에 적용) 결함 검출",
     "초기 RELEASE/RELEASE, rear_right_approach_risk = true → (false로 복귀하며) isofix_right = true, 좌측 입력은 모두 false",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq)
sq.step(50, {"rear_left_approach_risk": True, "isofix_right": True}, exp=E(LOCK, LOCK, pr="approach_risk", rc="approach_risk_left"))
case("s9_diff", ["SWR-009", "SWR-022"],
     "좌측은 접근위험(3순위), 우측은 ISOFIX(6순위)로 서로 다른 규칙 — 두 출력 LOCK, 평가의 priority_reason/reason_code는 높은 순위인 approach_risk/approach_risk_left — 한쪽 규칙 코드만 쓰거나 낮은 순위를 노출하는 결함 검출",
     "초기 RELEASE/RELEASE, rear_left_approach_risk = true 와 isofix_right = true 동시 입력",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq)
sq.step(50, {"rear_left_approach_risk": True, "rear_right_approach_risk": True}, exp=E(LOCK, LOCK, pr="approach_risk", rc="approach_risk_left"))
sq.step(50, {"isofix_left": True, "isofix_right": True}, exp=E(LOCK, LOCK, pr="isofix", rc="isofix_left"))
case("s9_tie", ["SWR-009", "SWR-022"],
     "좌·우가 같은 순위 규칙이면 좌측 이유 우선 — 좌·우 접근위험 동시 → approach_risk_left, 좌·우 ISOFIX 동시 → isofix_left — 동순위 타이브레이크가 우측이거나 마지막 평가 쪽으로 구현된 결함 검출",
     "좌·우 접근위험 동시 true → (false로 복귀하며) 좌·우 ISOFIX 동시 true",
     sq, [EP, REQB], "High")

# =====================================================================
# SWR-013 입력 검증 / freshness
# =====================================================================
sq = Seq()
sq.step(0, {"vehicle_speed_kph": 0.0}, exp=E(REL, REL, state="NORMAL", val="VALID"))
sq.step(50, {"vehicle_speed_kph": 300.0}, exp=E(LOCK, LOCK, val="VALID", rc="auto_lock_speed"))
case("s13_valid", ["SWR-013", "SWR-003"],
     "유효 경계값 — source_timestamp_s = 0.0(시계 0 ms), 속도 0.0과 300.0 km/h는 VALID로 처리(300.0에서 자동 잠금) — 범위를 `<`/`>`로 구현해 경계 유효값을 INVALID로 거부하는 결함 검출",
     "t=0 ms에 source_timestamp_s = 0.0, vehicle_speed_kph = 0.0 → 이후 vehicle_speed_kph = 300.0",
     sq, [BV, EP], "High")


def valid_refresh(sq, l, r):
    sq.step(50, {}, exp=E(l, r, state="NORMAL", val="VALID"))


def invalid_step(sq, l, r, bad=None, drop=None):
    sq.step(50, bad=bad or {}, drop=drop, exp=E(l, r, val="INVALID", pr="input_invalid", rc="input_invalid"))
    valid_refresh(sq, l, r)


sq = Seq()
boot(sq)
lock_left(sq)
for bad in [{"vehicle_speed_kph": 300.1}, {"vehicle_speed_kph": -0.1}, {"vehicle_speed_kph": 1000.0}, {"source_timestamp_s": -0.1}]:
    invalid_step(sq, LOCK, REL, bad=bad)
case("s13_range", ["SWR-013"],
     "범위 밖 값 각각(단계별 하나씩) — 300.1 / -0.1 km/h(경계 바깥), 1000.0 km/h(대표값), source_timestamp_s = -0.1 → INVALID, input_invalid, 출력(LOCK/RELEASE) 유지, 다음 유효 입력에서 VALID 복귀 — 상한/하한 한쪽만 검사하거나 음수 시각을 통과시키는 결함 검출",
     "vehicle_speed_kph = 300.1 / -0.1 / 1000.0, source_timestamp_s = -0.1 (각 단계 하나만 무효, 사이에 유효 입력)",
     sq, [BV, EP], "High")

sq = Seq()
boot(sq)
lock_left(sq)
for f in FIELD_ORDER:
    invalid_step(sq, LOCK, REL, drop=[f])
case("s13_missing", ["SWR-013"],
     "필드 누락 13종 각각(단계별 하나씩) → INVALID, input_invalid, 출력 유지 — 누락 필드를 기본값(false/0/NONE)으로 보완해 처리하는 결함 검출(특히 crash_status·ignition_on·sensor_fault)",
     "VehicleSnapshot에서 source_timestamp_s, vehicle_speed_kph, gear, crash_status, 불리언 9종을 각각 하나씩 제거 (사이에 유효 입력)",
     sq, [EP, ERR], "High")

sq = Seq()
boot(sq)
lock_left(sq)
for bad in [{"vehicle_speed_kph": "abc"}, {"vehicle_speed_kph": "3.0"}, {"vehicle_speed_kph": True},
            {"source_timestamp_s": "0.5"}, {"rear_left_approach_risk": "true"}, {"fire_detected": 1},
            {"ignition_on": 0}, {"sensor_fault": None}]:
    invalid_step(sq, LOCK, REL, bad=bad)
case("s13_type", ["SWR-013"],
     "형식 오류 각각(단계별 하나씩) — 속도 문자열 'abc'/'3.0', 속도 자리에 불리언 true, 시각 문자열, 불리언 자리에 'true'/1/0/null → INVALID, 출력 유지 — 느슨한 형 변환(문자열 숫자, 0/1 불리언, bool을 int로 인정)을 허용하는 결함 검출",
     "vehicle_speed_kph = \"abc\"/\"3.0\"/true, source_timestamp_s = \"0.5\", rear_left_approach_risk = \"true\", fire_detected = 1, ignition_on = 0, sensor_fault = null",
     sq, [EP, ERR], "High")

sq = Seq()
boot(sq)
lock_left(sq)
for bad in [{"crash_status": "UNKNOWN"}, {"crash_status": "confirmed"}, {"gear": "X"}, {"gear": "d"}]:
    invalid_step(sq, LOCK, REL, bad=bad)
case("s13_enum", ["SWR-013", "SWR-007"],
     "정의되지 않은 열거 값 각각 — crash_status 'UNKNOWN'/소문자 'confirmed', gear 'X'/소문자 'd' → INVALID, 출력 유지(특히 'confirmed'로 긴급 해제되지 않음) — 대소문자 무시 비교, gear 미검증(판정에 안 써도 검증 대상) 결함 검출",
     "crash_status = \"UNKNOWN\"/\"confirmed\", gear = \"X\"/\"d\"",
     sq, [EP, ERR], "High")

sq = Seq()
boot(sq)
lock_left(sq)
invalid_step(sq, LOCK, REL, bad={"vehicle_speed_kph": 301.0, "crash_status": "CONFIRMED"})
invalid_step(sq, LOCK, REL, bad={"vehicle_speed_kph": 301.0, "ignition_on": False})
invalid_step(sq, LOCK, REL, bad={"vehicle_speed_kph": -1.0, "fire_detected": True})
invalid_step(sq, LOCK, REL, bad={"vehicle_speed_kph": 301.0, "rear_right_approach_risk": True})
case("s13_unused", ["SWR-013", "SWR-022"],
     "무효 VehicleSnapshot은 판정에 쓰지 않는다 — 속도 범위 위반 묶음 안의 CONFIRMED/ignition_on=false/화재/우측 접근위험 값이 있어도 좌 LOCK/우 RELEASE 유지 — 필드별 부분 반영(유효해 보이는 필드만 사용) 결함 검출",
     "vehicle_speed_kph = 301.0 또는 -1.0 인 묶음에 crash_status=CONFIRMED / ignition_on=false / fire_detected=true / rear_right_approach_risk=true 를 각각 하나씩 포함",
     sq, [EP, ERR], "High")

sq = Seq()
boot(sq)
lock_all(sq)
bad_cmds = [
    {"side": "all", "action": "unlock", "source": "web"},
    {"side": "front", "action": "unlock", "source": "avn"},
    {"side": "all", "action": "toggle", "source": "avn"},
    {"action": "unlock", "source": "avn"},
    {"side": "all", "source": "avn"},
    {"side": "all", "action": "unlock"},
    {"side": "ALL", "action": "unlock", "source": "avn"},
    {"side": "all", "action": "unlock", "source": 123},
]
for bc in bad_cmds:
    sq.step(50, {}, [bc], E(LOCK, LOCK, val="VALID", rc="command_invalid"))
sq.step(50, {}, [{"side": "all", "action": "unlock", "source": "web"}, C("left", "unlock")], E(REL, LOCK))
case("s13_cmd", ["SWR-013"],
     "무효 DriverCommand 각각(단계별 하나씩) — 미등록 source 'web', side 'front', action 'toggle', 필드 누락 3종, 대문자 'ALL', source 숫자 → 적용 안 됨(LOCK/LOCK 유지), command_invalid. 무효 1건+유효 1건이 같은 주기에 오면 유효 건만 적용 — 무효 명령 적용, 필드 누락 기본값 보완, 무효 하나 때문에 같은 주기 유효 명령까지 버리는 결함 검출",
     "DriverCommand: source=web / side=front / action=toggle / side·action·source 각각 누락 / side=ALL / source=123 (모두 unlock 계열, 초기 LOCK/LOCK). 마지막: [무효 source=web all unlock, 유효 left unlock] 동시",
     sq, [EP, ERR], "High")

# freshness 경계: 200 ms
sq = Seq()
boot(sq)
sq.step(200, {}, [C("left", "lock")], E(LOCK, REL, val="VALID"))    # 스냅샷 시각 250 ms
sq.step(200, None, exp=E(LOCK, REL, state="NORMAL", val="VALID"))   # 나이 200 ms
sq.step(1, None, exp=E(LOCK, REL, state="DEGRADED", val="STALE", pr="input_stale", rc="input_stale"))  # 201 ms
case("s13_200", ["SWR-013", "SWR-023"],
     "freshness 경계 — 마지막 유효 스냅샷 후 200 ms에서는 VALID/NORMAL, 201 ms에서 STALE/DEGRADED(출력 유지, input_stale) — `>=`(200 ms에서 상실)로 구현되거나 상실 감지가 지연되는 결함 검출",
     "스냅샷 source_timestamp_s = 0.250 s 이후 스냅샷 없이 평가 시각 0.450 s(나이 200 ms) → 0.451 s(나이 201 ms)",
     sq, [BV, ST], "High")

sq = Seq()
boot(sq)
lock_left(sq)   # 마지막 스냅샷 100 ms
sq.step(50, None)
sq.step(50, None)
sq.step(50, None)
sq.step(50, None, exp=E(LOCK, REL, state="NORMAL", val="VALID"))    # 나이 200 ms
sq.step(50, None)                                                    # 나이 250 ms (판정 없음)
sq.step(50, None, exp=E(LOCK, REL, state="DEGRADED", val="STALE", pr="input_stale", rc="input_stale"))  # 나이 300 ms
case("s13_100", ["SWR-013", "SWR-023"],
     "상실 감지 시간 — 나이 200 ms까지 VALID, 200 ms 초과 후 100 ms 이내(나이 300 ms 평가까지)에 DEGRADED/STALE, 출력 유지 — 감지 지연 300 ms 초과(예: 임계 300 ms, 평가 2주기 지연) 결함 검출",
     "마지막 유효 스냅샷 t=100 ms 이후 스냅샷 없이 50 ms 간격 평가: 나이 50/100/150/200/250/300 ms",
     sq, [BV, REQB], "High", remarks="나이 250 ms 평가는 판정하지 않음(요구는 200 ms 초과 후 100 ms 이내이므로 250/300 ms 중 어느 시점 감지도 합격)")

sq = Seq()
boot(sq)
lock_all(sq)
for i in range(7):
    sq.step(50, None)
sq.step(50, None, [C("all", "unlock")], E(LOCK, LOCK, state="DEGRADED", val="STALE", pr="input_stale", rc="input_stale"))
sq.step(50, {}, exp=E(LOCK, LOCK, state="NORMAL", val="VALID"))
sq.step(50, {}, [C("all", "unlock")], E(REL, REL, state="NORMAL", val="VALID", rc="driver_unlock"))
case("s13_degraded", ["SWR-013", "SWR-004"],
     "DEGRADED 중 해제 명령은 적용되지 않고(input_stale) 새 유효 스냅샷으로 DEGRADED가 끝나며 이후 명령은 다시 적용 — DEGRADED 중 명령 적용, 복귀 후에도 명령 차단 상태가 남는 결함 검출",
     "초기 LOCK/LOCK, 스냅샷 중단 7주기(나이 350 ms) 후 나이 400 ms 평가에서 DriverCommand(side=all, action=unlock) → 유효 스냅샷 재수신(명령 없음) → DriverCommand(side=all, action=unlock)",
     sq, [ST, REQB, FI], "High")

sq = Seq()
boot(sq)
lock_left(sq)   # 마지막 유효 100 ms
for t_i in range(4):
    sq.step(50, bad={"vehicle_speed_kph": 400.0})   # 150/200/250/300 ms
sq.step(50, None)  # 350 ms (판정 없음)
sq.step(50, None, exp=E(LOCK, REL, state="DEGRADED", val="STALE", rc="input_stale"))  # 400 ms, 나이 300 ms
case("s13_invalid_fresh", ["SWR-013"],
     "무효 스냅샷은 freshness를 갱신하지 않는다 — 유효 스냅샷 후 무효 스냅샷만 4회 수신하고 이후 입력 없음, 마지막 유효 후 300 ms에 DEGRADED/STALE — 무효 입력 도착으로 마지막 수신 시각을 갱신해 DEGRADED가 지연/미발생하는 결함 검출",
     "마지막 유효 스냅샷 t=100 ms, 무효(vehicle_speed_kph = 400.0) 스냅샷 t=150/200/250/300 ms, 이후 입력 없음, 판정 t=400 ms",
     sq, [ST, ERR, FI], "High")

sq = Seq()
boot(sq)
lock_left(sq)   # 100 ms
sq.step(900, {"source_timestamp_s": 0.8}, exp=E(LOCK, REL, state="NORMAL", val="VALID"))   # 시계 1000 ms, 나이 0.200
sq.step(50, {"source_timestamp_s": 0.849}, exp=E(LOCK, REL, state="DEGRADED", val="STALE", rc="input_stale"))  # 시계 1050, 나이 0.201
sq.step(50, {"source_timestamp_s": 0.6}, exp=E(LOCK, REL, state="DEGRADED", val="STALE", rc="input_stale"))   # 나이 0.5
sq.step(50, {}, exp=E(LOCK, REL, state="NORMAL", val="VALID"))
case("s13_ts", ["SWR-013"],
     "freshness는 도착 시각이 아니라 source_timestamp_s 기준 — 방금 도착했지만 나이가 0.200 s(VALID), 0.201 s·0.500 s(STALE/DEGRADED)인 스냅샷, 이후 나이 0인 스냅샷에서 복귀 — 수신 시각 기준으로 구현되어 오래된 타임스탬프 데이터를 신선하다고 판단하는 결함 검출",
     "시계 1.000 s에 source_timestamp_s = 0.800(나이 0.200), 시계 1.050 s에 0.849(나이 0.201), 시계 1.100 s에 0.600(나이 0.500), 시계 1.150 s에 1.150(나이 0)",
     sq, [BV, ERR], "High")

# =====================================================================
# SWR-017 강제 해제
# =====================================================================
sq = Seq()
boot(sq)
lock_all(sq)
for flag, code in [("fire_detected", "fire"), ("overtemperature_detected", "overtemperature"), ("adult_present", "adult_present")]:
    sq.step(50, {flag: True}, exp=E(REL, REL, pr="forced_release", rc=code))
    sq.step(50, {}, [C("all", "lock")], E(LOCK, LOCK, rc="driver_lock"))
case("s17_single", ["SWR-017"],
     "입력 3종 단독 — fire/overtemperature/adult_present 각각 true인 다음 평가주기에 두 출력 RELEASE, 입력별 이유 코드(fire/overtemperature/adult_present) — 입력 하나가 누락되거나 이유 코드가 서로 바뀌는 결함 검출",
     "초기 LOCK/LOCK에서 fire_detected → overtemperature_detected → adult_present 를 순서대로 각각 단독 true (사이에 잠금 명령으로 LOCK 복귀)",
     sq, [EP, REQB], "Medium")

sq = Seq()
sq.step(50, {"vehicle_speed_kph": 50.0}, exp=E(LOCK, LOCK, state="NORMAL", val="VALID", rc="auto_lock_speed"))
sq.step(50, {"vehicle_speed_kph": 50.0, "adult_present": True}, exp=E(REL, REL, pr="forced_release", rc="adult_present"))
sq.step(50, {"vehicle_speed_kph": 50.0, "adult_present": True}, exp=E(REL, REL, rc="adult_present"))
sq.step(50, {"vehicle_speed_kph": 50.0, "adult_present": True}, [C("all", "lock")], E(REL, REL))
sq.step(50, {"vehicle_speed_kph": 50.0}, exp=E(LOCK, LOCK, pr="auto_lock", rc="auto_lock_speed"))
case("s17_adult_speed", ["SWR-017", "SWR-003"],
     "차속 50.0 km/h(자동 잠금 조건)에서 adult_present=true — 두 출력 RELEASE가 true인 동안 유지(자동 잠금·잠금 명령 차단), false가 되면 자동 잠금 재개 — 5순위가 한 주기만 적용되거나 6~8순위 잠금이 계속 적용되는 결함 검출",
     "vehicle_speed_kph = 50.0 유지, adult_present = true 3회(마지막은 잠금 명령 포함) → false",
     sq, [EP, REQB], "Medium")

sq = Seq()
boot(sq)
sq.step(50, {"fire_detected": True, "isofix_left": True}, exp=E(REL, REL, pr="forced_release", rc="fire"))
sq.step(50, {"fire_detected": True, "rear_left_approach_risk": True}, exp=E(LOCK, REL, pr="approach_risk", rc="approach_risk_left"))
case("s17_vs_upper", ["SWR-017", "SWR-018", "SWR-022"],
     "5순위 화재는 6순위 ISOFIX보다 우선(두 출력 RELEASE), 3순위 좌측 접근위험보다는 낮음(좌측 LOCK·우측 RELEASE) — 상·하위 순위 역전 결함 검출 (SWR-022 ⑤+⑥ 쌍과 ③ > ⑤)",
     "초기 RELEASE/RELEASE, fire_detected = true 와 isofix_left = true 동시 → fire_detected = true 와 rear_left_approach_risk = true 동시",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq)
sq.step(50, {"overtemperature_detected": True, "adult_present": True}, exp=E(REL, REL, rc="overtemperature"))
sq.step(50, {"fire_detected": True, "adult_present": True}, exp=E(REL, REL, rc="fire"))
sq.step(50, {"fire_detected": True, "overtemperature_detected": True}, exp=E(REL, REL, rc="fire"))
sq.step(50, {"fire_detected": True, "overtemperature_detected": True, "adult_present": True}, exp=E(REL, REL, rc="fire"))
case("s17_multi", ["SWR-017"],
     "복수 입력 동시 true 시 이유 코드 단일화(fire > overtemperature > adult_present) — (과온+성인)→overtemperature, (화재+성인)·(화재+과온)·세 입력→fire — 마지막 true 입력이나 열거 순서로 코드가 정해지는 결함 검출",
     "overtemperature+adult / fire+adult / fire+overtemperature / 세 입력 모두 true (각 단계 독립)",
     sq, [EP, "결정 테이블"], "Medium")

# =====================================================================
# SWR-018 ISOFIX
# =====================================================================
sq = Seq()
boot(sq)
sq.step(50, {"isofix_left": True}, exp=E(LOCK, REL, pr="isofix", rc="isofix_left"))
sq.step(50, {}, exp=E(LOCK, REL, pr="hold", rc="no_change"))
case("s18_left", ["SWR-018"],
     "isofix_left=true인 다음 평가주기에 좌측만 LOCK(우측 RELEASE 유지), isofix_left=false가 되어도 LOCK 유지(no_change) — 반대쪽 출력 변경, ISOFIX 해제 시 자동 RELEASE 결함 검출",
     "초기 RELEASE/RELEASE, isofix_left = true → false (명령 없음)",
     sq, [EP, REQB], "Medium")

sq = Seq()
boot(sq)
sq.step(50, {"isofix_right": True}, exp=E(REL, LOCK, pr="isofix", rc="isofix_right"))
sq.step(50, {"isofix_right": True}, [C("right", "unlock")], E(REL, LOCK, rc="driver_rejected"))
sq.step(50, {"isofix_left": True, "isofix_right": True}, exp=E(LOCK, LOCK, pr="isofix", rc="isofix_left"))
case("s18_right", ["SWR-018", "SWR-009"],
     "우측 ISOFIX: 우측만 LOCK·isofix_right, 우측 해제 명령 거절(driver_rejected), 좌·우 동시 true면 이유는 isofix_left — 좌/우 매핑 뒤바뀜, 우측 해제 허용 결함 검출",
     "초기 RELEASE/RELEASE, isofix_right = true, DriverCommand(side=right, action=unlock), 이어서 isofix_left = isofix_right = true",
     sq, [EP, REQB], "Medium")

sq = Seq()
boot(sq)
sq.step(50, {"isofix_left": True}, exp=E(LOCK, REL, rc="isofix_left"))
sq.step(50, {"isofix_left": True, "ignition_on": False}, exp=E(REL, REL, state="OFF", pr="ignition_off", rc="ignition_off"))
case("s18_ign", ["SWR-018", "SWR-020", "SWR-022"],
     "isofix_left=true와 ignition_on=false 동시 → 좌측 RELEASE(4순위 > 6순위) — ISOFIX가 시동 꺼짐 해제를 막는 순위 역전 결함 검출",
     "isofix_left = true로 좌측 LOCK 상태에서 isofix_left = true 유지 + ignition_on = false",
     sq, [EP, REQB], "High")

# =====================================================================
# SWR-020 시동 꺼짐
# =====================================================================
sq = Seq()
sq.step(50, {"vehicle_speed_kph": 50.0}, exp=E(LOCK, LOCK, state="NORMAL", val="VALID", rc="auto_lock_speed"))
for i in range(3):
    sq.step(50, {"vehicle_speed_kph": 50.0, "ignition_on": False}, exp=E(REL, REL, state="OFF", pr="ignition_off", rc="ignition_off"))
case("s20_off", ["SWR-020"],
     "ignition_on=false인 첫 평가주기에 두 출력 RELEASE, OFF, ignition_off이며 50.0 km/h여도 true인 동안 유지(자동 잠금 5~8순위 차단) — 첫 주기 지연, 한 주기만 해제되고 자동 잠금이 재개되는 결함 검출",
     "vehicle_speed_kph = 50.0으로 LOCK/LOCK 후 ignition_on = false 3주기 유지",
     sq, [EP, REQB], "Medium")

sq = Seq()
sq.step(50, {"ignition_on": False}, exp=E(REL, REL, state="OFF", val="VALID", pr="ignition_off", rc="ignition_off"))
sq.step(50, {"ignition_on": True}, exp=E(REL, REL, state="NORMAL", pr="hold", rc="no_change"))
sq.step(50, {"vehicle_speed_kph": 50.0}, exp=E(LOCK, LOCK, rc="auto_lock_speed"))
case("s20_on", ["SWR-020", "SWR-024"],
     "기동 후 첫 유효 입력이 ignition_on=false → OFF/ignition_off, ignition_on=true 복귀 시 RELEASE 유지·NORMAL(자동 복귀 잠금 없음), 이후 규칙이 다시 동작 — OFF 상태가 고착되거나 복귀 시 출력이 바뀌는 결함 검출",
     "기동 직후 첫 VehicleSnapshot ignition_on = false → true → (50.0 km/h)",
     sq, [EP, ST], "Medium")

# =====================================================================
# SWR-021 센서 고장
# =====================================================================
FAULT = dict(state="FAULT", pr="sensor_fault", rc="sensor_fault", wc="W_SENSOR_FAULT")
sq = Seq()
boot(sq)
lock_left(sq)
sq.step(50, {"sensor_fault": True}, exp=E(LOCK, REL, **FAULT))
case("s21_hold", ["SWR-021"],
     "sensor_fault=true인 첫 평가주기에 좌 LOCK·우 RELEASE 유지, FAULT, W_SENSOR_FAULT, sensor_fault — 고장 시 안전측으로 전부 해제/잠금하거나 경고 코드 누락 결함 검출",
     "좌측 LOCK/우측 RELEASE에서 sensor_fault = true",
     sq, [EP, REQB, ST], "High")

sq = Seq()
boot(sq)
lock_left(sq)
sq.step(50, {"sensor_fault": True}, [C("left", "unlock")], E(LOCK, REL, **FAULT))
sq.step(50, {"sensor_fault": True, "vehicle_speed_kph": 50.0}, exp=E(LOCK, REL, **FAULT))
sq.step(50, {"sensor_fault": True, "isofix_right": True}, exp=E(LOCK, REL, **FAULT))
sq.step(50, {"sensor_fault": True, "fire_detected": True}, exp=E(LOCK, REL, **FAULT))
sq.step(50, {"sensor_fault": True, "rear_right_approach_risk": True}, exp=E(LOCK, REL, **FAULT))
sq.step(50, {"sensor_fault": True, "ignition_on": False}, exp=E(LOCK, REL, pr="sensor_fault", rc="sensor_fault", wc="W_SENSOR_FAULT"))
case("s21_rules", ["SWR-021", "SWR-022"],
     "FAULT 중 3~8순위 각각(해제 명령 / 50.0 km/h / 우측 ISOFIX / 화재 / 우측 접근위험 / 시동 꺼짐)을 단독으로 넣어도 출력 LOCK/RELEASE 유지 — 하위 규칙 중 하나라도 FAULT를 뚫는 결함(특히 접근위험·시동 꺼짐 순위 오류) 검출",
     "sensor_fault = true 유지 + (a) 좌측 해제 명령 (b) 50.0 km/h (c) isofix_right (d) fire_detected (e) rear_right_approach_risk (f) ignition_on=false 를 각 단계 하나씩",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq)
lock_all(sq)
sq.step(50, {"sensor_fault": True}, exp=E(LOCK, LOCK, **FAULT))
crash7(sq, {"sensor_fault": True}, E(REL, REL, pr="crash", rc="crash_confirmed"))
case("s21_crash", ["SWR-021", "SWR-007"],
     "FAULT 중 충돌 CONFIRMED가 들어오면 300 ms 이내 두 출력 RELEASE(충돌은 고장 유지보다 우선) — 센서 고장 중 충돌 입력을 무시하는 결함 검출",
     "초기 LOCK/LOCK, sensor_fault = true 로 FAULT 진입 후 crash_status = CONFIRMED (sensor_fault 유지)",
     sq, [REQB, ST], "High")

sq = Seq()
boot(sq)
lock_left(sq)
sq.step(50, {"sensor_fault": True}, exp=E(LOCK, REL, **FAULT))
sq.step(50, {"vehicle_speed_kph": 50.0}, exp=E(LOCK, LOCK, state="NORMAL", pr="auto_lock", rc="auto_lock_speed", wc=None))
sq.step(50, {}, [C("all", "unlock")], E(REL, REL, state="NORMAL", rc="driver_unlock", wc=None))
case("s21_clear", ["SWR-021"],
     "sensor_fault=false가 된 평가주기부터 정상 판정(50.0 km/h 자동 잠금, 이후 해제 명령 적용), 상태 NORMAL, warning_code 없음(null) — FAULT/경고가 고착되거나 복귀 평가가 한 주기 늦는 결함 검출",
     "FAULT 진입 후 sensor_fault = false + vehicle_speed_kph = 50.0, 이어서 속도 0.0 + DriverCommand(side=all, action=unlock)",
     sq, [ST, REQB], "High")

sq = Seq()
sq.step(50, {"sensor_fault": True}, exp=E(REL, REL, state="FAULT", val="VALID", pr="sensor_fault", rc="sensor_fault", wc="W_SENSOR_FAULT"))
sq.step(50, {"sensor_fault": True}, [C("all", "lock")], E(REL, REL, **FAULT))
case("s21_first", ["SWR-021", "SWR-024"],
     "기동 후 첫 유효 입력부터 sensor_fault=true — 출력 RELEASE 유지·FAULT, 잠금 명령 미적용 — 확정 출력이 정의되기 전(초기값) 고장 처리와 NO_DATA→FAULT 전이 결함 검출",
     "기동 직후 첫 VehicleSnapshot부터 sensor_fault = true, DriverCommand(side=all, action=lock)",
     sq, [EP, ST], "High")

# =====================================================================
# SWR-022 우선순위 (인접 쌍)
# =====================================================================
sq = Seq()
boot(sq)
sq.step(50, {"sensor_fault": True, "rear_left_approach_risk": True}, exp=E(REL, REL, pr="sensor_fault", rc="sensor_fault"))
case("s22_23", ["SWR-022", "SWR-021", "SWR-005"],
     "②+③: 센서 고장과 좌측 접근위험 동시 — 접근위험 잠금이 적용되지 않고 출력 유지(RELEASE/RELEASE), priority_reason=sensor_fault — 2·3순위 역전 결함 검출",
     "초기 RELEASE/RELEASE, sensor_fault = true 와 rear_left_approach_risk = true 동시",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq)
sq.step(50, {"rear_left_approach_risk": True, "ignition_on": False}, exp=E(LOCK, REL, pr="approach_risk", rc="approach_risk_left"))
case("s22_34", ["SWR-022", "SWR-005", "SWR-020"],
     "③+④: 초기 RELEASE에서 좌측 접근위험과 시동 꺼짐 동시 — 좌측 LOCK(접근위험이 실제로 잠금), 우측 RELEASE. 직전 출력이 LOCK이면 구분되지 않는 '유지' 구현을 배제",
     "초기 RELEASE/RELEASE, rear_left_approach_risk = true 와 ignition_on = false 동시",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq)
lock_all(sq)
sq.step(50, {"ignition_on": False, "fire_detected": True}, exp=E(REL, REL, state="OFF", pr="ignition_off", rc="ignition_off"))
case("s22_45", ["SWR-022", "SWR-020", "SWR-017"],
     "④+⑤: 시동 꺼짐과 화재 동시 — 두 출력 RELEASE이고 priority_reason=ignition_off, reason_code=ignition_off(fire 아님) — 4·5순위 이유 코드 역전 결함 검출",
     "초기 LOCK/LOCK, ignition_on = false 와 fire_detected = true 동시",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq)
sq.step(50, {"isofix_left": True, "vehicle_speed_kph": 50.0}, exp=E(LOCK, LOCK, pr="isofix", rc="isofix_left"))
case("s22_67", ["SWR-022", "SWR-018", "SWR-003"],
     "⑥+⑦: 좌측 ISOFIX와 50.0 km/h 동시 — 두 출력 LOCK, priority_reason=isofix, reason_code=isofix_left(auto_lock_speed 아님) — 6·7순위 이유 역전 결함 검출",
     "초기 RELEASE/RELEASE, isofix_left = true 와 vehicle_speed_kph = 50.0 동시",
     sq, [EP, REQB], "Medium")

sq = Seq()
boot(sq)
lock_all(sq)
sq.step(50, {"isofix_left": True}, [C("right", "unlock")], E(LOCK, REL, pr="isofix", rc="isofix_left"))
case("s22_mixed", ["SWR-022", "SWR-018"],
     "SWR-022 예시: 좌측 ISOFIX(⑥)와 우측 운전자 해제(⑧) 동시 — 좌 LOCK·우 RELEASE, priority_reason=isofix, reason_code=isofix_left (우측 명령 이유가 노출되는 결함 검출)",
     "초기 LOCK/LOCK, isofix_left = true 와 DriverCommand(side=right, action=unlock) 동시",
     sq, [EP, REQB], "High")

sq = Seq()
boot(sq)
sq.step(50, {"isofix_right": True}, [C("left", "lock")], E(LOCK, LOCK, pr="isofix", rc="isofix_right"))
case("s22_right", ["SWR-022", "SWR-018", "SWR-009"],
     "우측 ISOFIX(⑥)와 좌측 운전자 잠금(⑧) 동시 — 두 출력 LOCK, 높은 순위 규칙이 우측 것이므로 reason_code=isofix_right (이유를 항상 좌측 기준으로 만드는 결함 검출)",
     "초기 RELEASE/RELEASE, isofix_right = true 와 DriverCommand(side=left, action=lock) 동시",
     sq, [EP, REQB], "High")

wow2 ={"rear_left_approach_risk": True, "ignition_on": False, "fire_detected": True, "overtemperature_detected": True,
        "adult_present": True, "isofix_left": True, "isofix_right": True, "vehicle_speed_kph": 300.0}
# 직전 출력을 (좌 RELEASE, 우 LOCK)으로 만들기 위해 별도 케이스 구성
sq = Seq()
boot(sq)
sq.step(50, {}, [C("right", "lock")], E(REL, LOCK, rc="driver_lock"))
sq.step(50, wow2, [C("all", "lock")], E(LOCK, REL, pr="approach_risk", rc="approach_risk_left"))
case("s22_wow", ["SWR-022"],
     "WoW: 충돌·센서 고장을 제외한 모든 규칙을 동시에 최대로 거는 상황 — 좌측 접근위험 + 시동 꺼짐 + 화재·과열·성인 + 양쪽 ISOFIX + 300.0 km/h + 전체 잠금 명령. 직전 출력 좌 RELEASE/우 LOCK에서 좌 LOCK(3순위), 우 RELEASE(4순위), approach_risk_left — 하위 규칙 사이 순위 처리 오류 검출",
     "직전 좌 RELEASE/우 LOCK, rear_left_approach_risk = true, ignition_on = false, fire/overtemperature/adult = true, isofix 좌우 true, vehicle_speed_kph = 300.0, DriverCommand(side=all, action=lock)",
     sq, [WOW, REQB], "High", proposed=True)

# =====================================================================
# SWR-022 페어와이즈 (PICT)
# =====================================================================
PICT_ROWS = []
with open(os.path.join(HERE, "pict_result_SWR-022.tsv"), encoding="utf-8") as f:
    PICT_ROWS = list(csv.DictReader(f, delimiter="\t"))

RANK_PR = {1: "crash", 2: "sensor_fault", 3: "approach_risk", 4: "ignition_off", 5: "forced_release",
           6: "isofix", 7: "auto_lock", 8: "driver_command"}


def oracle(r):
    crash, sensor, riskl = r["CRASH"], r["SENSOR"] == "on", r["RISKL"] == "on"
    ign, forced, isol = r["IGN"] == "on", r["FORCED"], r["ISOFIXL"] == "on"
    speed, cmd, prior = float(r["SPEED"]), r["CMD"], r["PRIOR"]
    L = LOCK if prior[0] == "L" else REL
    R = LOCK if prior[1] == "L" else REL
    targets = {"none": [], "lock_left": [("L", LOCK)], "unlock_left": [("L", REL)],
               "unlock_all": [("L", REL), ("R", REL)]}[cmd]
    tdict = dict(targets)
    out, ranks, codes = {}, {}, {}
    forced_code = {"fire": "fire", "overtemp": "overtemperature", "adult": "adult_present"}.get(forced)
    for side, prev in (("L", L), ("R", R)):
        if crash == "CONFIRMED":
            rk, v, code = 1, REL, "crash_confirmed"
        elif sensor:
            rk, v, code = 2, prev, "sensor_fault"
        elif side == "L" and riskl:
            rk, v, code = 3, LOCK, "approach_risk_left"
        elif not ign:
            rk, v, code = 4, REL, "ignition_off"
        elif forced != "none":
            rk, v, code = 5, REL, forced_code
        elif side == "L" and isol:
            rk, v, code = 6, LOCK, "isofix_left"
        elif speed >= 3.0:
            rk, v, code = 7, LOCK, "auto_lock_speed"
        elif side in tdict:
            rk, v, code = 8, tdict[side], "driver_lock" if tdict[side] == LOCK else "driver_unlock"
        else:
            rk, v, code = None, prev, None
        out[side], ranks[side], codes[side] = v, rk, code
    cand = [(ranks[s], 0 if s == "L" else 1, s) for s in "LR" if ranks[s] is not None]
    exp = E(out["L"], out["R"], val="VALID")
    if sensor is False:
        exp["warning_code"] = None
    if not cand:
        exp["priority_reason"] = "hold"
        best = None
        exp["reason_code"] = "crash_pending" if crash == "PENDING" else "no_change"
        return exp
    best_rank, _, best_side = min(cand)
    exp["priority_reason"] = RANK_PR[best_rank]
    blocked_ambiguous = best_rank >= 4 and any(
        (ranks[s] is not None and 4 <= ranks[s] <= 7) for s in tdict)
    if best_rank >= 4 and crash == "PENDING":
        if not blocked_ambiguous:
            exp["reason_code"] = "crash_pending"
    elif best_rank >= 4 and blocked_ambiguous:
        pass     # 같은 출력에서 4~7순위가 명령을 막을 때 reason_code(driver_rejected 여부)는 판정하지 않음
    else:
        exp["reason_code"] = codes[best_side]
    return exp


def cmds_of(cmd):
    return {"none": None, "lock_left": [C("left", "lock")], "unlock_left": [C("left", "unlock")],
            "unlock_all": [C("all", "unlock")]}[cmd]


PW_KEYS = []
for i, row in enumerate(PICT_ROWS, 1):
    sq = Seq()
    boot(sq)
    if row["PRIOR"] == "LL":
        lock_all(sq)
    elif row["PRIOR"] == "LR":
        lock_left(sq)
    snap = {
        "crash_status": row["CRASH"], "sensor_fault": row["SENSOR"] == "on",
        "rear_left_approach_risk": row["RISKL"] == "on", "ignition_on": row["IGN"] == "on",
        "fire_detected": row["FORCED"] == "fire", "overtemperature_detected": row["FORCED"] == "overtemp",
        "adult_present": row["FORCED"] == "adult", "isofix_left": row["ISOFIXL"] == "on",
        "vehicle_speed_kph": float(row["SPEED"]),
    }
    sq.step(50, snap, cmds_of(row["CMD"]), oracle(row))
    key = f"pw{i:02d}"
    PW_KEYS.append(key)
    desc = " / ".join(f"{k}={row[k]}" for k in ["CRASH", "SENSOR", "RISKL", "IGN", "FORCED", "ISOFIXL", "SPEED", "CMD", "PRIOR"])
    case(key, ["SWR-022"],
         f"페어와이즈 조합 {i:02d}/{len(PICT_ROWS)}: 규칙 입력 9개 파라미터의 2-way 조합에서 가장 높은 순위 규칙의 출력·priority_reason이 나오는지 확인 — 인접하지 않은 순위 사이, 직전 출력, 명령과의 상호작용에서 생기는 순위 오류 검출",
         f"PICT 행 {i:02d}: {desc}",
         sq, [PW, REQB], "High", pre=PRE_FRESH + "; 직전 출력은 PRIOR 값(RR=RELEASE/RELEASE, LL=LOCK/LOCK, LR=좌 LOCK/우 RELEASE)을 사전 단계로 설정",
         remarks="기대값은 SWR-022 우선순위 표에서 도출. 같은 출력에서 4~7순위가 운전자 명령을 막는 조합의 reason_code(driver_rejected 여부)는 판정하지 않음(미결 Q-07)")

# =====================================================================
# SWR-024 초기 상태
# =====================================================================
sq = Seq()
sq.step(50, None, exp=E(REL, REL, state="OFF", val="NO_DATA"))
for i in range(2):
    sq.step(50, None, [C("all", "lock")], E(REL, REL, state="OFF", val="NO_DATA"))
for i in range(6):
    sq.step(50, None, exp=E(REL, REL, state="OFF", val="NO_DATA") if i == 5 else None)
sq.step(50, {}, exp=E(REL, REL, state="NORMAL", val="VALID"))
sq.step(50, {}, [C("all", "lock")], E(LOCK, LOCK, state="NORMAL", val="VALID", rc="driver_lock"))
case("s24_init", ["SWR-024", "SWR-013"],
     "기동 직후 RELEASE/RELEASE·OFF·NO_DATA, 유효 입력 전 잠금 명령 미적용, 스냅샷 없이 450 ms가 지나도 NO_DATA 유지(STALE/DEGRADED로 가지 않음), 첫 유효 입력(ignition_on=true)에서 NORMAL/VALID, 이후 명령 적용 — 초기값 오류와 첫 수신 전 freshness 타이머가 기동 시각부터 도는 결함 검출",
     "기동 직후 스냅샷 없이 평가 + DriverCommand(side=all, action=lock) 2회, 스냅샷 없이 6주기, 첫 VehicleSnapshot(기본값), 이어서 DriverCommand(side=all, action=lock)",
     sq, [EP, REQB, ST], "Medium")

sq = Seq()
sq.step(50, bad={"vehicle_speed_kph": 400.0}, exp=None)
sq.step(50, bad={"vehicle_speed_kph": 400.0}, cmds=[C("all", "lock")], exp=E(REL, REL))
sq.step(50, {}, exp=E(REL, REL, state="NORMAL", val="VALID"))
case("s24_invalid_first", ["SWR-024", "SWR-013"],
     "기동 후 무효 스냅샷(속도 400.0 km/h)만 들어온 상태의 잠금 명령은 적용되지 않음(첫 '유효' 입력 전), 이후 유효 입력에서 NORMAL — 무효 입력 도착을 '첫 입력 수신'으로 처리해 명령을 풀어 주는 결함 검출",
     "기동 직후 vehicle_speed_kph = 400.0(무효) 스냅샷 2회와 DriverCommand(side=all, action=lock), 이어서 유효 스냅샷",
     sq, [EP, ERR], "Medium")

# --- [제안] 거절된 명령의 보존 여부
sq = Seq()
sq.step(50, None, [C("all", "lock")], E(REL, REL, state="OFF", val="NO_DATA"))
sq.step(50, {}, exp=E(REL, REL, state="NORMAL", val="VALID"))
case("p_nodata_retain", ["SWR-024"],
     "유효 입력 전에 받은 잠금 명령이 첫 유효 스냅샷 평가에서 뒤늦게 적용되지 않음 — 거절된 명령을 큐에 남기는 결함 검출 (요구가 직접 규정하지 않은 보존 여부를 확인)",
     "기동 직후 스냅샷 없이 DriverCommand(side=all, action=lock) 1회, 다음 평가에서 첫 VehicleSnapshot(기본값, 명령 없음)",
     sq, [ERR, ST], "Medium", proposed=True,
     remarks="가정: '적용하지 않는다'는 폐기를 뜻함(Q-09 참조)")

sq = Seq()
boot(sq)
lock_all(sq)
for i in range(7):
    sq.step(50, None)
sq.step(50, None, [C("all", "unlock")], E(LOCK, LOCK, state="DEGRADED", val="STALE", rc="input_stale"))
sq.step(50, {}, exp=E(LOCK, LOCK, state="NORMAL", val="VALID"))
case("p_degraded_retain", ["SWR-013"],
     "DEGRADED 중 받은 해제 명령이 복귀 평가에서 뒤늦게 적용되지 않음 — 거절 명령을 보존했다가 복귀 시 적용하는 결함 검출 (요구가 직접 규정하지 않은 보존 여부)",
     "초기 LOCK/LOCK, 스냅샷 중단 중 DriverCommand(side=all, action=unlock) 1회, 이후 유효 스냅샷(명령 없음)",
     sq, [ERR, ST], "Medium", proposed=True,
     remarks="가정: '적용하지 않는다'는 폐기를 뜻함(Q-09 참조)")

# =====================================================================
# SWR-023 평가 주기 / 명령 순서 (벡터 가능)
# =====================================================================
def ord_sim(cmds, start=(REL, REL)):
    L, R = start
    for c in cmds:
        v = LOCK if c["action"] == "lock" else REL
        if c["side"] in ("left", "all"):
            L = v
        if c["side"] in ("right", "all"):
            R = v
    return L, R


sq = Seq()
boot(sq)
cmds_a = [C("left", "lock"), C("left", "unlock")]
sq.step(50, {}, cmds_a, E(*ord_sim(cmds_a)))
cmds_b = [C("left", "unlock"), C("left", "lock")]
sq.step(50, {}, cmds_b, E(*ord_sim(cmds_b, (REL, REL))))
cmds_c = [C("right", "lock"), C("all", "lock"), C("left", "unlock")]
sq.step(50, {}, cmds_c, E(*ord_sim(cmds_c, (LOCK, REL))))
case("n23_order", ["SWR-023", "SWR-001", "SWR-002"],
     "한 평가주기에 받은 명령은 받은 순서대로 적용 — (좌 잠금, 좌 해제)→좌 RELEASE, (좌 해제, 좌 잠금)→좌 LOCK, (우 잠금, 전체 잠금, 좌 해제)→좌 RELEASE/우 LOCK — 마지막/첫 명령만 쓰거나 역순·side별 그룹 순으로 적용하는 결함 검출",
     "동일 주기 DriverCommand 목록 (a) [left lock, left unlock] (b) [left unlock, left lock] (c) [right lock, all lock, left unlock]",
     sq, [REQB, EP], "High", cat="non-functional")

sq = Seq()
seq10 =[C("all", "lock", "physical_button"), C("left", "unlock", "avn"), C("right", "unlock", "voice"),
         C("all", "lock", "mobile_app"), C("left", "unlock", "physical_button"), C("right", "lock", "avn"),
         C("all", "unlock", "voice"), C("left", "lock", "mobile_app"), C("right", "lock", "physical_button"),
         C("left", "unlock", "avn")]
sq.step(50, {"vehicle_speed_kph": 2.9}, exp=E(REL, REL, state="NORMAL", val="VALID"))
sq.step(50, {"vehicle_speed_kph": 2.9}, seq10, E(*ord_sim(seq10)))
case("n23_wow", ["SWR-023", "SWR-001", "SWR-002", "SWR-003"],
     "WoW: 한 평가주기에 명령 10건(4종 source × 3종 side × lock/unlock 혼합) + 속도 2.9 km/h(자동 잠금 직전) 동시 — 순차 적용 결과(좌 RELEASE/우 LOCK)가 나오는지 확인 — 다수 명령 처리 중 중간 상태 유실, 큐 길이 제한, 임계 직하 속도에서의 오동작 검출",
     "동일 주기 DriverCommand 10건 [all lock, left unlock, right unlock, all lock, left unlock, right lock, all unlock, left lock, right lock, left unlock], vehicle_speed_kph = 2.9",
     sq, [WOW, "상태 전이"], "Medium", proposed=True, cat="non-functional")

# =====================================================================
# 벡터 없는 케이스 (이력, 상태 조회, Web, 재생)
# =====================================================================
ENV_EV = "PC/SIL (Python 3.12 childlock, 고정 시계). 결정 이력(Event) 조회 API/함수로 확인"
ENV_WEB = "Web (FastAPI 시뮬레이터: POST /api/snapshot, /api/command, /api/step, GET /api/status, /api/events)"

case("n10_ids", ["SWR-010"],
     "평가 5회 후 event_id = 1,2,3,4,5 — 평가마다 정확히 1건, 입력이 없거나(NO_DATA)·무효이거나·명령이 없어도 건너뛰지 않음. 무효/무입력 평가에서 이벤트를 만들지 않거나 id를 건너뛰는 결함 검출",
     "평가 5회: (1) 스냅샷 없음 (2) 유효 스냅샷(기본값) (3) 무효 스냅샷(vehicle_speed_kph=300.1) (4) 유효 스냅샷+DriverCommand(side=all, action=lock, source=avn) (5) 스냅샷·명령 없음",
     procedure="1. childlock을 새로 기동하고 시계 0 ms에서 시작\n2. 시계 +50 ms, 스냅샷 없음, 평가 1회\n3. 시계 +50 ms, 기본값 VehicleSnapshot 제출, 평가 1회\n4. 시계 +50 ms, vehicle_speed_kph=300.1 VehicleSnapshot 제출, 평가 1회\n5. 시계 +50 ms, 기본값 VehicleSnapshot과 DriverCommand(all, lock, avn) 제출, 평가 1회\n6. 시계 +50 ms, 제출 없음, 평가 1회\n7. 결정 이력을 조회하여 event_id 목록 확인",
     expected="이력 5건, event_id = [1, 2, 3, 4, 5] (순서·연속). 평가 횟수와 이벤트 수가 같다",
     pass_criteria="event_id 목록이 정확히 [1,2,3,4,5]",
     techniques=[REQB, EP, ERR], priority="Medium", env=ENV_EV, cat="non-functional")

case("n10_restart", ["SWR-010"],
     "재기동 후 첫 이벤트의 event_id가 다시 1 — 프로세스 전역 카운터가 모듈 재사용/영속 저장으로 이어지는 결함 검출",
     "평가 3회 실행 후 childlock 프로세스 종료·재기동, 평가 1회",
     procedure="1. childlock 기동, 평가 3회 실행(50 ms 간격, 기본값 스냅샷), event_id [1,2,3] 확인\n2. 프로세스를 종료하고 새 프로세스로 childlock 재기동(시계 0 ms)\n3. 시계 +50 ms, 기본값 스냅샷 제출, 평가 1회\n4. 결정 이력 조회",
     expected="재기동 후 이력은 1건이고 event_id = 1",
     pass_criteria="재기동 후 첫 이벤트 event_id == 1, 이력 건수 == 1",
     techniques=[REQB, ERR], priority="Medium", env="PC/SIL (프로세스 재기동 필요: 별도 프로세스 2회 실행)", cat="non-functional")

case("n10_multi", ["SWR-010"],
     "한 평가주기에 DriverCommand 3건을 받아도 이벤트는 1건(event_id 1씩 증가) — 명령 1건당 이벤트를 만드는 결함 검출",
     "기본값 스냅샷과 같은 주기에 DriverCommand 3건 [left lock, right lock, all unlock], 이후 평가 1회",
     procedure="1. childlock 기동, 시계 +50 ms, 기본값 스냅샷과 DriverCommand 3건(left lock, right lock, all unlock; source=avn) 제출, 평가 1회\n2. 시계 +50 ms, 기본값 스냅샷 제출, 평가 1회\n3. 결정 이력 조회",
     expected="이력 2건, event_id = [1, 2]",
     pass_criteria="이벤트 수 == 평가 수 == 2, event_id == [1,2]",
     techniques=[REQB, EP], priority="Medium", env=ENV_EV, cat="non-functional")

case("n11_fields", ["SWR-011"],
     "모든 입력 종류를 넣은 뒤 각 이벤트의 필드 집합이 허용 8개(event_id, timestamp_s, state, lock_left, lock_right, priority_reason, reason_code, input_validity)와 정확히 같다 — DriverCommand source·원본 스냅샷 값·개인정보 필드 혼입 결함 검출. timestamp_s는 판정에 쓴 입력의 source_timestamp_s와 같다",
     "6종 입력을 순차 평가: 유효 스냅샷+4종 source 명령(physical_button/avn/voice/mobile_app), 무효 스냅샷(속도 300.1), 스냅샷 중단으로 STALE, sensor_fault=true, crash_status=CONFIRMED",
     procedure="1. childlock 기동, 50 ms 간격으로 기본값 스냅샷과 DriverCommand(all, lock, source=physical_button/avn/voice/mobile_app 각 1회씩, 평가 4회) 제출\n2. 무효 스냅샷(vehicle_speed_kph=300.1) 제출 후 평가\n3. 유효 스냅샷 1회 후 스냅샷 없이 평가 6회(STALE 유도)\n4. 유효 스냅샷(sensor_fault=true) 평가, 이어서 유효 스냅샷(crash_status=CONFIRMED) 평가\n5. 결정 이력 전체 조회, 각 이벤트의 키 집합과 timestamp_s 확인",
     expected="모든 이벤트의 키 집합 == {event_id, timestamp_s, state, lock_left, lock_right, priority_reason, reason_code, input_validity} (8개, 추가·누락 없음). 'source' 키와 값이 이벤트 어디에도 없음. 스냅샷이 제출된 평가의 timestamp_s == 그 스냅샷의 source_timestamp_s",
     pass_criteria="모든 이벤트에서 키 집합이 허용 8개와 정확히 일치",
     techniques=[REQB, EP], priority="Medium", env=ENV_EV, cat="non-functional")

case("n11_extra", ["SWR-011"],
     "허용되지 않은 추가 필드(user_name, phone, device_id)가 섞인 입력을 받아도(수락·거절 불문) 이벤트 필드는 허용 8개뿐이고 입력의 개인정보 값이 이벤트에 나타나지 않음 — 입력 dict 통째 저장 결함 검출",
     "VehicleSnapshot에 user_name=\"홍길동\", phone=\"010-0000-0000\", device_id=\"DEV-123\" 추가 필드, DriverCommand에 account=\"user01\" 추가 필드",
     procedure="1. childlock 기동, 시계 +50 ms\n2. 기본값 VehicleSnapshot에 user_name=\"홍길동\", phone=\"010-0000-0000\", device_id=\"DEV-123\"를 추가하고 DriverCommand(all, lock, avn)에 account=\"user01\"를 추가해 제출, 평가 1회\n3. 결정 이력 조회 후 전체 이벤트를 JSON 문자열로 직렬화\n4. 키 집합 확인과 문자열 '홍길동', '010-0000-0000', 'DEV-123', 'user01' 검색",
     expected="이벤트 키 집합 == 허용 8개(수락 여부와 무관). 직렬화 문자열에 4개 값이 하나도 없음",
     pass_criteria="키 집합 일치 AND 4개 문자열 미검출",
     techniques=[ERR, EP], priority="Medium", env=ENV_EV, cat="non-functional", proposed=True,
     remarks="추가 필드 수락/거절은 명세에 없어 판정하지 않음(Q-08)")

case("n12_100", ["SWR-012"],
     "이력 경계 99/100건 — 평가 99회 후 99건, 100회 후 100건(event_id 1~100, 오름차순) — 용량을 99로 구현하거나 100건째에서 이미 버리는 off-by-one 결함 검출",
     "평가 99회 → 조회, 평가 1회 추가(누적 100회) → 조회 (50 ms 간격, 기본값 스냅샷, 명령 없음)",
     procedure="1. childlock 기동, 50 ms 간격 기본값 스냅샷으로 평가 99회\n2. 결정 이력 조회: 건수와 event_id 확인\n3. 평가 1회 추가(누적 100회)\n4. 결정 이력 조회: 건수, event_id 목록, 정렬 확인",
     expected="99회 후 99건(event_id 1~99). 100회 후 100건, event_id = 1~100, 오름차순",
     pass_criteria="건수 99, 100 및 event_id 정렬이 기대와 일치",
     techniques=[BV, REQB], priority="Medium", env=ENV_EV, cat="non-functional")

case("n12_101", ["SWR-012"],
     "이력 경계 101건 — 평가 101회 후 조회 결과가 event_id 2~101의 100건, 오름차순 — 가장 오래된 것이 아닌 최신 것을 버리거나, 100건 초과 시 전부 초기화/정렬 깨짐 결함 검출",
     "평가 101회 (50 ms 간격, 기본값 스냅샷, 명령 없음)",
     procedure="1. childlock 기동, 50 ms 간격 기본값 스냅샷으로 평가 101회\n2. 결정 이력 조회\n3. 건수, 첫·마지막 event_id, 오름차순 여부 확인",
     expected="100건, event_id = 2..101, 오름차순 (event_id 1 없음)",
     pass_criteria="건수 100, 첫 id 2, 마지막 id 101, 연속 오름차순",
     techniques=[BV, REQB], priority="High", env=ENV_EV, cat="non-functional")

case("n12_restart", ["SWR-012"],
     "재기동 후 이력 0건(휘발성) — 이력을 파일/DB에 복원하는 결함 검출",
     "평가 5회 후 프로세스 재기동, 조회",
     procedure="1. childlock 기동, 평가 5회(50 ms 간격, 기본값 스냅샷)\n2. 이력 5건 확인\n3. 프로세스 종료 후 재기동\n4. 평가 없이 결정 이력 조회",
     expected="재기동 직후 이력 0건",
     pass_criteria="조회 결과 건수 == 0",
     techniques=[REQB, FI], priority="Medium", env="PC/SIL (프로세스 재기동 필요)", cat="non-functional")

case("n12_nofile", ["SWR-012"],
     "실행 중 작업 폴더에 새 파일이 생기지 않음 — 이력을 로그 파일/DB/임시 파일로 기록하는 결함 검출 (101건 평가 중 및 종료 후 모두 확인)",
     "빈 임시 작업 폴더에서 평가 101회 실행, 실행 전후 파일 목록(재귀) 비교",
     procedure="1. 빈 임시 폴더를 작업 디렉터리로 하고 파일 목록(재귀, 숨김 포함) 스냅샷 A 저장\n2. childlock 기동, 평가 101회 실행, 이력 조회, 정상 종료\n3. 파일 목록 스냅샷 B 저장(__pycache__ 제외 여부는 별도 기록)\n4. A와 B 비교",
     expected="새로 생성된 파일·폴더 없음(Python 바이트코드 캐시 __pycache__ 제외)",
     pass_criteria="A와 B 차집합이 비어 있음(__pycache__ 제외)",
     techniques=[REQB, ERR], priority="Low", env="PC/SIL (파일 시스템 비교 필요)", cat="non-functional")

case("n12_250", ["SWR-012"],
     "반복 롤오버 — 평가 250회 후 event_id 151~250의 100건, 오름차순 — 용량 초과가 1회만 처리되고 이후 계속 늘어나는 결함 검출",
     "평가 250회 (50 ms 간격, 기본값 스냅샷)",
     procedure="1. childlock 기동, 50 ms 간격 기본값 스냅샷으로 평가 250회\n2. 결정 이력 조회\n3. 건수, 첫·마지막 event_id 확인",
     expected="100건, event_id = 151..250, 오름차순",
     pass_criteria="건수 100, 첫 id 151, 마지막 id 250",
     techniques=[ERR, EP], priority="Low", env=ENV_EV, cat="non-functional", proposed=True)

case("n16_replay", ["SWR-016"],
     "결정론: 모든 규칙을 거치는 입력 벡터를 고정 시계로 1,000회 재생해 공개 결과 해시(SHA-256)가 모두 같음 — 난수, 실제 시계, dict/set 순서, 모듈 전역 상태 누수(재생 간 상태 잔존) 결함 검출",
     "입력 벡터 V: 이 사양서의 TC-F 벡터 중 규칙별 대표 케이스(충돌 CONFIRMED·PENDING, 센서 고장, freshness 상실, 접근위험·override, 시동 꺼짐, 화재/과온/성인, ISOFIX, 자동 잠금, 운전자 명령 4종 source, 무효 입력·무효 명령)를 이어 붙인 시퀀스. 재생 1,000회",
     procedure="1. 벡터 V를 구성: s3_bound, s4_all, s5_left, s6_100, s7_basic, s8_rules, s13_missing, s13_cmd, s13_200, s17_multi, s18_right, s20_off, s21_rules, s24_init 케이스의 steps를 순서대로 이어 붙인 시퀀스(케이스 사이에 새 childlock 인스턴스)\n2. 1,000회 반복: 새 childlock 인스턴스를 만들고 고정 시계 0 ms에서 벡터 V를 재생하며 매 평가의 Status(7필드)와 최종 이벤트 목록을 수집\n3. 매 회 수집 결과를 키 정렬 JSON으로 직렬화해 SHA-256 계산\n4. 1,000개 해시의 고유 값 개수 확인",
     expected="1,000개 해시가 모두 같다(고유 해시 1개)",
     pass_criteria="고유 해시 수 == 1",
     techniques=[REQB, ERR], priority="Medium", env="PC/SIL (스크립트 반복 실행, 1,000회 재생)", cat="non-functional")

case("n16_hashseed", ["SWR-016"],
     "서로 다른 프로세스 환경(PYTHONHASHSEED=0/1/random, TZ=UTC/Asia/Seoul)에서 같은 벡터를 재생해도 해시 동일 — 집합 순회 순서·시간대에 따라 달라지는 값 사용 결함 검출",
     "n16_replay와 같은 벡터 V, 환경 6종(PYTHONHASHSEED 0/1/random × TZ UTC/Asia/Seoul)에서 각 1회씩 별도 프로세스 재생",
     procedure="1. n16_replay의 벡터 V를 재생하는 스크립트를 준비\n2. 환경 변수 PYTHONHASHSEED(0, 1, random)와 TZ(UTC, Asia/Seoul) 조합 6가지로 각각 별도 프로세스 실행\n3. 각 프로세스가 출력한 SHA-256 비교",
     expected="6개 해시가 모두 n16_replay의 해시와 같다",
     pass_criteria="고유 해시 수 == 1",
     techniques=[ERR, EP], priority="Low", env="PC/SIL (별도 프로세스 6회 실행, 환경 변수 설정)", cat="non-functional", proposed=True)

case("f14_status", ["SWR-014"],
     "상태 조회 응답에 7개 필드(lock_left, lock_right, state, input_validity, priority_reason, reason_code, warning_code)가 모두 있고 값이 직전 평가 결과와 같다 — 필드 누락(특히 warning_code가 없을 때 키 자체 생략), 이전 평가 값 반환 결함 검출. 기동 직후(평가 전)도 확인",
     "(a) 기동 직후 GET /api/status (b) 정상 스냅샷 평가 후 (c) sensor_fault=true 평가 후 (d) 이어서 crash_status=CONFIRMED 평가 후 각각 GET /api/status",
     procedure="1. 시뮬레이터 기동 직후 GET /api/status 호출, 응답 키와 값 확인\n2. POST /api/snapshot(기본값), POST /api/step(advance_ms=50) 후 GET /api/status 확인\n3. POST /api/snapshot(sensor_fault=true), POST /api/step(50) 후 GET /api/status 확인\n4. POST /api/snapshot(crash_status=CONFIRMED, sensor_fault=true), POST /api/step(50) 후 GET /api/status 확인",
     expected="(a) lock_left=RELEASE, lock_right=RELEASE, state=OFF, input_validity=NO_DATA, 7개 키 모두 존재(warning_code=null)\n(b) RELEASE/RELEASE, NORMAL, VALID, warning_code=null\n(c) state=FAULT, warning_code=W_SENSOR_FAULT, reason_code=sensor_fault\n(d) 응답이 (c)가 아닌 최신 평가 결과(crash_confirmed, 두 출력 RELEASE)를 반영\n모든 응답의 키 집합이 정확히 7개",
     pass_criteria="모든 응답에서 7개 키가 존재하고 값이 해당 평가 결과와 일치",
     techniques=[REQB, EP], priority="Medium", env=ENV_WEB, cat="functional")

case("f14_idem", ["SWR-014"],
     "상태 조회를 연속 2회 호출해도 응답이 같고 결정 이벤트 수가 늘지 않음 — 조회가 평가를 일으키거나 상태를 바꾸는 부작용 결함 검출 (요구가 직접 규정하지 않은 확인)",
     "평가 1회 후 GET /api/status 3회 연속, 전후 GET /api/events 건수 비교",
     procedure="1. 기본값 스냅샷 제출, POST /api/step(50)\n2. GET /api/events 건수 N 기록\n3. GET /api/status를 3회 연속 호출하여 응답 비교\n4. GET /api/events 건수 재확인",
     expected="3회 응답이 같고, 이벤트 건수는 N 그대로",
     pass_criteria="응답 3건 동일 AND 이벤트 건수 불변",
     techniques=[ERR], priority="Low", env=ENV_WEB, cat="functional", proposed=True)

case("f15_display", ["SWR-015"],
     "입력 주입 후 화면(GET /)에 좌·우 출력, state, 입력 유효성, 이유 코드가 표시되고 priority_reason이 reason_code로도 표시됨 — 일부 항목 미표시, 이전 값 잔존, 이유 코드 매핑 누락 결함 검출 (수동 판정)",
     "브라우저로 GET / 접속 후 세 시나리오: (a) 정지·정상 (b) 50.0 km/h 자동 잠금 (c) sensor_fault=true",
     procedure="1. 시뮬레이터를 기동하고 브라우저에서 GET /를 연다(수동)\n2. (a) 기본값 스냅샷 주입 후 step 50 ms, 화면 확인\n3. (b) vehicle_speed_kph=50.0 스냅샷 주입 후 step 50 ms, 화면 확인\n4. (c) sensor_fault=true 스냅샷 주입 후 step 50 ms, 화면 확인\n5. 각 시나리오에서 화면의 좌·우 출력, state, 입력 유효성, 최근 결정 이유(reason_code)를 GET /api/status 값과 대조",
     expected="(a) RELEASE/RELEASE, NORMAL, VALID가 표시. (b) LOCK/LOCK, 이유 auto_lock_speed 표시. (c) FAULT, 이유 sensor_fault 표시. 모든 화면 값이 /api/status와 일치하고 priority_reason이 reason_code로도 표시",
     pass_criteria="세 시나리오 모두 4개 표시 항목이 /api/status와 일치(시험자 육안 판정, 화면 캡처 첨부)",
     techniques=[REQB, EP], priority="Low", env="Web 브라우저 화면 확인(수동) + HTTP API", cat="functional",
     remarks="화면 표시 확인은 수동 시험")

case("f15_500", ["SWR-015"],
     "상태를 직렬화하지 못하면 GET /api/status가 HTTP 500 — 예외를 삼키고 200과 빈/부분 응답을 돌려주는 결함 검출",
     "상태 직렬화기가 예외를 일으키도록 시험 하네스에서 대체(주입) 후 GET /api/status",
     procedure="1. 시험 하네스(FastAPI TestClient)로 시뮬레이터를 기동하고 기본값 스냅샷·step 50 ms 실행, 정상 시 GET /api/status가 HTTP 200임을 확인\n2. 상태 직렬화 함수가 예외를 발생시키도록 하네스에서 대체(monkeypatch)\n3. GET /api/status 호출, HTTP 상태 코드 확인\n4. 대체를 되돌린 후 GET /api/status가 다시 200인지 확인",
     expected="2단계 후 응답 HTTP 상태 코드 == 500. 되돌린 뒤에는 200",
     pass_criteria="직렬화 실패 시 상태 코드 500",
     techniques=[FI, REQB], priority="Medium", env="Web (FastAPI TestClient + 직렬화 실패 주입용 시험 하네스)", cat="functional",
     remarks="실패 주입 수단은 시뮬레이터 공개 API에 없어 하네스 대체가 필요함(Q-02)")

# =====================================================================
# 키 -> ID 부여
# =====================================================================
fi = ni = 0
for c in CASES:
    if c["category"] == "functional":
        fi += 1
        c["id"] = f"TC-F-{fi:03d}"
    else:
        ni += 1
        c["id"] = f"TC-NF-{ni:03d}"
    if c["proposed"]:
        pass


def ids(*keys):
    return [KEYMAP[k]["id"] for k in keys]


# =====================================================================
# 요구사항
# =====================================================================
REQS = [
    ("SWR-001", "운전자 잠금 명령 처리", "functional", "QM", "유효 DriverCommand(action=lock)를 SWR-004 조건 만족 시 side가 지정한 출력만 다음 평가주기에 LOCK으로 하고 지정하지 않은 출력은 바꾸지 않는다.", True, False),
    ("SWR-002", "운전자 해제 명령 처리", "functional", "QM", "유효 DriverCommand(action=unlock)를 SWR-004 조건 만족 시 side가 지정한 출력만 다음 평가주기에 RELEASE로 하고 지정하지 않은 출력은 바꾸지 않는다.", True, False),
    ("SWR-003", "주행 자동 잠금", "functional", "QM", "유효 입력의 vehicle_speed_kph가 3.0 이상인 평가주기마다 상위 규칙(1~6순위)이 적용되지 않는 출력을 LOCK으로 하고, 3.0 미만으로 내려가도 자동 해제하지 않는다.", True, True),
    ("SWR-004", "운전자 명령 적용 조건", "functional", "QM", "운전자 명령은 8순위. 지정 출력에 1~7순위 규칙이 적용 중이면 명령을 적용하지 않고 reason_code는 1~2순위면 그 코드, 3순위면 approach_risk_<side>, 4~7순위면 driver_rejected(CR-01). side=all은 좌·우 각각 판정.", True, False),
    ("SWR-005", "접근위험 도어 잠금과 해제 억제", "functional", "B", "rear_*_approach_risk=true인 평가주기마다 해당 도어 출력을 LOCK으로 하고 그 도어의 운전자 해제와 4~8순위 해제를 적용하지 않으며 reason_code=approach_risk_<side>를 기록한다.", True, False),
    ("SWR-006", "접근위험 억제 후 재입력 override", "functional", "QM", "SWR-005의 첫 해제 억제 시각부터 10.0 s 이하에 같은 도어 해제 재입력이 오면 state=OVERRIDE, reason_code=approach_override_<side>를 생성하고 접근위험 true인 동안 LOCK 유지. 10.0 s 초과는 새 첫 억제. 접근위험 false가 되면 OVERRIDE 종료.", True, True),
    ("SWR-007", "충돌 확정 긴급 해제", "functional", "B", "crash_status=CONFIRMED가 되면 모든 규칙에 우선하여 300 ms 이내 두 출력 RELEASE, state=CRASH_RELEASE, reason_code=crash_confirmed. 이후 crash_status가 바뀌어도 ignition_on=false가 될 때까지 RELEASE 유지.", True, True),
    ("SWR-008", "충돌 판정 대기(PENDING) 처리", "functional", "B", "crash_status=PENDING이면 긴급 해제하지 않고 다른 규칙으로 판정하며, 1~3순위 규칙이 적용되지 않으면 reason_code=crash_pending, 적용되면 그 규칙의 코드를 기록한다.", True, False),
    ("SWR-009", "좌·우 독립 판정", "functional", "B", "좌·우 출력을 도어별 입력(접근위험, ISOFIX)과 side 지정에 따라 독립 판정하며 한쪽 도어 전용 입력은 반대쪽 출력을 바꾸지 않는다.", True, False),
    ("SWR-010", "결정 이벤트 ID 부여", "non-functional", "QM", "평가주기마다 결정 이벤트 1건을 만들고 기동 후 1부터 1씩 증가하는 event_id를 부여한다.", True, False),
    ("SWR-011", "결정 이벤트 허용 필드", "non-functional", "QM", "결정 이벤트에는 SWIF 6장 허용 필드 8개만 저장하고 영상·음성·개인 식별자·DriverCommand source는 저장하지 않는다.", True, False),
    ("SWR-012", "결정 이력 용량과 휘발성", "non-functional", "QM", "결정 이벤트를 메모리에만 보존하고 최신 100건을 넘으면 가장 오래된 것부터 버리며 event_id 오름차순으로 조회되고 영구 저장소에 기록하지 않는다.", True, True),
    ("SWR-013", "입력 유효성·freshness 감시", "functional", "B", "VehicleSnapshot/DriverCommand를 SWIF 규칙으로 검증: 무효 스냅샷은 판정에 쓰지 않고 출력 유지·INVALID·input_invalid, 무효 명령은 적용 안 함·command_invalid, 200 ms 초과 미갱신 시 100 ms 이내 DEGRADED/STALE·출력 유지, DEGRADED 중 명령 미적용, 새 유효 스냅샷으로 DEGRADED 종료.", True, True),
    ("SWR-014", "상태 조회", "functional", "QM", "상태 조회 요청에 SWIF 4장의 7개 필드를 담아 최신 평가 결과로 응답한다.", True, False),
    ("SWR-015", "상태 표시와 직렬화 오류 응답", "functional", "QM", "Web 시뮬레이터는 상태를 화면에 표시하고 priority_reason을 reason_code로도 표시하며, 상태를 직렬화하지 못하면 HTTP 500으로 응답한다.", True, False),
    ("SWR-016", "결정론적 재생", "non-functional", "QM", "같은 초기 상태와 같은 입력 순서(값·시각)를 고정 시계로 재생하면 항상 같은 공개 결과를 만들고, 판정에 실제 시계·난수·환경 의존 값을 쓰지 않는다.", True, False),
    ("SWR-017", "화재·과온·성인 탑승 강제 해제", "functional", "QM", "fire/overtemperature/adult_present 중 하나라도 true이면 다음 평가주기에 두 출력 RELEASE, 입력별 이유 코드 기록(복수면 fire > overtemperature > adult_present), true인 동안 6~8순위 잠금 미적용, 1~4순위가 적용되는 출력은 그 규칙을 따른다.", True, False),
    ("SWR-018", "ISOFIX 강제 잠금", "functional", "QM", "isofix_left/right=true인 평가주기마다 해당 도어 출력을 LOCK으로 하고 reason_code=isofix_<side>를 기록하며 반대쪽 출력은 바꾸지 않는다. 1~5순위가 적용되는 출력은 그 규칙을 따른다.", True, False),
    ("SWR-020", "시동 꺼짐 해제", "functional", "QM", "ignition_on=false인 첫 평가주기에 두 출력 RELEASE, state=OFF, reason_code=ignition_off. false인 동안 5~8순위 미적용. 1~3순위가 적용되는 출력은 그 규칙을 따른다.", True, False),
    ("SWR-021", "센서 고장 출력 유지", "functional", "B", "sensor_fault=true인 첫 평가주기부터 새 명령과 3~8순위를 적용하지 않고 확정 출력을 유지하며 state=FAULT, warning_code=W_SENSOR_FAULT, reason_code=sensor_fault. 충돌 확정은 적용. false가 된 평가주기부터 정상 판정.", True, False),
    ("SWR-022", "판정 우선순위", "functional", "B", "평가주기마다 좌·우 출력을 ①충돌 확정 ②센서 고장/freshness 상실 ③접근위험 ④시동 꺼짐 ⑤화재·과온·성인 ⑥ISOFIX ⑦자동 잠금 ⑧운전자 명령 순으로 각각 판정, 최고 순위 규칙만 적용하고 priority_reason 제공, 규칙 없으면 hold. 좌우 규칙이 다르면 높은 순위(동순위는 좌측) 것을 평가의 priority_reason/reason_code로 한다.", True, False),
    ("SWR-023", "평가 주기", "non-functional", "B", "50 ms 고정 주기로 평가하며 각 평가는 최신 유효 VehicleSnapshot과 직전 평가 이후 받은 DriverCommand(받은 순서대로)를 사용한다.", True, True),
    ("SWR-024", "기동 시 초기 상태", "functional", "QM", "기동 직후 두 출력 RELEASE, state=OFF, input_validity=NO_DATA. 첫 유효 VehicleSnapshot 전에는 운전자 명령을 적용하지 않는다.", True, False),
]
requirements = [
    {"id": i, "title": t, "text": x, "category": c, "asil": a, "testable": True, "has_inputs": hi, "has_ranges": hr}
    for (i, t, c, a, x, hi, hr) in REQS
]

# =====================================================================
# 설계 항목
# =====================================================================
DESIGN = []


def D(did, req, tech, item, values, covered, applicable=True, note=""):
    DESIGN.append({"id": did, "basis_id": req, "technique": tech, "item": item, "values": values,
                   "covered_by": ids(*covered) if covered else [], "applicable": applicable, "note": note})


def NA(req, note, tech=PW):
    D(f"PW-{req}-NA", req, tech, "적용 검토", "", [], False, note)


# SWR-001
D("EP-SWR-001-V1", "SWR-001", EP, "side=left 유효 클래스", "left × source 4종", ["s1_left"])
D("EP-SWR-001-V2", "SWR-001", EP, "side=right 유효 클래스", "right × source 4종", ["s1_right"])
D("EP-SWR-001-V3", "SWR-001", EP, "side=all 유효 클래스", "all × source 4종", ["s1_all"])
D("EP-SWR-001-V4", "SWR-001", EP, "비지정 출력이 LOCK/RELEASE인 두 상태", "left lock 후 right lock", ["s1_keep"])
D("EP-SWR-001-I1", "SWR-001", EP, "무효 클래스(미등록 source/side/action)", "SWR-013 케이스(s13_cmd)에서 검증", [], False,
  "SWR-001은 유효 DriverCommand만 다룬다. 무효 명령의 동작은 SWR-013(command_invalid) 요구이므로 그 케이스에서 검증한다.")
NA("SWR-001", "side × source는 파라미터 2개로 전체 12조합을 모두 실행하므로 페어와이즈가 필요 없다(전수 시험).")
# SWR-002
D("EP-SWR-002-V1", "SWR-002", EP, "side=left 유효 클래스", "left × source 4종", ["s2_left"])
D("EP-SWR-002-V2", "SWR-002", EP, "side=right 유효 클래스", "right × source 4종", ["s2_right"])
D("EP-SWR-002-V3", "SWR-002", EP, "side=all 유효 클래스", "all × source 4종", ["s2_all"])
D("EP-SWR-002-V4", "SWR-002", EP, "비지정 출력이 LOCK인 상태", "left unlock 후 right unlock", ["s2_keep"])
NA("SWR-002", "side × source는 파라미터 2개로 전체 12조합을 모두 실행하므로 페어와이즈가 필요 없다(전수 시험).")
# SWR-003
D("EP-SWR-003-V1", "SWR-003", EP, "속도 < 3.0 (자동 잠금 안 함)", "0.0, 2.9", ["s3_bound", "s3_nounlock"])
D("EP-SWR-003-V2", "SWR-003", EP, "속도 ≥ 3.0 (자동 잠금)", "3.0, 3.1, 50.0, 300.0", ["s3_bound", "s3_31", "s4_speed", "s13_valid"])
D("EP-SWR-003-V3", "SWR-003", EP, "3.0 이상에서 미만으로 하강(해제하지 않음)", "3.0→2.9→0.0", ["s3_nounlock"])
D("BV-SWR-003-01", "SWR-003", BV, "자동 잠금 임계값", "2.9(직하), 3.0(경계), 3.1(직상) — 3값 경계(비교 연산자 위험)", ["s3_bound", "s3_31"])
NA("SWR-003", "상호작용하는 이산 파라미터가 속도 1개뿐이다.")
# SWR-004
D("EP-SWR-004-V1", "SWR-004", EP, "막는 규칙 없음(명령 적용)", "side=all 판정에서 막는 규칙이 없는 출력(우측 잠금 적용)", ["s4_all"])
D("EP-SWR-004-I1", "SWR-004", EP, "1순위가 막음 → crash_confirmed", "CONFIRMED + 잠금 명령", ["s4_crash"])
D("EP-SWR-004-I2", "SWR-004", EP, "2순위가 막음 → sensor_fault / input_stale", "sensor_fault, 스냅샷 중단", ["s4_sensor", "s13_degraded"])
D("EP-SWR-004-I3", "SWR-004", EP, "3순위가 막음 → approach_risk_<side>", "좌측 접근위험 + 해제", ["s5_left"])
D("EP-SWR-004-I4", "SWR-004", EP, "4순위(시동 꺼짐)가 막음 → driver_rejected", "ignition false + 잠금", ["s4_ign"])
D("EP-SWR-004-I5", "SWR-004", EP, "5순위(화재)가 막음 → driver_rejected", "fire + 잠금", ["s4_fire"])
D("EP-SWR-004-I6", "SWR-004", EP, "6순위(ISOFIX)가 막음 → driver_rejected", "isofix_left + 좌측 해제", ["s4_isofix"])
D("EP-SWR-004-I7", "SWR-004", EP, "7순위(자동 잠금)가 막음 → driver_rejected", "50.0 km/h + 해제", ["s4_speed"])
D("EP-SWR-004-I8", "SWR-004", EP, "side=all에서 출력별 판정이 갈림", "좌 ISOFIX + 전체 해제", ["s4_all"])
NA("SWR-004", "막는 규칙을 독립 변수로 보면 8개지만 한 출력에 순위 1개만 적용되는 구조라 규칙별 단독 EP로 모두 덮는다. 복수 규칙 상호작용은 SWR-022 페어와이즈가 담당한다.")
# SWR-005
D("EP-SWR-005-V1", "SWR-005", EP, "좌측 접근위험 true(우측 false)", "RELEASE 상태에서 true, 해제 명령, 위험 해소", ["s5_left", "s5_ign"])
D("EP-SWR-005-V2", "SWR-005", EP, "우측 접근위험 true(좌측 false)", "우측 true, 우측/all 해제", ["s5_right"])
D("EP-SWR-005-V3", "SWR-005", EP, "접근위험 true + 시동 꺼짐", "좌측 true + ignition false", ["s5_ign"])
NA("SWR-005", "독립 파라미터는 좌/우 접근위험 2개와 명령이며 순위 상호작용은 SWR-022 페어와이즈에서 다룬다.")
# SWR-006
D("EP-SWR-006-V1", "SWR-006", EP, "같은 도어 재입력(10.0 s 이하)", "간격 10.0 s", ["s6_100"])
D("EP-SWR-006-V2", "SWR-006", EP, "같은 도어 재입력(10.0 s 초과)", "간격 10.1 s", ["s6_101"])
D("EP-SWR-006-I1", "SWR-006", EP, "다른 도어 재입력", "우측 억제 후 좌측 재입력", ["s6_door"])
D("EP-SWR-006-V3", "SWR-006", EP, "OVERRIDE 종료(접근위험 false)", "true 유지 → false", ["s6_100"])
D("BV-SWR-006-01", "SWR-006", BV, "재입력 간격 10.0 s", "10.0(경계 포함), 10.1(바깥) — 분해능 0.1 s", ["s6_100", "s6_101"])
NA("SWR-006", "독립 파라미터는 간격과 도어 2개로 경계값·EP로 모두 덮는다.")
# SWR-007
D("EP-SWR-007-V1", "SWR-007", EP, "CONFIRMED(LOCK/접근위험/고속 상태)", "LOCK/LOCK, 50.0 km/h, 좌 접근위험", ["s7_basic"])
D("EP-SWR-007-V2", "SWR-007", EP, "CONFIRMED 이후 NONE/PENDING(래치)", "NONE, PENDING + 명령·속도·접근위험·ISOFIX", ["s7_latch"])
D("EP-SWR-007-V3", "SWR-007", EP, "래치 종료(ignition false 후 복귀)", "ignition false→true", ["s7_ign"])
D("EP-SWR-007-V4", "SWR-007", EP, "CONFIRMED + 센서 고장 동시", "sensor_fault true", ["s7_sensor", "s21_crash"])
D("EP-SWR-007-V5", "SWR-007", EP, "첫 유효 입력이 CONFIRMED(출력 RELEASE)", "기동 직후 CONFIRMED", ["s7_first"])
D("BV-SWR-007-01", "SWR-007", BV, "해제 시간 300 ms", "입력 후 300 ms 시점에 RELEASE(50 ms 주기, +300 ms 평가)", ["s7_basic", "s7_sensor", "s7_first"])
D("WOW-SWR-007-01", "SWR-007", WOW, "WoW: 다른 모든 규칙 최대 + CONFIRMED", "300.0 km/h, 좌·우 접근위험·ISOFIX, 센서 고장, 잠금 명령", ["s7_wow"])
NA("SWR-007", "충돌 입력은 단일 3값 열거이고 다른 규칙과의 조합은 SWR-022 페어와이즈와 WoW 케이스가 담당한다.")
# SWR-008
D("EP-SWR-008-V1", "SWR-008", EP, "PENDING 단독(규칙 없음)", "LOCK/LOCK에서 PENDING 7회", ["s8_hold"])
D("EP-SWR-008-V2", "SWR-008", EP, "PENDING + 1~3순위 규칙", "좌측 접근위험, 센서 고장", ["s8_rules"])
D("EP-SWR-008-V3", "SWR-008", EP, "PENDING + 4~8순위 규칙만", "50.0 km/h, ignition false, 잠금 명령", ["s8_rules"])
D("EP-SWR-008-V4", "SWR-008", EP, "PENDING → CONFIRMED", "전이", ["s8_confirm"])
D("EP-SWR-008-V5", "SWR-008", EP, "PENDING → NONE", "전이", ["s8_none"])
NA("SWR-008", "PENDING과 결합하는 규칙은 SWR-022 페어와이즈(CRASH 파라미터에 PENDING 포함)와 s8_rules 결정 테이블로 덮는다.")
# SWR-009
D("EP-SWR-009-V1", "SWR-009", EP, "좌 입력만 true + all 명령", "좌 접근위험 + all unlock", ["s9_mixed"])
D("EP-SWR-009-V2", "SWR-009", EP, "우 전용 입력만 true", "우 접근위험, 우 ISOFIX", ["s9_right"])
D("EP-SWR-009-V3", "SWR-009", EP, "좌·우 서로 다른 규칙", "좌 접근위험 + 우 ISOFIX", ["s9_diff"])
D("EP-SWR-009-V4", "SWR-009", EP, "좌·우 같은 순위(타이브레이크)", "접근위험 양쪽, ISOFIX 양쪽", ["s9_tie", "s22_right"])
NA("SWR-009", "도어 파라미터는 접근위험·ISOFIX·명령 side로 구성되며 조합은 s9 케이스와 SWR-022 페어와이즈로 덮는다.")
# SWR-010
D("EP-SWR-010-V1", "SWR-010", EP, "평가 종류별 이벤트 생성(NO_DATA, 유효, 무효, 명령, 무입력)", "5회 평가", ["n10_ids"])
D("EP-SWR-010-V2", "SWR-010", EP, "재기동", "재기동 후 id 1", ["n10_restart"])
D("EP-SWR-010-V3", "SWR-010", EP, "한 주기 다수 명령", "명령 3건 → 이벤트 1건", ["n10_multi"])
NA("SWR-010", "독립 파라미터 없음(평가 횟수 하나).")
# SWR-011
D("EP-SWR-011-V1", "SWR-011", EP, "허용 입력 전 종류(명령 4종 source, 무효, STALE, FAULT, CRASH)", "6종 입력", ["n11_fields"])
D("EP-SWR-011-I1", "SWR-011", EP, "허용되지 않은 추가 필드 입력", "user_name/phone/device_id/account", ["n11_extra"])
NA("SWR-011", "이산 파라미터 사이 상호작용이 없고 이벤트 필드 집합 일치만 판정한다.")
# SWR-012
D("EP-SWR-012-V1", "SWR-012", EP, "100건 미만/이하(99, 100)", "99, 100회", ["n12_100"])
D("EP-SWR-012-V2", "SWR-012", EP, "100건 초과(101, 250)", "101, 250회", ["n12_101", "n12_250"])
D("EP-SWR-012-V3", "SWR-012", EP, "재기동 후 / 파일 미생성", "재기동, 파일 목록 비교", ["n12_restart", "n12_nofile"])
D("BV-SWR-012-01", "SWR-012", BV, "이력 용량 100건", "99, 100(경계), 101(경계 바깥)", ["n12_100", "n12_101"])
NA("SWR-012", "독립 파라미터가 평가 횟수 1개뿐이다.")
# SWR-013
D("EP-SWR-013-V1", "SWR-013", EP, "유효 스냅샷(경계 포함)", "0.0, 300.0, ts 0.0", ["s13_valid"])
D("EP-SWR-013-I1", "SWR-013", EP, "무효: 속도 범위 밖", "300.1, -0.1, 1000.0", ["s13_range"])
D("EP-SWR-013-I2", "SWR-013", EP, "무효: source_timestamp_s 음수", "-0.1", ["s13_range"])
D("EP-SWR-013-I3", "SWR-013", EP, "무효: 필드 누락(13종)", "각 필드 제거", ["s13_missing"])
D("EP-SWR-013-I4", "SWR-013", EP, "무효: 형식 오류", "문자열 속도, bool 속도, 불리언 자리 문자열/0/1/null", ["s13_type"])
D("EP-SWR-013-I5", "SWR-013", EP, "무효: 정의되지 않은 열거 값", "crash UNKNOWN/confirmed, gear X/d", ["s13_enum"])
D("EP-SWR-013-I6", "SWR-013", EP, "무효 스냅샷 내용은 판정에 쓰지 않음", "무효 묶음 안의 CONFIRMED 등", ["s13_unused"])
D("EP-SWR-013-I7", "SWR-013", EP, "무효 DriverCommand(미등록 source/side/action, 누락, 대소문자, 형식)", "8종", ["s13_cmd"])
D("EP-SWR-013-V2", "SWR-013", EP, "freshness 유지/상실/복귀", "200 ms, 201 ms, 신규 스냅샷", ["s13_200", "s13_100", "s13_degraded"])
D("EP-SWR-013-V3", "SWR-013", EP, "무효 스냅샷은 freshness 미갱신", "무효만 4회", ["s13_invalid_fresh"])
D("EP-SWR-013-V4", "SWR-013", EP, "source_timestamp_s 기준 freshness", "나이 0.200/0.201/0.500", ["s13_ts"])
D("BV-SWR-013-01", "SWR-013", BV, "속도 범위", "-0.1, 0.0, 300.0, 300.1 (분해능 0.1)", ["s13_range", "s13_valid"])
D("BV-SWR-013-02", "SWR-013", BV, "source_timestamp_s 하한", "-0.1, 0.0", ["s13_range", "s13_valid"])
D("BV-SWR-013-03", "SWR-013", BV, "freshness 한계 200 ms", "나이 200 ms(유효), 201 ms(상실)", ["s13_200", "s13_ts"])
D("BV-SWR-013-04", "SWR-013", BV, "상실 감지 시간 100 ms(나이 300 ms까지)", "나이 200/300 ms", ["s13_100"])
NA("SWR-013", "무효 입력은 무효 클래스를 케이스당 하나씩 두는 규칙에 따라 단일 변이로 시험한다. 두 개 이상 동시 변이는 무효 원인 분리가 안 되어 페어와이즈 대상에서 제외했다.")
# SWR-014
D("EP-SWR-014-V1", "SWR-014", EP, "조회 시점: 기동 직후 / 평가 후 / FAULT / CRASH", "4 시점", ["f14_status"])
D("EP-SWR-014-V2", "SWR-014", EP, "연속 조회 부작용 없음", "3회 연속", ["f14_idem"])
NA("SWR-014", "입력 파라미터가 시점 하나뿐이다.")
# SWR-015
D("EP-SWR-015-V1", "SWR-015", EP, "화면 표시 3 시나리오", "정상, 자동 잠금, 센서 고장", ["f15_display"])
D("EP-SWR-015-I1", "SWR-015", EP, "직렬화 실패", "하네스 주입", ["f15_500"])
NA("SWR-015", "입력 파라미터가 시나리오 하나이며 화면 확인은 수동이다.")
# SWR-016
D("EP-SWR-016-V1", "SWR-016", EP, "모든 규칙을 거치는 벡터 1,000회 재생", "벡터 V ×1000", ["n16_replay"])
D("EP-SWR-016-V2", "SWR-016", EP, "프로세스 환경 변화(PYTHONHASHSEED, TZ)", "6조합", ["n16_hashseed"])
NA("SWR-016", "환경 파라미터가 PYTHONHASHSEED·TZ 2개이고 6조합 전수 실행으로 충분하다.")
# SWR-017
D("EP-SWR-017-V1", "SWR-017", EP, "입력 3종 단독 true", "fire / overtemperature / adult", ["s17_single"])
D("EP-SWR-017-V2", "SWR-017", EP, "복수 입력 동시 true", "(over,adult), (fire,adult), (fire,over), 3종", ["s17_multi"])
D("EP-SWR-017-V3", "SWR-017", EP, "true 지속 중 하위(6~8순위) 잠금 차단", "50.0 km/h + adult", ["s17_adult_speed"])
D("EP-SWR-017-V4", "SWR-017", EP, "상·하위 규칙 동시", "화재+ISOFIX, 화재+좌 접근위험", ["s17_vs_upper"])
D("DT-SWR-017-01", "SWR-017", "결정 테이블", "fire/over/adult 3입력 8조합 중 true 포함 7조합의 이유 코드", "단독 3 + 2개 3(일부) + 3개 동시", ["s17_single", "s17_multi"])
NA("SWR-017", "독립 불리언 3개이나 전체 조합이 8개뿐이라 결정 테이블로 전수 시험(과온+성인 외 조합 포함)한다. 다른 규칙과의 조합은 SWR-022 페어와이즈.")
# SWR-018
D("EP-SWR-018-V1", "SWR-018", EP, "좌측 ISOFIX true(우측 false)", "isofix_left", ["s18_left"])
D("EP-SWR-018-V2", "SWR-018", EP, "우측 ISOFIX true(좌측 false)", "isofix_right", ["s18_right"])
D("EP-SWR-018-V3", "SWR-018", EP, "양쪽 true / 시동 꺼짐 동시", "좌우 true, 좌 true + ignition false", ["s18_right", "s18_ign"])
D("EP-SWR-018-V4", "SWR-018", EP, "ISOFIX 해제 후(자동 해제하지 않음)", "true → false", ["s18_left"])
NA("SWR-018", "독립 파라미터가 좌/우 ISOFIX 2개이며 상위 규칙 상호작용은 SWR-022 페어와이즈에서 다룬다.")
# SWR-020
D("EP-SWR-020-V1", "SWR-020", EP, "ignition_on=false 지속(고속 포함)", "50.0 km/h, 3주기", ["s20_off"])
D("EP-SWR-020-V2", "SWR-020", EP, "ignition_on=true 복귀", "false → true", ["s20_on", "s7_ign"])
D("EP-SWR-020-V3", "SWR-020", EP, "ignition false + 접근위험 동시", "좌 접근위험", ["s5_ign"])
NA("SWR-020", "독립 파라미터가 ignition 1개이며 상호작용은 SWR-022 페어와이즈에서 다룬다.")
# SWR-021
D("EP-SWR-021-V1", "SWR-021", EP, "sensor_fault true 첫 평가주기", "좌 LOCK/우 RELEASE", ["s21_hold"])
D("EP-SWR-021-V2", "SWR-021", EP, "FAULT 중 3~8순위 각각", "명령/속도/ISOFIX/화재/접근위험/시동 꺼짐", ["s21_rules"])
D("EP-SWR-021-V3", "SWR-021", EP, "FAULT 중 충돌 확정", "CONFIRMED", ["s21_crash"])
D("EP-SWR-021-V4", "SWR-021", EP, "sensor_fault false 복귀", "복귀 후 자동 잠금·명령", ["s21_clear"])
D("EP-SWR-021-V5", "SWR-021", EP, "첫 유효 입력부터 고장", "기동 직후 sensor_fault", ["s21_first"])
NA("SWR-021", "독립 파라미터가 sensor_fault 1개이며 다른 규칙 조합은 s21_rules와 SWR-022 페어와이즈로 덮는다.")
# SWR-022
D("EP-SWR-022-V1", "SWR-022", EP, "인접 순위 쌍 ①+②", "충돌 + 센서 고장", ["s7_sensor"])
D("EP-SWR-022-V2", "SWR-022", EP, "인접 순위 쌍 ②+③", "센서 고장 + 접근위험", ["s22_23"])
D("EP-SWR-022-V3", "SWR-022", EP, "인접 순위 쌍 ③+④", "접근위험 + 시동 꺼짐(RELEASE/LOCK 두 선행 상태)", ["s22_34", "s5_ign"])
D("EP-SWR-022-V4", "SWR-022", EP, "인접 순위 쌍 ④+⑤", "시동 꺼짐 + 화재", ["s22_45"])
D("EP-SWR-022-V5", "SWR-022", EP, "인접 순위 쌍 ⑤+⑥", "화재 + ISOFIX", ["s17_vs_upper"])
D("EP-SWR-022-V6", "SWR-022", EP, "인접 순위 쌍 ⑥+⑦", "ISOFIX + 자동 잠금", ["s22_67"])
D("EP-SWR-022-V7", "SWR-022", EP, "인접 순위 쌍 ⑦+⑧", "자동 잠금 + 해제 명령", ["s4_speed"])
D("EP-SWR-022-V8", "SWR-022", EP, "규칙 없음 → hold/no_change", "속도 2.9, 센서 정상 등", ["s3_nounlock"])
D("EP-SWR-022-V9", "SWR-022", EP, "좌 ISOFIX + 우 해제 명령 / 우 ISOFIX + 좌 잠금", "reason_code 좌우 선택", ["s22_mixed", "s22_right"])
for i, k in enumerate(PW_KEYS, 1):
    D(f"PW-SWR-022-{i:02d}", "SWR-022", PW, f"PICT 행 {i:02d}", PICT_ROWS[i - 1] and " / ".join(f"{a}={b}" for a, b in PICT_ROWS[i - 1].items()), [k])
D("WOW-SWR-022-01", "SWR-022", WOW, "WoW: 충돌·센서 고장 외 모든 규칙 최대", "접근위험+시동 꺼짐+강제 해제 3종+ISOFIX 양쪽+300.0 km/h+전체 잠금 명령", ["s22_wow"])
# SWR-023
D("EP-SWR-023-V1", "SWR-023", EP, "한 주기 명령 순서(2건·3건)", "[lock,unlock], [unlock,lock], [R lock, all lock, L unlock]", ["n23_order"])
D("EP-SWR-023-V2", "SWR-023", EP, "한 주기 다수 명령(10건) + 임계 직하 속도", "WoW 케이스", ["n23_wow"])
D("BV-SWR-023-01", "SWR-023", BV, "시간 요구를 주기 단위로 만족(300 ms 이내 해제, 100 ms 이내 감지)", "+300 ms 평가에서 RELEASE, 나이 300 ms 평가에서 DEGRADED", ["s7_basic", "s13_100"])
D("WOW-SWR-023-01", "SWR-023", WOW, "WoW: 명령 10건 + 속도 2.9", "n23_wow", ["n23_wow"])
NA("SWR-023", "독립 파라미터가 명령 수·순서뿐이며 순서 조합은 전수 3건으로 충분하다.")
# SWR-024
D("EP-SWR-024-V1", "SWR-024", EP, "유효 입력 전: 스냅샷 없음", "평가 + 잠금 명령, 450 ms 경과", ["s24_init"])
D("EP-SWR-024-V2", "SWR-024", EP, "유효 입력 전: 무효 스냅샷만", "400.0 km/h", ["s24_invalid_first"])
D("EP-SWR-024-V3", "SWR-024", EP, "첫 유효 입력 후", "ignition true/false, sensor_fault, CONFIRMED, 3.1 km/h", ["s24_init", "s20_on", "s21_first"])
D("EP-SWR-024-V4", "SWR-024", EP, "유효 입력 전 받은 명령의 비보존([제안])", "NO_DATA 중 잠금 명령", ["p_nodata_retain"])
NA("SWR-024", "독립 파라미터가 첫 입력 종류 1개이며 초기 상태 조합이 적다.")
# SWR-021 etc. done. (SWR-013 retention proposal)
D("EP-SWR-013-V5", "SWR-013", EP, "DEGRADED 중 받은 명령의 비보존([제안])", "DEGRADED 중 해제 명령", ["p_degraded_retain"])

# =====================================================================
# 미결 사항
# =====================================================================
OPEN = [
    {"id": "Q-01", "basis_id": "SWR-023", "question": "검증 기준 ①(1.0 s 동안 평가 20회)을 시험 환경에서 어떻게 관측하는가? 시험자가 평가를 직접 호출하므로 '50 ms 주기를 스스로 지키는지'는 시험자가 호출하지 않는 한 확인할 수 없다. 시계 전진만으로 평가가 자동 실행되는 모드(스케줄러)가 있는가?",
     "impact": "검증 기준 ①(평가 횟수 20회)에 대한 케이스를 만들지 않음. ②(명령 순서)·③(300/100 ms 주기 단위 충족)만 시험"},
    {"id": "Q-02", "basis_id": "SWR-015", "question": "직렬화 실패(검증 기준 ②)를 어떻게 주입하는가? 시뮬레이터 공개 API(5종)에는 실패 주입 수단이 없다. 시험 하네스에서 직렬화 함수를 monkeypatch해도 되는가, 별도 주입 엔드포인트가 있는가?",
     "impact": "TC f15_500은 하네스 monkeypatch를 가정해 작성함. 수단이 다르면 절차 수정 필요"},
    {"id": "Q-03", "basis_id": "SWR-013", "question": "SWIF가 정의하지 않은 입력의 처리 — NaN/Infinity 속도, 정수형 속도(예: 3), 분해능 0.1에 맞지 않는 값(예: 2.95), 미래 시각의 source_timestamp_s(시계보다 큼) — 는 유효인가 무효인가?",
     "impact": "해당 입력의 케이스를 만들지 않음(기대값 추측 방지)"},
    {"id": "Q-04", "basis_id": "SWR-006", "question": "접근위험이 false가 된 뒤 다시 true가 되면 10.0 s override 창(첫 억제 시각)이 유지되는가, 초기화되는가?",
     "impact": "해당 시나리오 케이스를 만들지 않음"},
    {"id": "Q-05", "basis_id": "SWR-013", "question": "무효 스냅샷이 도착한 평가에서 freshness도 상실된 경우 input_validity가 INVALID인가 STALE인가? 또한 이때 state는 무엇인가?",
     "impact": "s13_invalid_fresh는 무효 스냅샷이 없는 평가(나이 300 ms)에서만 STALE을 판정함"},
    {"id": "Q-06", "basis_id": "SWR-007", "question": "CONFIRMED와 sensor_fault=true가 동시일 때(또는 CONFIRMED와 ignition_on=false 동시일 때) state는 CRASH_RELEASE인가 FAULT/OFF인가, warning_code는 W_SENSOR_FAULT인가 null인가?",
     "impact": "해당 케이스는 출력·priority_reason·reason_code만 판정하고 state/warning_code는 판정하지 않음"},
    {"id": "Q-07", "basis_id": "SWR-004", "question": "같은 출력에서 4~7순위 규칙이 운전자 명령을 막을 때, 그 평가의 reason_code는 driver_rejected인가 막은 규칙의 이유 코드(예: isofix_left)인가? PENDING 중 같은 상황의 reason_code는 crash_pending인가 driver_rejected인가? (SWR-004는 driver_rejected, SWR-003/018 검증 기준은 규칙 코드를 기술)",
     "impact": "driver_rejected를 명시한 SWR-004 검증 기준 케이스는 판정하고, 페어와이즈 행에서는 이 경우 reason_code를 판정하지 않음"},
    {"id": "Q-08", "basis_id": "SWR-011", "question": "VehicleSnapshot/DriverCommand에 SWIF에 없는 추가 필드가 있으면 유효인가 무효인가?",
     "impact": "n11_extra([제안])는 수락 여부를 판정하지 않고 이벤트 필드만 확인"},
    {"id": "Q-09", "basis_id": "SWR-013", "question": "DEGRADED 중이거나 첫 유효 스냅샷 전에 받은 DriverCommand는 폐기되는가, 보존되었다가 복귀 후 적용되는가? ('적용하지 않아야 한다'만 규정)",
     "impact": "p_nodata_retain, p_degraded_retain은 폐기를 가정한 [제안] 케이스"},
]

# =====================================================================
# 출력
# =====================================================================
out_cases = []
for c in CASES:
    d = {k: v for k, v in c.items() if not k.startswith("_")}
    out_cases.append(d)

data = {
    "title": "전자식 차일드락 제어 SW 시스템 테스트 명세 (SWE.6)",
    "basis_document": "SWR-SPEC-001 v1.1 (BL-SWR-1.1)",
    "requirements": requirements,
    "test_cases": out_cases,
    "design": DESIGN,
    "pict_models": [{"basis_id": "SWR-022", "model_file": "pict_model_SWR-022.txt",
                     "result_file": "pict_result_SWR-022.tsv", "order": 2, "rows": len(PICT_ROWS)}],
    "open_issues": OPEN,
}
with open(os.path.join(HERE, "stc_testcases.json"), "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print("cases", len(out_cases), "vector", sum(1 for c in out_cases if "vector" in c))

