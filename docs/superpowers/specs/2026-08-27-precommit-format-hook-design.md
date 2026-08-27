# Git 提交前自动格式化 Hook（ruff + autocorrect）设计

- 日期：2026-08-27
- 状态：已确认
- 方案：B（`autocorrect-py` SDK + 薄封装脚本 + pre-commit 框架）

## 1. 背景与目标

项目现状：ruff 配置齐全（行宽 100、`E/F/W/I/UP/B`），AGENTS.md 规定提交前 `ruff + pytest` 全绿，但完全依赖手动执行；中文注释与文档（`notes/`、`AGENTS.md`）的排版（中英文间距、全角/半角标点）无任何工具约束。

目标：每次 `git commit` 前，自动完成：

1. Python 代码格式化（ruff lint --fix + ruff format，含空行、缩进规范）
2. 注释与文档的 CJK 排版修正（中英文之间加空格、中文句内标点转全角）

## 2. 需求决策记录

| 决策点 | 选择 |
|--------|------|
| 标点规则 | 中文句内用全角标点（，。：；），中英文/数字之间加空格 |
| 作用范围 | 代码注释/docstring + Markdown 文档 + 配置文件注释（全量） |
| hook 管理 | pre-commit 框架（`.pre-commit-config.yaml` 入库，协作者/CI 复用） |
| 修复后行为 | hook 自动修复文件但不重新 stage，提交中断，人工 review 后 `git add -u` 重提 |

## 3. 方案选型

选定**方案 B**：`autocorrect-py` SDK + 薄封装脚本。

- `autocorrect-py`（官方 PyPI 绑定）进 dev 依赖组，走 `uv.lock` 锁定，跨平台，CI 零额外安装
- 自写 ~80 行薄封装 CLI 弥补该包不带可执行文件的缺口
- 排除方案 A（brew 二进制，游离于 uv 依赖管理外，CI/换机器需额外安装）与方案 C（全自研正则，中文排版边界极多，重复造轮子）

加分项：`autocorrect_py.format_for()` 是纯函数 SDK，未来产品侧（factotum 文案输出规范化、飞书消息润色）可直接复用。

## 4. 组件构成

| 文件 | 职责 |
|------|------|
| `tools/copywriting.py` | 薄封装 CLI：读文件 → `autocorrect_py.format_for()` → 有变更写回并 exit 1；`--lint` 模式只报不改（供 CI）；无参数时默认处理 `git ls-files` 全量（手动全仓格式化入口）。**`.py` 文件特殊处理**：autocorrect 默认会连字符串字面量一起改写（实测 `"错误:配置加载失败."` → `"错误：配置加载失败。"`），会破坏运行时文案与 AGENTS.md 错误消息约定，故对 `.py` 仅格式化注释与 docstring（tokenize 定位注释 token + ast 定位 docstring，按纯文本格式化其内容后原位拼回；注意 CPython `col_offset` 是 UTF-8 字节偏移，精确列位置必须取自 tokenize） |
| `.autocorrectrc` | 规则配置（见 §6） |
| `.autocorrectignore` | 忽略清单：`uv.lock`、`.opencode/node_modules/` 等自动生成物 |
| `.pre-commit-config.yaml` | 三个 local hook（`language: system`，经 `uv run` 调用），版本始终跟 `uv.lock` 走 |
| `pyproject.toml` | dev 组新增 `autocorrect-py` + `pre-commit` |

## 5. 执行流

```
git commit
 └─ pre-commit 按 hook 顺序处理暂存文件
     1. uv run ruff check --fix   # import 排序等自动修复
     2. uv run ruff format        # 代码格式化
     3. uv run python tools/copywriting.py <files>  # CJK 排版
 ├─ 任一 hook 修改文件 → 提交中断（pre-commit 标准行为）
 │    review diff → git add -u → 重新 commit
 └─ 全部无改动 → 提交放行
```

copywriting 放最后：其输出不影响 ruff 两个环节，避免顺序耦合。

## 6. `.autocorrectrc` 关键规则

- `fullwidth: 1` — 中文句内标点转全角
- `space-word: 1` / `halfwidth-word: 1` 等默认规则保持
- `spellcheck: 0` — 关闭实验性拼写检查（误伤拼音、领域术语）
- `context.codeblock: 0` — 不格式化 Markdown 内代码块，保护 `notes/` 的 state dump 与实验代码样本

注意：`.autocorrectrc` 不会从 cwd 自动加载（实测 SDK 行为），封装脚本必须显式读取并调用 `load_config(config_str)`。

## 7. 错误处理

- 文件读写/编码异常：逐文件捕获，报文件名 + 原因，继续处理其余文件，最终 exit 1（单个坏文件不卡死整个提交）
- 不识别的文件类型：autocorrect 原样返回，无副作用
- 退出码约定：`0` 干净 / `1` 有修改或 lint 未过 / 内部错误归并 `1`（pre-commit 只关心非零）

## 8. 测试（`tests/test_copywriting.py`，表驱动）

- 中英加空格：`基于DeepAgents构建` → `基于 DeepAgents 构建`
- 全角标点：`这是第一句,第二句.` → `这是第一句，第二句。`
- 无改动：纯英文注释、纯代码
- `.py` 专属：注释与 docstring 被格式化，字符串字面量（含 f-string）原样保留；语法错误文件原样返回；幂等性（二次运行无变化）
- CLI 行为：fix 模式写回 + exit 1；`--lint` 不写 + exit 1；干净文件 exit 0
- 代码块保护：Markdown 内 code fence 内容不被改动

## 9. CI 与文档同步

- `ci.yml` 在 format check 后新增：`uv run python tools/copywriting.py --lint`
- AGENTS.md §3 结构图补 `tools/`，§5 补 pre-commit 说明
- 提示协作者：clone 后执行 `uv run pre-commit install`
