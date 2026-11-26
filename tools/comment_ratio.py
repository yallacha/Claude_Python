"""!
@brief 파이썬 소스의 주석률을 측정한다.
"""

import argparse
import ast
import io
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

# 줄 분류에 쓰지 않는 토큰 (줄바꿈, 들여쓰기, 파일 끝)
_LAYOUT_TOKENS = {
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
    tokenize.ENCODING,
}


@dataclass(frozen=True)
class LineCounts:
    """!@brief 파일 한 개의 줄 분류 결과."""

    code: int
    comment: int
    docstring: int

    @property
    def ratio(self) -> float | None:
        """!
        @brief 주석률(%)을 계산한다.
        @return (주석 + docstring) / 전체 x 100. 센 줄이 없으면 None
        """
        total = self.code + self.comment + self.docstring
        if total == 0:
            return None
        return (self.comment + self.docstring) / total * 100


_DOC_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _docstring_rows(tree: ast.AST) -> set[int]:
    """!
    @brief 모듈·클래스·함수 docstring이 차지하는 줄 번호를 모은다.
    @param tree 파싱된 소스의 AST
    @return docstring 줄 번호 집합
    """
    rows: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DOC_OWNERS) or not node.body:
            continue
        first = node.body[0]
        # 본문 첫 문장이 문자열 상수 하나뿐이면 docstring이다
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                rows.update(range(first.lineno, first.end_lineno + 1))
    return rows


def count_lines(source: str) -> LineCounts:
    """!
    @brief 소스를 코드 줄, 주석 줄, docstring 줄로 분류해 센다.
    @param source 파이썬 소스 문자열
    @return 줄 분류 결과. 빈 줄은 어느 쪽에도 세지 않는다.
    """
    code_rows: set[int] = set()
    comment_rows: set[int] = set()
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            comment_rows.add(tok.start[0])
        elif tok.type not in _LAYOUT_TOKENS:
            # 여러 줄에 걸친 토큰(긴 문자열 등)은 걸친 줄을 모두 코드로 본다
            code_rows.update(range(tok.start[0], tok.end[0] + 1))
    doc_rows = _docstring_rows(ast.parse(source))
    code_rows -= doc_rows
    # 코드와 주석이 함께 있는 줄은 코드 줄로만 센다
    comment_rows -= code_rows | doc_rows
    return LineCounts(code=len(code_rows), comment=len(comment_rows), docstring=len(doc_rows))


def _collect_files(paths: list[str]) -> list[Path] | None:
    """!
    @brief 검사할 .py 파일 목록을 만든다. 폴더는 하위까지 찾는다.
    @param paths 파일 또는 폴더 경로 목록
    @return 정렬된 파일 목록. 없는 경로가 있으면 None
    """
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.is_file():
            files.append(path)
        else:
            print(f"오류: 경로가 없습니다: {raw}", file=sys.stderr)
            return None
    return files


def main(argv: list[str] | None = None) -> int:
    """!
    @brief 파일별 주석률을 출력하고 기준 미달 여부를 종료 코드로 알린다.
    @param argv 명령줄 인자 (None이면 sys.argv 사용)
    @return 0: 모두 통과, 1: 기준 미달 파일 있음, 2: 경로 오류
    """
    parser = argparse.ArgumentParser(description="파이썬 소스 주석률 검사")
    parser.add_argument("paths", nargs="+", help="검사할 파일 또는 폴더")
    parser.add_argument("--min", type=float, default=20.0, help="최소 주석률(%%)")
    args = parser.parse_args(argv)

    files = _collect_files(args.paths)
    if files is None:
        return 2
    failed = 0
    for path in files:
        ratio = count_lines(path.read_text(encoding="utf-8")).ratio
        if ratio is None:
            continue  # 빈 파일은 주석률을 정의할 수 없으므로 건너뛴다
        verdict = "OK" if ratio >= args.min else "FAIL"
        failed += verdict == "FAIL"
        print(f"{verdict:4} {ratio:6.1f}%  {path}")
    print(f"기준 {args.min:.1f}% 미달 파일: {failed}개")
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover - 명령줄 진입점
    sys.exit(main())
