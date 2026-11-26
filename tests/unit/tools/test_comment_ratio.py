"""!
@brief tools.comment_ratio 단위 테스트.
"""

from tools.comment_ratio import LineCounts, count_lines, main

# 주석률 25% (주석 1 / 전체 4), 20% 기준 통과
PASSING_SOURCE = "# 설명\na = 1\nb = 2\nc = 3\n"
# 주석률 정확히 20% (주석 1 / 전체 5), 경계값
BOUNDARY_SOURCE = "# 설명\na = 1\nb = 2\nc = 3\nd = 4\n"
# 주석률 0%, 20% 기준 미달
FAILING_SOURCE = "a = 1\nb = 2\n"


def test_counts_code_and_comment_lines_and_ignores_blank_lines():
    """!@brief 코드 줄, 주석 줄을 따로 세고 빈 줄은 세지 않는다."""
    source = "# 설명\n\nx = 1\n\ny = 2\n"

    assert count_lines(source) == LineCounts(code=2, comment=1, docstring=0)


def test_line_with_code_and_trailing_comment_counts_as_code_only():
    """!@brief 코드 뒤에 붙은 주석은 주석 줄로 세지 않는다(주석률 부풀리기 방지)."""
    source = "x = 1  # 설명\ny = '# 문자열 안의 샵'\n"

    assert count_lines(source) == LineCounts(code=2, comment=0, docstring=0)


def test_module_class_and_function_docstrings_count_as_docstring_lines():
    """!@brief 모듈·클래스·함수 docstring은 여러 줄이어도 docstring 줄로 센다."""
    source = (
        '"""모듈 설명."""\n'
        "class Door:\n"
        '    """문 클래스."""\n'
        "    def lock(self):\n"
        '        """!\n'
        "        @brief 잠근다.\n"
        '        """\n'
        "        return 1\n"
    )

    assert count_lines(source) == LineCounts(code=3, comment=0, docstring=5)


def test_multiline_string_that_is_not_a_docstring_counts_as_code():
    """!@brief 대입된 여러 줄 문자열은 docstring이 아니라 코드다."""
    source = 'x = 1\ntext = """\n첫째\n둘째\n"""\n'

    assert count_lines(source) == LineCounts(code=5, comment=0, docstring=0)


def test_non_string_constant_as_first_statement_is_not_a_docstring():
    """!@brief 본문 첫 문장이 `...` 같은 비문자열 상수면 docstring이 아니다."""
    source = "def stub():\n    ...\n"

    assert count_lines(source) == LineCounts(code=2, comment=0, docstring=0)


def test_ratio_is_comment_and_docstring_share_of_all_counted_lines_in_percent():
    """!@brief 주석률 = (주석 + docstring) / (코드 + 주석 + docstring) x 100."""
    assert LineCounts(code=6, comment=1, docstring=1).ratio == 25.0


def test_ratio_is_none_when_file_has_no_counted_lines():
    """!@brief 빈 파일은 주석률을 정의할 수 없으므로 None이다(0으로 나누기 방지)."""
    assert LineCounts(code=0, comment=0, docstring=0).ratio is None


def test_main_returns_0_when_every_file_meets_minimum_including_exact_boundary(tmp_path):
    """!@brief 모든 파일이 기준 이상(경계값 20.0% 포함)이면 0을 반환한다."""
    (tmp_path / "ok.py").write_text(PASSING_SOURCE, encoding="utf-8")
    (tmp_path / "edge.py").write_text(BOUNDARY_SOURCE, encoding="utf-8")

    assert main([str(tmp_path), "--min", "20"]) == 0


def test_main_returns_1_and_names_file_below_minimum(tmp_path, capsys):
    """!@brief 기준 미달 파일이 하나라도 있으면 1을 반환하고 그 파일을 출력한다."""
    (tmp_path / "ok.py").write_text(PASSING_SOURCE, encoding="utf-8")
    (tmp_path / "bad.py").write_text(FAILING_SOURCE, encoding="utf-8")

    assert main([str(tmp_path), "--min", "20"]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out and "bad.py" in out


def test_main_searches_subdirectories_recursively(tmp_path):
    """!@brief 하위 폴더의 .py 파일도 검사한다."""
    sub = tmp_path / "pkg" / "inner"
    sub.mkdir(parents=True)
    (sub / "bad.py").write_text(FAILING_SOURCE, encoding="utf-8")

    assert main([str(tmp_path), "--min", "20"]) == 1


def test_main_skips_empty_files_instead_of_failing(tmp_path):
    """!@brief 빈 파일(예: 빈 __init__.py)은 기준 미달로 보지 않는다."""
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")

    assert main([str(tmp_path), "--min", "20"]) == 0


def test_main_accepts_single_file_path(tmp_path):
    """!@brief 폴더가 아닌 파일 경로도 직접 검사한다."""
    target = tmp_path / "bad.py"
    target.write_text(FAILING_SOURCE, encoding="utf-8")

    assert main([str(target), "--min", "20"]) == 1


def test_main_returns_2_for_missing_path(tmp_path, capsys):
    """!@brief 없는 경로는 검사 통과로 오인하지 않도록 2를 반환한다."""
    assert main([str(tmp_path / "nope"), "--min", "20"]) == 2
    assert "nope" in capsys.readouterr().err
