# 学习笔记

实验结论沉淀目录。每组实验一份笔记：`<NN>-<topic>.md`（如 `01-filesystem.md`）。

结构建议：结论先行 → 证据（state dump / trace 片段）→ 与 harness9 对照 → 对
`assistant/` 产品侧的影响。

证据排版约定：state dump 等证据文档含嵌套三反引号字面量时，外层代码块用四反引号
包裹。实测（2026-08-27，`context.codeblock: 0` 下）：块内直接文本不被改写，但嵌套
围栏邻近行仍可能被误判排版；逐字保真的证据以 `.autocorrectignore` 豁免兜底。
