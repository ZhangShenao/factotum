"""CJK 文案格式化薄封装。

为什么存在：autocorrect-py 只提供 SDK 不带 CLI，本脚本补上 CLI 缺口，
供 pre-commit hook 与 CI 复用；未来产品侧文案规范化也可直接复用本模块。

关键契约（实测确定，详见 docs/superpowers/specs/2026-08-27-precommit-format-hook-design.md）：
- .autocorrectrc 不会从 cwd 自动加载，必须显式 load_config
- ast 的 col_offset 是 UTF-8 字节偏移，精确列位置必须取自 tokenize
- py 文件只格式化注释与 docstring，字符串字面量原样保留
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

import autocorrect_py as ac

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / ".autocorrectrc"
IGNORE_PATH = REPO_ROOT / ".autocorrectignore"

_DOCSTRING = re.compile(r"^([A-Za-z]{0,2})(\"\"\"|''')(.*?)\2$", re.DOTALL)

_config_loaded = False


def _ensure_config() -> None:
    """显式加载 .autocorrectrc（SDK 不读 cwd，进程内只加载一次）。"""
    global _config_loaded
    if not _config_loaded:
        if CONFIG_PATH.exists():
            ac.load_config(CONFIG_PATH.read_text(encoding="utf-8"))
        _config_loaded = True


def _load_ignore_patterns() -> list[str]:
    """读取 .autocorrectignore 的裸模式（# 注释行忽略，先 strip 再判前缀）。"""
    if not IGNORE_PATH.exists():
        return []
    lines = (line.strip() for line in IGNORE_PATH.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def _is_ignored(path: Path, patterns: list[str]) -> bool:
    """简化版 gitignore 语义：相对路径全匹配、文件名匹配、目录前缀匹配。

    绝对路径先归一化为仓库相对路径，否则全路径/目录前缀豁免对绝对入参静默失效；
    仓库外路径保持原样，交由文件名匹配兜底。
    """
    try:
        rel = str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        rel = str(path)
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(path.name, pat):
            return True
        if rel.startswith(f"{pat.rstrip('/')}/"):
            return True
    return False


def _segment(lines: list[str], start: tuple[int, int], end: tuple[int, int]) -> str:
    """按 (row, col) 闭开区间切出源码片段，tokenize 坐标系（1-based 行）。"""
    sr, sc = start
    er, ec = end
    if sr == er:
        return lines[sr - 1][sc:ec]
    return lines[sr - 1][sc:] + "".join(lines[sr : er - 1]) + lines[er - 1][:ec]


def format_python(content: str) -> str:
    """仅格式化 py 文件的注释与 docstring，其余原样返回。

    为什么不动字符串字面量：autocorrect 会改写运行时文案，
    破坏「错误消息不以句号结尾」等项目约定与测试断言。
    """
    lines = content.splitlines(keepends=True)
    try:
        tree = ast.parse(content)
        toks = list(tokenize.generate_tokens(io.StringIO(content).readline))
    except SyntaxError:
        return content

    edits: list[tuple[tuple[int, int], tuple[int, int], str]] = []
    docstring_nodes: list[ast.Constant] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstring_nodes.append(body[0].value)
    for v in docstring_nodes:
        # ast 列偏移是字节偏移，含中文即错位；用行号匹配 tokenize 的 STRING token
        spans = [
            t
            for t in toks
            if t.type == tokenize.STRING and t.start[0] == v.lineno and t.end[0] == v.end_lineno
        ]
        if len(spans) != 1:
            continue
        matched = _DOCSTRING.match(_segment(lines, spans[0].start, spans[0].end))
        if matched:
            inner = ac.format_for(matched.group(3), "x.txt")
            quote = matched.group(2)
            edits.append((spans[0].start, spans[0].end, matched.group(1) + quote + inner + quote))
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            edits.append((tok.start, tok.end, ac.format_for(tok.string, "x.txt")))

    # 逆序应用编辑，避免前面的改写使后面的坐标失效
    for (sr, sc), (er, ec), replacement in sorted(
        edits, key=lambda e: (e[1][0], e[1][1]), reverse=True
    ):
        before = lines[sr - 1][:sc]
        after = lines[er - 1][ec:]
        middle = replacement.splitlines(keepends=True)
        if len(middle) == 1:
            lines[sr - 1 : er] = [before + middle[0] + after]
        else:
            lines[sr - 1 : er] = [before + middle[0], *middle[1:-1], middle[-1] + after]
    return "".join(lines)


def format_file(path: Path, *, fix: bool = True) -> bool:
    """格式化单个文件，返回是否有改动；fix=False 时只检测不写回。"""
    _ensure_config()
    content = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        corrected = format_python(content)
    else:
        corrected = ac.format_for(content, path.name)
    if corrected == content:
        return False
    if fix:
        path.write_text(corrected, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CJK 文案格式化（中英文加空格、全角标点）")
    parser.add_argument("files", nargs="*", help="待处理文件；为空时处理 git ls-files 全量")
    parser.add_argument("--lint", action="store_true", help="只检测不修复（CI 模式）")
    args = parser.parse_args(argv)

    _ensure_config()
    patterns = _load_ignore_patterns()
    if args.files:
        files = [Path(f) for f in args.files]
    else:
        try:
            listing = subprocess.run(
                ["git", "ls-files"], capture_output=True, text=True, check=True, cwd=REPO_ROOT
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or "").strip() or f"exit {exc.returncode}"
            print(f"git ls-files 执行失败: {detail}", file=sys.stderr)
            return 1
        files = [Path(line) for line in listing.stdout.splitlines() if line.strip()]

    fix = not args.lint
    changed: list[str] = []
    failed: list[str] = []
    for path in files:
        if _is_ignored(path, patterns):
            continue
        try:
            if format_file(path, fix=fix):
                changed.append(str(path))
        except (OSError, UnicodeError, ValueError) as exc:
            failed.append(f"{path}: {exc}")

    action = "格式化" if fix else "lint 未通过（--lint 模式未修复）"
    for path in changed:
        print(f"{action}: {path}")
    for message in failed:
        print(f"处理失败: {message}", file=sys.stderr)
    return 1 if changed or failed else 0


if __name__ == "__main__":
    sys.exit(main())
