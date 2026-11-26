"""테스트 케이스 JSON을 검증하고 엑셀로 만든다.

사용법:
    python build_workbook.py <testcases.json> --out <result.xlsx> [--template <양식.xlsx>]

검증(추적성, 커버리지, 필수 항목, EP/BVA 적용, 중복)에 실패하면 엑셀을 만들지 않고 exit 1.
형식은 references/data-format.md 참고.
"""
import argparse
import json
import re
import sys
from copy import copy
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

TECHNIQUES = {
    "요구사항 기반", "동치 분할", "경계값 분석", "페어와이즈(PICT)", "WoW(Worst-of-Worst)",
    "고장 주입", "오류 추정", "상태 전이", "결정 테이블",
}
CATEGORIES = {"functional": "기능 테스트", "non-functional": "비기능 테스트"}
SOURCES = {"basis", "user", "claude"}
REQUIRED_TC = ["id", "basis_ids", "purpose", "inputs", "procedure", "expected", "techniques"]
PROPOSED_TAG = "[제안]"

DEFAULT_COLUMNS = [
    ("테스트 케이스 ID", "id", 14),
    ("테스트 베이시스 ID", "basis_ids", 16),
    ("구분", "division", 8),
    ("테스트 목적", "purpose", 36),
    ("사전 조건", "preconditions", 28),
    ("입력 값", "inputs", 32),
    ("절차", "procedure", 44),
    ("예상 출력 값", "expected", 36),
    ("합격 기준", "pass_criteria", 26),
    ("사용한 테스트 기법", "techniques", 22),
    ("테스트 환경", "environment", 16),
    ("ASIL", "asil", 7),
    ("우선순위", "priority", 9),
    ("실행 결과", "result", 16),
    ("판정", "verdict", 8),
    ("비고", "remarks", 20),
]
FIELDS = {f for _, f, _ in DEFAULT_COLUMNS}

HEAD_FILL = PatternFill("solid", fgColor="1F4E78")
HEAD_FONT = Font(bold=True, color="FFFFFF")
PROPOSED_FILL = PatternFill("solid", fgColor="FFF2CC")
BAD_FILL = PatternFill("solid", fgColor="F8CBAD")
THIN = Side(style="thin", color="A6A6A6")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def validate(data: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    reqs = data.get("requirements") or []
    tcs = data.get("test_cases") or []
    design = data.get("design") or []
    issues = data.get("open_issues") or []
    if not str(data.get("basis_document") or "").strip():
        errors.append("basis_document가 비어 있습니다. 사용자가 준 테스트 베이시스 문서 이름을 적으세요. "
                      "베이시스가 없으면 케이스를 만들지 말고 사용자에게 요청하세요.")
    sample_ids = [r.get("id") for r in reqs if str(r.get("id", "")).startswith("SAMPLE-")]
    if sample_ids and not data.get("sample"):
        errors.append(f"예시 요구사항({', '.join(sample_ids[:3])} 등)이 있는데 \"sample\": true가 없습니다. "
                      "사용자가 예시를 명시적으로 요청한 경우에만 쓰세요.")
    if not reqs:
        errors.append("requirements가 비어 있습니다.")
    if not tcs:
        errors.append("test_cases가 비어 있습니다.")

    req_by_id = {}
    for r in reqs:
        rid = r.get("id")
        if not rid:
            errors.append(f"ID 없는 요구사항: {r.get('title') or r.get('text', '')[:30]}")
            continue
        if rid in req_by_id:
            errors.append(f"요구사항 ID 중복: {rid}")
        req_by_id[rid] = r
        if r.get("category") not in CATEGORIES:
            errors.append(f"{rid}: category는 functional / non-functional 중 하나여야 합니다.")
        if r.get("testable", True) is False and not any(i.get("basis_id") == rid for i in issues):
            errors.append(f"{rid}: testable=false인데 이 요구사항에 대한 open_issues 질문이 없습니다.")

    tc_by_id = {}
    seen_sig = {}
    for t in tcs:
        tid = t.get("id") or "(ID 없음)"
        for f in REQUIRED_TC:
            if not t.get(f):
                errors.append(f"{tid}: 필수 항목 '{f}'이(가) 비어 있습니다.")
        if tid in tc_by_id:
            errors.append(f"테스트 케이스 ID 중복: {tid}")
        tc_by_id[tid] = t
        if t.get("category") not in CATEGORIES:
            errors.append(f"{tid}: category는 functional / non-functional 중 하나여야 합니다.")
        src = t.get("source", "basis")
        if src not in SOURCES:
            errors.append(f"{tid}: source는 basis / user / claude 중 하나여야 합니다.")
        if src == "claude" and not t.get("proposed"):
            errors.append(f"{tid}: source=claude인 케이스는 proposed=true여야 합니다([제안] 표시).")
        if src == "user" and t.get("proposed"):
            errors.append(f"{tid}: 사용자 케이스(source=user)는 [제안]일 수 없습니다.")
        for b in as_list(t.get("basis_ids")):
            if b not in req_by_id:
                errors.append(f"{tid}: 존재하지 않는 테스트 베이시스 ID '{b}'를 참조합니다.")
        for tech in as_list(t.get("techniques")):
            if tech not in TECHNIQUES:
                errors.append(f"{tid}: 알 수 없는 기법 '{tech}'. 허용: {', '.join(sorted(TECHNIQUES))}")
        sig = (tuple(sorted(as_list(t.get("basis_ids")))), norm(t.get("preconditions")), norm(t.get("inputs")))
        if sig[2] and sig in seen_sig:
            errors.append(f"{tid}: {seen_sig[sig]}와 베이시스·사전 조건·입력 값이 같습니다(중복 케이스).")
        else:
            seen_sig[sig] = tid

    design_by_req = {}
    for d in design:
        did = d.get("id") or "(ID 없음)"
        rid = d.get("basis_id")
        if rid not in req_by_id:
            errors.append(f"설계 항목 {did}: 존재하지 않는 basis_id '{rid}'.")
            continue
        if d.get("technique") not in TECHNIQUES:
            errors.append(f"설계 항목 {did}: 알 수 없는 기법 '{d.get('technique')}'.")
        design_by_req.setdefault(rid, []).append(d)
        if d.get("applicable", True) is False:
            if not d.get("note"):
                errors.append(f"설계 항목 {did}: 적용하지 않은 이유(note)가 없습니다.")
            continue
        covered = as_list(d.get("covered_by"))
        if not covered:
            errors.append(f"설계 항목 {did}: 이 항목을 덮는 테스트 케이스(covered_by)가 없습니다.")
        for c in covered:
            t = tc_by_id.get(c)
            if t is None:
                errors.append(f"설계 항목 {did}: covered_by의 '{c}' 케이스가 없습니다.")
            elif rid not in as_list(t.get("basis_ids")):
                errors.append(f"설계 항목 {did}: {c}가 {rid}를 추적하지 않습니다.")

    for rid, r in req_by_id.items():
        if r.get("testable", True) is False:
            continue
        covering = [t for t in tcs if rid in as_list(t.get("basis_ids")) and not t.get("proposed")]
        if not covering:
            errors.append(f"{rid}: [제안]이 아닌 테스트 케이스가 없습니다(베이시스 커버리지 미달).")
        techs = {d.get("technique") for d in design_by_req.get(rid, []) if d.get("applicable", True) is not False}
        if r.get("has_inputs") and "동치 분할" not in techs:
            errors.append(f"{rid}: 입력이 있는데 동치 분할 설계 항목이 없습니다.")
        if r.get("has_ranges") and "경계값 분석" not in techs:
            errors.append(f"{rid}: 범위가 있는데 경계값 분석 설계 항목이 없습니다.")
        all_techs = {d.get("technique") for d in design_by_req.get(rid, [])}
        if r.get("has_inputs") and "페어와이즈(PICT)" not in all_techs:
            warnings.append(f"{rid}: 페어와이즈 적용 여부 검토 기록이 없습니다(applicable=false라도 이유를 남기세요).")

    for t in tcs:
        if "페어와이즈(PICT)" in as_list(t.get("techniques")):
            if not data.get("pict_models"):
                errors.append(f"{t.get('id')}: 페어와이즈 기법을 썼는데 pict_models(PICT 모델·결과 파일) 기록이 없습니다.")
                break
    if not any("WoW(Worst-of-Worst)" in as_list(t.get("techniques")) for t in tcs):
        warnings.append("WoW(Worst-of-Worst) 케이스가 하나도 없습니다. 엣지 케이스 검토 결과를 확인하세요.")
    return errors, warnings


def cell_value(t: dict, field: str, req_by_id: dict):
    if field == "basis_ids":
        return ", ".join(as_list(t.get("basis_ids")))
    if field == "techniques":
        return ", ".join(as_list(t.get("techniques")))
    if field == "division":
        return PROPOSED_TAG if t.get("proposed") else ("사용자" if t.get("source") == "user" else "일반")
    if field == "purpose":
        p = str(t.get("purpose", ""))
        return p if not t.get("proposed") or p.startswith(PROPOSED_TAG) else f"{PROPOSED_TAG} {p}"
    if field == "asil":
        levels = [str(req_by_id[b].get("asil", "")) for b in as_list(t.get("basis_ids")) if b in req_by_id]
        order = ["D", "C", "B", "A", "QM"]
        for lv in order:
            if lv in levels:
                return lv
        return ""
    if field in ("result", "verdict"):
        return t.get(field, "")
    return t.get(field, "")


def style_header(ws, row: int, ncol: int):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill, cell.font, cell.border = HEAD_FILL, HEAD_FONT, BORDER
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")


def write_table(ws, headers, rows, widths=None, start_row=1):
    for i, h in enumerate(headers, 1):
        ws.cell(row=start_row, column=i, value=h)
    style_header(ws, start_row, len(headers))
    for r_i, row in enumerate(rows, start_row + 1):
        for c_i, v in enumerate(row, 1):
            cell = ws.cell(row=r_i, column=c_i, value=v)
            cell.alignment, cell.border = WRAP, BORDER
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)


def tc_sheets_default(wb, data, req_by_id):
    for cat, name in CATEGORIES.items():
        ws = wb.create_sheet(name)
        tcs = [t for t in data["test_cases"] if t.get("category") == cat]
        rows = [[cell_value(t, f, req_by_id) for _, f, _ in DEFAULT_COLUMNS] for t in tcs]
        write_table(ws, [h for h, _, _ in DEFAULT_COLUMNS], rows, [w for _, _, w in DEFAULT_COLUMNS])
        ws.auto_filter.ref = ws.dimensions
        for r_i, t in enumerate(tcs, 2):
            if t.get("proposed"):
                for c in range(1, len(DEFAULT_COLUMNS) + 1):
                    ws.cell(row=r_i, column=c).fill = PROPOSED_FILL


def tc_sheets_template(wb, data, req_by_id, tpl: dict):
    base = wb[tpl["sheet"]] if tpl.get("sheet") else wb.worksheets[0]
    hrow = int(tpl.get("header_row", 1))
    colmap = tpl.get("columns") or {}
    bad = [f for f in colmap.values() if f not in FIELDS]
    if bad:
        sys.exit(f"오류: template.columns에 알 수 없는 필드: {bad}. 허용: {sorted(FIELDS)}")
    header_cols = {}
    for c in range(1, base.max_column + 1):
        v = base.cell(row=hrow, column=c).value
        if v is not None and str(v).strip() in colmap:
            header_cols[c] = colmap[str(v).strip()]
    missing = set(colmap) - {str(base.cell(row=hrow, column=c).value).strip() for c in header_cols}
    if missing:
        sys.exit(f"오류: 양식 {hrow}행에서 머리글을 찾지 못했습니다: {sorted(missing)}")
    sample = {c: base.cell(row=hrow + 1, column=c) for c in header_cols}
    base_index = wb.worksheets.index(base)
    for offset, (cat, name) in enumerate(CATEGORIES.items(), 1):
        ws = wb.copy_worksheet(base)
        ws.title = name
        wb.move_sheet(ws, offset=(base_index + offset) - wb.worksheets.index(ws))
        tcs = [t for t in data["test_cases"] if t.get("category") == cat]
        for r_i, t in enumerate(tcs, hrow + 1):
            for c, field in header_cols.items():
                cell = ws.cell(row=r_i, column=c, value=cell_value(t, field, req_by_id))
                src = sample[c]
                if src.has_style:
                    cell.font, cell.border, cell.number_format = copy(src.font), copy(src.border), src.number_format
                cell.alignment = WRAP
                if t.get("proposed"):
                    cell.fill = PROPOSED_FILL
    wb.remove(base)


def build(data: dict, out: Path, template: Path | None):
    req_by_id = {r["id"]: r for r in data["requirements"]}
    tcs = data["test_cases"]
    if template:
        wb = load_workbook(template)
        tc_sheets_template(wb, data, req_by_id, data.get("template") or {})
    else:
        wb = Workbook()
        wb.remove(wb.active)
        tc_sheets_default(wb, data, req_by_id)

    # 테스트 설계
    ws = wb.create_sheet("테스트 설계")
    rows = [[d.get("id"), d.get("basis_id"), d.get("technique"), d.get("item"), d.get("values"),
             "적용" if d.get("applicable", True) is not False else "미적용",
             ", ".join(as_list(d.get("covered_by"))), d.get("note", "")] for d in data.get("design") or []]
    write_table(ws, ["설계 ID", "테스트 베이시스 ID", "기법", "대상", "값/조합", "적용", "커버 케이스", "근거/비고"],
                rows, [18, 16, 20, 28, 36, 8, 24, 40])
    pict = data.get("pict_models") or []
    if pict:
        start = len(rows) + 4
        ws.cell(row=start - 1, column=1, value="PICT 모델").font = Font(bold=True)
        write_table(ws, ["테스트 베이시스 ID", "모델 파일", "결과 파일", "차수", "조합 수"],
                    [[p.get("basis_id"), p.get("model_file"), p.get("result_file"), p.get("order"), p.get("rows")] for p in pict],
                    start_row=start)
        ws.freeze_panes = "A2"

    # 추적성 매트릭스
    ws = wb.create_sheet("추적성 매트릭스")
    rows = []
    for r in data["requirements"]:
        normal = [t["id"] for t in tcs if r["id"] in as_list(t.get("basis_ids")) and not t.get("proposed")]
        prop = [t["id"] for t in tcs if r["id"] in as_list(t.get("basis_ids")) and t.get("proposed")]
        testable = r.get("testable", True) is not False
        status = "커버" if normal else ("미결(테스트 불가)" if not testable else "미커버")
        rows.append([r["id"], r.get("title", ""), "기능" if r.get("category") == "functional" else "비기능",
                     r.get("asil", ""), ", ".join(normal), ", ".join(prop), len(normal), status])
    write_table(ws, ["테스트 베이시스 ID", "요구사항", "분류", "ASIL", "테스트 케이스", "[제안] 케이스", "케이스 수", "상태"],
                rows, [16, 36, 8, 7, 36, 24, 9, 16])
    for r_i, row in enumerate(rows, 2):
        if row[-1] != "커버":
            for c in range(1, 9):
                ws.cell(row=r_i, column=c).fill = BAD_FILL
    start = len(rows) + 4
    ws.cell(row=start - 1, column=1, value="역방향: 테스트 케이스 → 베이시스").font = Font(bold=True)
    write_table(ws, ["테스트 케이스 ID", "구분", "테스트 베이시스 ID"],
                [[t["id"], cell_value(t, "division", req_by_id), ", ".join(as_list(t.get("basis_ids")))] for t in tcs],
                start_row=start)
    ws.freeze_panes = "A2"

    # 커버리지 요약
    ws = wb.create_sheet("커버리지 요약")
    reqs = data["requirements"]
    testable = [r for r in reqs if r.get("testable", True) is not False]
    covered = [r for r in testable if any(r["id"] in as_list(t.get("basis_ids")) and not t.get("proposed") for t in tcs)]
    applicable_design = [d for d in data.get("design") or [] if d.get("applicable", True) is not False]
    design_cov = [d for d in applicable_design if as_list(d.get("covered_by"))]

    def pct(a, b):
        return f"{(a / b * 100):.1f}%" if b else "-"

    def count_tech(name):
        return sum(1 for t in tcs if name in as_list(t.get("techniques")))

    summary = [
        ["요구사항 수 (전체)", len(reqs)],
        ["  기능 / 비기능", f"{sum(r.get('category') == 'functional' for r in reqs)} / {sum(r.get('category') == 'non-functional' for r in reqs)}"],
        ["  테스트 가능 / 미결", f"{len(testable)} / {len(reqs) - len(testable)}"],
        ["테스트 베이시스 커버리지 (테스트 가능 기준)", f"{pct(len(covered), len(testable))} ({len(covered)}/{len(testable)})"],
        ["테스트 베이시스 커버리지 (전체 기준)", f"{pct(len(covered), len(reqs))} ({len(covered)}/{len(reqs)})"],
        ["설계 항목 커버리지 (EP/BVA/PICT 등)", f"{pct(len(design_cov), len(applicable_design))} ({len(design_cov)}/{len(applicable_design)})"],
        ["테스트 케이스 수 (일반+사용자 / [제안])", f"{sum(not t.get('proposed') for t in tcs)} / {sum(bool(t.get('proposed')) for t in tcs)}"],
        ["  기능 / 비기능", f"{sum(t.get('category') == 'functional' for t in tcs)} / {sum(t.get('category') == 'non-functional' for t in tcs)}"],
    ] + [[f"기법별 케이스 수: {name}", count_tech(name)] for name in sorted(TECHNIQUES) if count_tech(name)]
    summary.insert(0, ["테스트 베이시스", str(data.get("basis_document"))])
    if data.get("sample"):
        summary.insert(0, ["주의", "실제 테스트 베이시스가 아닌 예시(SAMPLE) 요구사항으로 만든 산출물"])
    write_table(ws, ["항목", "값"], summary, [44, 28])
    ws.cell(row=len(summary) + 3, column=1,
            value="[제안] 케이스는 베이시스 커버리지 계산에서 제외됩니다.").font = Font(italic=True, color="7F7F7F")

    # 미결 사항
    ws = wb.create_sheet("미결 사항")
    write_table(ws, ["ID", "테스트 베이시스 ID", "질문", "영향"],
                [[i.get("id"), i.get("basis_id"), i.get("question"), i.get("impact", "")] for i in data.get("open_issues") or []],
                [8, 16, 60, 36])

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return {
        "output": str(out),
        "requirements": len(reqs),
        "testable": len(testable),
        "basis_coverage_testable": pct(len(covered), len(testable)),
        "basis_coverage_all": pct(len(covered), len(reqs)),
        "design_coverage": pct(len(design_cov), len(applicable_design)),
        "test_cases": len(tcs),
        "proposed": sum(bool(t.get("proposed")) for t in tcs),
        "open_issues": len(data.get("open_issues") or []),
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="테스트 케이스 JSON → 검증 → 엑셀")
    ap.add_argument("json", help="테스트 케이스 JSON (UTF-8)")
    ap.add_argument("--out", required=True, help="출력 .xlsx 경로")
    ap.add_argument("--template", help="사용자 양식 .xlsx (JSON에 template 매핑 필요)")
    args = ap.parse_args()

    data = json.loads(Path(args.json).read_text(encoding="utf-8-sig"))
    if args.template and not data.get("template"):
        sys.exit("오류: --template을 줬지만 JSON에 template 매핑이 없습니다. references/data-format.md 참고.")
    errors, warnings = validate(data)
    for w in warnings:
        print(f"경고: {w}", file=sys.stderr)
    if errors:
        print(f"검증 실패 {len(errors)}건 — 엑셀을 만들지 않았습니다.", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    result = build(data, Path(args.out), Path(args.template) if args.template else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
