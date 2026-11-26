"""Microsoft PICT로 페어와이즈(또는 n-wise) 조합을 도출한다.

사용법:
    python run_pict.py <model.txt> --out <result.tsv> [--order 2] [--seed seed.txt] [--pict PATH]

PICT 찾는 순서: --pict 인자 → PATH의 pict(.exe) → %LOCALAPPDATA%\\pict\\pict.exe
없으면 GitHub 공식 릴리스(microsoft/pict v3.7.4)에서 받아 SHA-256을 확인한 뒤 쓴다.
결과는 UTF-8 TSV로 저장하고, 요약(행 수, 파라미터)을 표준 출력에 JSON으로 출력한다.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

PICT_URL = "https://github.com/microsoft/pict/releases/download/v3.7.4/pict.exe"
PICT_SHA256 = "80ABA862739CF18B4FAA13D408163324D188A1C4EFCCDD977D9C5BA3F8950BBD"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def find_pict(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            sys.exit(f"오류: --pict 경로에 파일이 없습니다: {p}")
        return p
    on_path = shutil.which("pict")
    if on_path:
        return Path(on_path)
    local = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "pict" / "pict.exe"
    if local.is_file():
        return local
    if os.name != "nt":
        sys.exit("오류: PICT가 없습니다. https://github.com/microsoft/pict 를 빌드해 PATH에 두거나 --pict로 지정하세요.")
    local.parent.mkdir(parents=True, exist_ok=True)
    tmp = local.with_suffix(".download")
    print(f"PICT 다운로드: {PICT_URL}", file=sys.stderr)
    urllib.request.urlretrieve(PICT_URL, tmp)
    digest = sha256(tmp)
    if digest != PICT_SHA256:
        tmp.unlink(missing_ok=True)
        sys.exit(f"오류: 받은 pict.exe의 SHA-256이 다릅니다 ({digest}). 사용하지 않고 지웠습니다.")
    tmp.replace(local)
    return local


def decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="PICT로 조합 테스트 도출")
    ap.add_argument("model", help="PICT 모델 파일 (UTF-8)")
    ap.add_argument("--out", required=True, help="결과 TSV 경로")
    ap.add_argument("--order", type=int, default=2, help="조합 차수 (기본 2 = 페어와이즈)")
    ap.add_argument("--seed", help="반드시 포함할 조합을 담은 시드 파일")
    ap.add_argument("--pict", help="pict 실행 파일 경로")
    args = ap.parse_args()

    model = Path(args.model)
    if not model.is_file():
        sys.exit(f"오류: 모델 파일이 없습니다: {model}")
    pict = find_pict(args.pict)

    cmd = [str(pict), str(model), f"/o:{args.order}"]
    if args.seed:
        cmd.append(f"/e:{args.seed}")
    proc = subprocess.run(cmd, capture_output=True)
    out, err = decode(proc.stdout), decode(proc.stderr)
    if proc.returncode != 0:
        sys.exit(f"오류: PICT 실행 실패 (exit {proc.returncode})\n{err or out}")

    lines = [ln for ln in out.splitlines() if ln.strip()]
    if not lines:
        sys.exit("오류: PICT 결과가 비어 있습니다. 모델과 제약 조건을 확인하세요.")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")

    header = lines[0].split("\t")
    summary = {
        "pict": str(pict),
        "model": str(model),
        "result": str(Path(args.out)),
        "order": args.order,
        "parameters": header,
        "rows": len(lines) - 1,
        "warnings": err.strip() or None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
