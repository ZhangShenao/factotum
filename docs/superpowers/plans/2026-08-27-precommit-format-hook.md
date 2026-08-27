# Git 提交前自动格式化 Hook 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `git commit` 前自动完成 ruff 代码格式化与 CJK 文案排版修正（中英文加空格、中文句全角标点）。

**Architecture:** pre-commit 框架挂三个 local hook（`language: system`，经 `uv run` 调用），CJK 排版由自写薄封装 CLI `tools/copywriting.py` 驱动 `autocorrect-py` SDK；`.py` 文件仅格式化注释与 docstring（tokenize+ast 定位，字符串字面量不动），其余文件类型整文件处理。

**Tech Stack:** Python 3.12+/uv、autocorrect-py（dev 依赖）、pre-commit、ruff、pytest。

**规格:** `docs/superpowers/specs/2026-08-27-precommit-format-hook-design.md`

## Global Constraints

- 依赖只经 uv 管理：新增依赖进 `[dependency-groups] dev`，锁定 `uv.lock`
- ruff：行宽 100、target py312、规则 `E/F/W/I/UP/B`，提交前 `uv run ruff check . && uv run ruff format --check . && uv run pytest` 全绿
- 注释/docstring 中文、解释"为什么"；模块/函数 `snake_case`；公开函数完整类型注解
- 错误消息不以大写字母开头、不以句号结尾（中文消息自然满足：不带结尾句号）
- 实测确定的 SDK 契约（勿凭记忆改动）：
  - `autocorrect_py.format_for(content: str, filename_or_ext: str) -> str`，参数顺序是**内容在前**
  - `.autocorrectrc` **不会**从 cwd 自动加载，必须 `ac.load_config(config_str)` 显式加载（幂等：进程内首次调用后缓存）
  - CPython `ast` 的 `col_offset`/`end_col_offset` 是 UTF-8 **字节**偏移，含中文时不能直接用于 `str` 切片；`tokenize` 的位置是**字符**偏移，docstring 精确列位置必须取自 tokenize
  - docstring 内容按纯文本格式化（`format_for(inner, 'x.txt')`）行为确定；整段按 `.py` 格式化行为不一致（实测），勿用

---

### Task 1: 依赖与 autocorrect 配置基座

**Files:**
- Modify: `pyproject.toml`（dev 依赖组）
- Create: `.autocorrectrc`
- Create: `.autocorrectignore`
- Modify: `uv.lock`（uv add 自动）

**Interfaces:**
- Consumes: 无
- Produces: dev 组含 `autocorrect-py`、`pre-commit`；仓库根存在 `.autocorrectrc`（`spellcheck: 0`、`context.codeblock: 0`）与 `.autocorrectignore`（`uv.lock`、`.opencode/node_modules`），Task 2 的 `_ensure_config`/`_load_ignore_patterns` 依赖这两个文件

- [ ] **Step 1: 添加 dev 依赖**

```bash
uv add --dev autocorrect-py pre-commit
```

- [ ] **Step 2: 创建 `.autocorrectrc`**

```yaml
# yaml-language-server: $schema=https://huacnlee.github.io/autocorrect/schema.json
# CJK 文案排版规则：默认规则保持，仅关掉实验性拼写检查与 Markdown 代码块格式化
# 为什么关 codeblock：保护 notes/ 里的 state dump 与实验代码样本不被改写
rules:
  spellcheck: 0
context:
  codeblock: 0
```

- [ ] **Step 3: 创建 `.autocorrectignore`**

```
# 自动生成物不参与文案格式化
uv.lock
.opencode/node_modules
```

- [ ] **Step 4: 验证依赖与配置可加载**

```bash
uv run python -c "
import autocorrect_py as ac
ac.load_config(open('.autocorrectrc', encoding='utf-8').read())
r = ac.format_for('基于DeepAgents构建,这是测试.', 'x.md')
assert r == '基于 DeepAgents 构建，这是测试。', r
print('ok')
"
```

Expected: 输出 `ok`

- [ ] **Step 5: Lint + 提交**

```bash
uv run ruff check . && uv run ruff format --check .
git add pyproject.toml uv.lock .autocorrectrc .autocorrectignore
git commit -m "chore: 引入 autocorrect-py 与 pre-commit 依赖及文案排版规则配置"
```

---

### Task 2: `tools/copywriting.py` 薄封装 CLI（TDD）

**Files:**
- Create: `tools/copywriting.py`
- Create: `tests/test_copywriting.py`
- Modify: `pyproject.toml:43-44`（pytest 配置加 `pythonpath`）

**Interfaces:**
- Consumes: Task 1 的 `.autocorrectrc`/`.autocorrectignore`、`autocorrect_py` SDK
- Produces: `format_python(content: str) -> str`（仅格式化注释/docstring）、`format_file(path: Path, *, fix: bool = True) -> bool`（返回是否有改动）、`main(argv: list[str] | None = None) -> int`（0 干净 / 1 有修改或失败）。Task 3 的 pre-commit hook 与 CI 以 `uv run python tools/copywriting.py [--lint] [files...]` 调用

- [ ] **Step 1: pytest 配置支持从仓库根导入**

`pyproject.toml` 的 `[tool.pytest.ini_options]` 改为：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: 写失败测试**

创建 `tests/test_copywriting.py`：

```python
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
        content = 'def f():\n    """第一行:说明,\n\n    第二行:细节.\n    """\n    return 1\n'
        expected = 'def f():\n    """第一行：说明，\n\n    第二行：细节。\n    """\n    return 1\n'
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
```

- [ ] **Step 3: 运行测试确认失败**

```bash
uv run pytest tests/test_copywriting.py -q
```

Expected: FAIL，`ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 4: 实现 `tools/copywriting.py`**

```python
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
    """读取 .autocorrectignore 的裸模式（# 注释行忽略）。"""
    if not IGNORE_PATH.exists():
        return []
    lines = IGNORE_PATH.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def _is_ignored(path: Path, patterns: list[str]) -> bool:
    """简化版 gitignore 语义：相对路径全匹配、文件名匹配、目录前缀匹配。"""
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
        listing = subprocess.run(
            ["git", "ls-files"], capture_output=True, text=True, check=True, cwd=REPO_ROOT
        )
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
```

注意：若 `test_multiline_docstring` 因 autocorrect 对多行文本的具体行为差异而失败，以实际输出修正 expected 值（先运行 `uv run python -c "import autocorrect_py as ac; print(repr(ac.format_for('第一行:说明,\\n\\n    第二行:细节.', 'x.txt')))"` 查看实际行为，保持断言与工具真实行为一致，勿改实现迁就断言）。

- [ ] **Step 5: 运行测试确认通过**

```bash
uv run pytest tests/test_copywriting.py -v
```

Expected: 全部 PASS

- [ ] **Step 6: 全量验证 + 提交**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest -q
git add tools/copywriting.py tests/test_copywriting.py pyproject.toml
git commit -m "feat: copywriting 薄封装 CLI，py 文件仅格式化注释与 docstring"
```

---

### Task 3: pre-commit 集成与端到端验证

**Files:**
- Create: `.pre-commit-config.yaml`

**Interfaces:**
- Consumes: Task 1 依赖、Task 2 的 `tools/copywriting.py` CLI
- Produces: `git commit` 时自动执行 ruff-lint → ruff-format → copywriting 三 hook；修复文件后提交中断（人工 `git add -u` 重提）

- [ ] **Step 1: 创建 `.pre-commit-config.yaml`**

```yaml
# 提交前格式化：ruff 修代码排版，copywriting 修 CJK 文案排版
# 为什么用 local hooks：版本跟随 uv.lock，与 CI 单一事实来源
repos:
  - repo: local
    hooks:
      - id: ruff-lint
        name: ruff check --fix
        entry: uv run ruff check --fix
        language: system
        types: [python]
      - id: ruff-format
        name: ruff format
        entry: uv run ruff format
        language: system
        types: [python]
      - id: copywriting
        name: copywriting (CJK 排版)
        entry: uv run python tools/copywriting.py
        language: system
        files: \.(py|md|markdown|ya?ml|toml|json|txt|cfg|ini|example)$|^AGENTS\.md$
```

- [ ] **Step 2: 安装 hook 并验证**

```bash
uv run pre-commit install
ls .git/hooks/pre-commit
```

Expected: `pre-commit installed at .git/hooks/pre-commit`

- [ ] **Step 3: 端到端验证（脏文件 → 提交中断 → 已修复未 re-stage）**

```bash
printf '基于DeepAgents构建,测试.\n' > .tmp-hook-e2e.md
git add .tmp-hook-e2e.md
git commit -m "wip: hook e2e"; echo "exit=$?"
cat .tmp-hook-e2e.md
git reset .tmp-hook-e2e.md && rm .tmp-hook-e2e.md
```

Expected: `exit=1`（提交被中断），文件内容已变为 `基于 DeepAgents 构建，测试。`

- [ ] **Step 4: 全仓首次格式化（人工 review 门禁）**

```bash
uv run python tools/copywriting.py
git diff --stat
```

仔细 review 全部 diff（预期集中在 AGENTS.md、notes/ 等中文文档的标点/间距），确认无误后：

```bash
git add -u && git commit -m "chore: 全仓 CJK 文案排版首次修正"
```

若无 diff 则跳过 commit。

- [ ] **Step 5: 提交配置**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: pre-commit 挂载 ruff 与 copywriting 提交前格式化"
```

---

### Task 4: CI 与文档同步

**Files:**
- Modify: `.github/workflows/ci.yml:25-26`（format check 后插入 copywriting lint）
- Modify: `AGENTS.md`（§3 结构图、§5 提交说明）

**Interfaces:**
- Consumes: Task 2 的 `--lint` 模式
- Produces: CI 增加 `Copywriting lint` 步骤；AGENTS.md 记录 `uv run pre-commit install` onboarding

- [ ] **Step 1: CI 增加 lint 步骤**

`.github/workflows/ci.yml` 在 `Format check (ruff format)` 步骤之后插入：

```yaml
      - name: Copywriting lint (autocorrect)
        run: uv run python tools/copywriting.py --lint
```

- [ ] **Step 2: AGENTS.md 同步**

§3 项目结构图中 `├── tests/` 行之前插入：

```
├── tools/                     # 开发辅助脚本（copywriting CJK 排版）
```

§5 「格式化与 Lint」小节末尾追加：

```markdown
### 提交前 Hook

- 仓库根执行 `uv run pre-commit install` 启用：`ruff check --fix` → `ruff format` → `tools/copywriting.py`（CJK 文案排版，中文句全角标点、中英文加空格；`.py` 仅动注释/docstring）
- hook 修复文件后提交会中断，review 后 `git add -u` 重新提交
- 规则配置见 `.autocorrectrc`，忽略清单见 `.autocorrectignore`
```

- [ ] **Step 3: 本地等价 CI 验证 + 提交**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest -q \
  && uv run python tools/copywriting.py --lint
git add .github/workflows/ci.yml AGENTS.md
git commit -m "chore: CI 增加 copywriting lint，AGENTS.md 记录 pre-commit onboarding"
```

---

## 自审记录

- 规格覆盖：§4 组件（Task 1 配置、Task 2 CLI、Task 3 pre-commit）✓；§7 错误处理（逐文件捕获、退出码）✓；§8 测试全覆盖 ✓；§9 CI/文档（Task 4）✓
- 类型一致性：`format_python`/`format_file`/`main` 签名在 Task 2 Interfaces 与实现一致；Task 3/4 调用方式与 Task 2 产出的 CLI 参数一致
- 核心实现代码已在本机原型验证（含中英混排、f-string 保护、幂等性、tokenize 字节偏移陷阱）
