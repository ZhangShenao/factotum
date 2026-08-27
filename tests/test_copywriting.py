"""tools/copywriting.py 表驱动测试：CJK 排版、py 文件只动注释/docstring、CLI 退出码。"""

import pytest

from tools.copywriting import format_file, format_python, main


class TestFormatPython:
    """py 文件只格式化注释与 docstring，字符串字面量原样保留。"""

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            ("# 注释:基于DeepAgents构建\n", "# 注释：基于 DeepAgents 构建\n"),
            ("x = 1  # 行尾:中文,标点.\n", "x = 1  # 行尾：中文，标点。\n"),
            ('"""模块docstring,第二行."""\n', '"""模块 docstring，第二行。"""\n'),
            ("# plain english comment\n", "# plain english comment\n"),
            ('MSG = "错误:配置加载失败."\n', 'MSG = "错误:配置加载失败."\n'),
            ('s = f"模板{x}基于DeepAgents"\n', 's = f"模板{x}基于DeepAgents"\n'),
            ("def broken(:\n", "def broken(:\n"),
        ],
    )
    def test_table(self, content: str, expected: str) -> None:
        assert format_python(content) == expected

    def test_multiline_docstring(self) -> None:
        # autocorrect 实测行为：inner 以「空行 + 末尾空白行」结尾时（闭合引号独占行的标准
        # docstring 形态），空行之后的行不做格式化；expected 以工具真实输出为准，勿改实现迁就断言
        content = 'def f():\n    """第一行:说明,\n\n    第二行:细节.\n    """\n    return 1\n'
        expected = 'def f():\n    """第一行：说明，\n\n    第二行:细节.\n    """\n    return 1\n'
        assert format_python(content) == expected

    def test_idempotent(self) -> None:
        once = format_python("# 注释:基于DeepAgents构建\n")
        assert format_python(once) == once


class TestFormatFile:
    """整文件处理：md 走全量，codeblock 受 .autocorrectrc 保护。"""

    def test_md_spacing_and_punctuation(self, tmp_path) -> None:
        f = tmp_path / "note.md"
        f.write_text("基于DeepAgents构建,这是测试.\n", encoding="utf-8")
        assert format_file(f) is True
        assert f.read_text(encoding="utf-8") == "基于 DeepAgents 构建，这是测试。\n"

    def test_md_codeblock_protected(self, tmp_path) -> None:
        f = tmp_path / "note.md"
        content = "```python\n# 块内基于DeepAgents不加空格\n```\n"
        f.write_text(content, encoding="utf-8")
        assert format_file(f) is False
        assert f.read_text(encoding="utf-8") == content

    def test_py_string_literal_preserved(self, tmp_path) -> None:
        f = tmp_path / "mod.py"
        f.write_text('MSG = "错误:配置加载失败."\n', encoding="utf-8")
        assert format_file(f) is False

    def test_no_cjk_unchanged(self, tmp_path) -> None:
        f = tmp_path / "README.md"
        f.write_text("hello world\n", encoding="utf-8")
        assert format_file(f) is False


class TestMain:
    """CLI 退出码契约：0 干净 / 1 有修改或失败。"""

    def test_fix_mode_rewrites_and_exits_1(self, tmp_path) -> None:
        f = tmp_path / "note.md"
        f.write_text("基于DeepAgents构建.\n", encoding="utf-8")
        assert main([str(f)]) == 1
        assert f.read_text(encoding="utf-8") == "基于 DeepAgents 构建。\n"

    def test_lint_mode_no_write(self, tmp_path) -> None:
        f = tmp_path / "note.md"
        original = "基于DeepAgents构建.\n"
        f.write_text(original, encoding="utf-8")
        assert main(["--lint", str(f)]) == 1
        assert f.read_text(encoding="utf-8") == original

    def test_clean_exits_0(self, tmp_path) -> None:
        f = tmp_path / "note.md"
        f.write_text("hello\n", encoding="utf-8")
        assert main([str(f)]) == 0

    def test_ignored_file_skipped(self, tmp_path) -> None:
        f = tmp_path / "uv.lock"
        original = "基于DeepAgents构建.\n"
        f.write_text(original, encoding="utf-8")
        assert main([str(f)]) == 0
        assert f.read_text(encoding="utf-8") == original

    def test_binary_file_reports_error(self, tmp_path) -> None:
        f = tmp_path / "blob.bin"
        f.write_bytes(b"\xff\xfe\x00")
        assert main([str(f)]) == 1
