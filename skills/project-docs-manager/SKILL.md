---
name: project-docs-manager
description: 文档驱动的 AI 自主迭代引擎。维护结构化项目文档库作为 AI 的操作系统，让 AI 自主理解现状、提出方案、执行变更、回收效果、沉淀知识，形成完整迭代闭环。用户用自然语言对话即可驱动全流程，无需记忆具体命令。当用户消息涉及项目迭代推进、了解现状、追溯决策、沉淀知识、更新文档等意图时触发
user-invokable: true
---

# project-docs-manager

以文档为中心的 AI 任务流程管理技能。维护结构化项目文档库，让 AI 自主理解项目全貌、历史决策和当前状态，形成"背景 → 分析 → 方案 → 实施 → 效果"的完整闭环。

## Design Philosophy

**文档是 AI 的操作系统，不是人的操作对象。** 这不只是一个文档管理工具——它要实现的是让 AI 能够自主地理解项目现状、提出优化方向、执行变更、回收效果、沉淀知识，然后基于新的认知发起下一轮迭代，全程不依赖人类重新交代背景。人类只在关键决策点把关，其余由 AI 自主驱动。

**用户用自然语言对话，无需记命令。** 除首次初始化外，所有操作都通过自然语言触发。用户说意图，AI 自己去读对应的文档、做分析、执行、写回结果。

核心原则：
1. 单一事实源（Single Source of Truth）：所有项目知识沉淀在项目文档库中，不散落在聊天记录里。文档库是 AI 和人类共同的唯一参考。
2. 机器可读优先（Machine-Readable First）：文档使用固定的 section、字段和格式，而非随意叙事。AI 能快速解析、定位和更新。
3. 闭环自更新（Self-Updating Loop）：每次迭代结束后，AI 必须更新文档，确保下一次 session 看到的是最新状态。绝不留"口头约定"。
4. 一轮一文件（One Iteration, One Change File）：一项迭代的全部内容（业务背景、方案分析、审批决策、实施过程、效果数据、经验总结）维护在同一份 `changes/*.md` 文件中，完整记录从发起到归档的全过程。

## Key Paths

本技能文档中使用以下路径占位符：

| 占位符 | 说明 |
|--------|------|
| `{docs_path}` | 仓库内文档库路径，仅存放 `_INDEX.md` 作为入口索引 |
| `{media_path}` | 文档媒介路径，即实际文档存放位置（本地目录 / Obsidian vault / 云端 URL） |

## Standard Architecture

项目文档库采用"仓库索引 + 媒介详情"两层架构，AI 先扫索引做决策，只在必要时打开详情：

```
{docs_path}/                    # 仓库内（入口索引）
└── _INDEX.md                   # 目录索引（轻量，AI 优先扫描），链接指向 {media_path}

{media_path}/                   # 文档媒介（实际文档）
├── OVERVIEW.md                 # 全局概览 + 当前进展
├── CHANGELOG.md                # 变更历史索引（时间倒排，一句话摘要）
├── KNOWLEDGE.md                # 知识库索引（一句话摘要）
├── INVESTIGATION.md            # 调研索引（探索性调研、数据分析、可行性验证）
├── changes/                    # 变更详情
│   └── YYYY-MM-DD_xxx.md
├── knowledge/                  # 知识详情
│   └── topic_xxx.md
└── investigations/             # 调研详情
    └── YYYY-MM-DD_xxx.md
```

### File Responsibilities

| 文件 | 职责 | AI 扫描优先级 |
|------|------|---------------|
| `{docs_path}/_INDEX.md` | 文档库全局目录，列出每个文件路径和一句话说明 | **最高** — 每次 session 首先读取 |
| `{media_path}/OVERVIEW.md` | 项目背景、目标、当前状态、核心指标、团队分工 | 高 — 理解项目全貌 |
| `{media_path}/CHANGELOG.md` | 变更历史索引，每条记录：日期、标题、一句话结果、详情链接 | 高 — 了解迭代历史 |
| `{media_path}/KNOWLEDGE.md` | 知识条目索引，每条：主题、一句话说明、详情链接 | 中 — 按需查阅 |
| `{media_path}/INVESTIGATION.md` | 调研条目索引，每条：主题、一句话说明、详情链接、日期 | 中 — 按需查阅 |
| `{media_path}/changes/*.md` | 单次变更详情：背景、方案、实施、结果、TODO | 低 — 仅需深入时打开 |
| `{media_path}/knowledge/*.md` | 单个知识主题详情：定义、上下文、相关链接 | 低 — 仅需深入时打开 |
| `{media_path}/investigations/*.md` | 单次调研详情：问题定义、数据源、调研方案、结论 | 低 — 仅需深入时打开 |

### AI 自动读取依赖链

`{docs_path}/_INDEX.md` 的"每次 session 首先读取"依赖于在项目 `CLAUDE.md` 中注册文档库路径。完整链路：

```
CLAUDE.md（AI 每次 session 自动加载）
  → 包含文档库路径和操作规范
    → 指示 AI 首先读取 {docs_path}/_INDEX.md
      → {docs_path}/_INDEX.md 引导 AI 按需读取 {media_path}/ 下的文档
```

初始化流程的 Step 5 会自动完成此注册。如果 `CLAUDE.md` 中缺少文档库配置，AI 将无法自动感知文档库的存在。

## Document Maintenance Rules

### Cross-Reference（交叉引用）
- 在关键位置标注跳转链接，格式：`→ 详见 [文件名](相对路径)`
- 新增或修改文档时，同步更新所有引用该文档的地方
- `{docs_path}/_INDEX.md` 中每个条目都必须有可点击的链接

### Index Discipline（索引纪律）
- `{docs_path}/_INDEX.md` 只维护顶层索引文件（OVERVIEW / CHANGELOG / KNOWLEDGE / INVESTIGATION）的链接，不直接列出子文档
- `{media_path}/CHANGELOG.md`、`{media_path}/KNOWLEDGE.md`、`{media_path}/INVESTIGATION.md` 是二级索引文件，只放摘要和链接，不放详情
- 索引条目控制在一行以内（< 150 字符）
- 详情一律放在 `{media_path}/changes/`、`{media_path}/knowledge/` 或 `{media_path}/investigations/` 子目录

### Update Protocol（更新协议）
每次文档变更必须：
1. `{docs_path}/_INDEX.md` 只维护顶层索引文件链接（OVERVIEW / CHANGELOG / KNOWLEDGE / INVESTIGATION），仅在新增顶层索引文件时更新
2. 新增子文档时，更新对应的索引文件（`CHANGELOG.md` / `KNOWLEDGE.md` / `INVESTIGATION.md`），不要加到 `_INDEX.md`
3. 更新 `{media_path}/OVERVIEW.md` 中的"当前进展"（如状态变化）
4. 检查并更新相关文档中的交叉引用链接

## Workflow Dispatch

根据用户自然语言意图分发到对应流程。除初始化外，用户无需记忆具体命令。

### Iteration Lifecycle（迭代生命周期）

一轮完整迭代遵循以下闭环，每个环节的产出都追加到同一份 `changes/YYYY-MM-DD_xxx.md` 文件中：

```
① 推进迭代 → ② 确认执行 → ③ 实施推进 → ④ 回收效果 → ⑤ 整理分析 → ⑥ 沉淀归档 → 回到 ①
```

### Operations（操作一览）

| 操作 | 触发方式 | 说明 |
|------|----------|------|
| **初始化文档库** | `/project-docs-manager 初始化项目文档库` | 仅首次，→ [INITIALIZE.md](./references/INITIALIZE.md)：扫描项目 → 创建文档骨架 → 注册到 CLAUDE.md |
| **了解现状** | 「目前的进展和效果」「距离目标还有多远」「当前项目状态是什么」 | AI 读取 `_INDEX.md` → `OVERVIEW.md` → `CHANGELOG.md` 汇总 |
| **追溯历史** | 「为什么当时这么决策」「上次那个方案效果怎么样」「之前试过哪些方案」 | AI 读取 `CHANGELOG.md` → 打开对应 `changes/*.md` 深入分析 |
| **查阅知识** | 「之前有没有踩过类似的坑」「关于 XX 有什么已知约束」 | AI 读取 `KNOWLEDGE.md` → 打开对应 `knowledge/*.md` |
| **查阅调研** | 「之前做过 XX 方向的调研吗」「XX 的可行性分析结论是什么」 | AI 读取 `INVESTIGATION.md` → 打开对应 `investigations/*.md` |
| **记录调研** | 「做一下 XX 方向的调研」「分析一下 XX 的可行性」 | AI 执行探索性调研 → 写入 `investigations/*.md` → 更新 INVESTIGATION.md 索引 |
| **推进迭代** | 「下一步可以做什么」「对比一下方案 A 和 B」 | 业务背景 -> AI 差距分析 → 提出方案 + 推荐理由 + 风险评估 → 创建本轮 `changes/YYYY-MM-DD_xxx.md`，记录方案分析。→ [UPDATE.md](./references/UPDATE.md) |
| **确认执行** | 「好，按方案 A 执行」 | 人类审批，AI 在同一份 change 文件中记录审批决策和理由，开始实施 |
| **纠偏调整** | 「方向不对，换方案 B」「这个先放一下，优先做 XX」 | AI 在同一份 change 文件中记录中止原因，按新方向重新进入迭代循环 |
| **实施推进** | 「这个模块先评审一下」「继续」「进展如何」 | AI 按方案落地，模块级汇报，人类随时介入评审；实施过程追加到同一份 change 文件 |
| **回收效果** | 「效果怎么样」「跑一下前后对比」「数据出来了吗」 | AI 收集前后对比数据，汇总效果指标，判断是否达标；效果数据追加到同一份 change 文件 |
| **整理分析** | 「总结一下这次迭代」「有什么新发现」「哪些经验值得记录」 | AI 分析成败原因，提炼知识；结论追加到同一份 change 文件，可复用知识同步到 `KNOWLEDGE.md` |

## Document Templates

文档库创建时使用 `references/templates/` 目录下的标准模板：

| 模板文件 | 用途 |
|----------|------|
| [`templates/_INDEX.md`](./references/templates/_INDEX.md) | 仓库索引模板 |
| [`templates/OVERVIEW.md`](./references/templates/OVERVIEW.md) | 项目概览模板 |
| [`templates/CHANGELOG.md`](./references/templates/CHANGELOG.md) | 变更历史索引模板 |
| [`templates/KNOWLEDGE.md`](./references/templates/KNOWLEDGE.md) | 知识库索引模板 |
| [`templates/change_detail.md`](./references/templates/change_detail.md) | 单次变更详情模板 |
| [`templates/knowledge_detail.md`](./references/templates/knowledge_detail.md) | 知识主题详情模板 |

**注意**：初始化文档库时，AI 应复制上述模板文件到用户的 `{media_path}/` 目录，而不是让用户直接修改 skill 目录下的模板本身。

## Supported Document Media

项目仅维护 `{docs_path}/_INDEX.md` 作为入口索引，其余文档（`{media_path}/OVERVIEW.md`、`{media_path}/CHANGELOG.md`、`{media_path}/KNOWLEDGE.md`、`{media_path}/INVESTIGATION.md`、`{media_path}/changes/`、`{media_path}/knowledge/`、`{media_path}/investigations/`）均创建在用户选择的文档媒介中。

支持的媒介：
- **本地目录**（默认）：文档创建在用户指定的本地路径，`{docs_path}/_INDEX.md` 中以相对/绝对路径链接
- **本地文档库（Obsidian）**：文档创建在 Obsidian vault 内，利用双向链接和标签系统
- **云文档**（钉钉文档、Notion 等）：文档在云端平台维护，`{docs_path}/_INDEX.md` 中以云端 URL 引用

初始化时会询问用户偏好的媒介，差异化处理详见 → [INITIALIZE.md](./references/INITIALIZE.md)。