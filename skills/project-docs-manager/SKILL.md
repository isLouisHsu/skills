---
name: project-docs-manager
description: 以文档为中心的 AI 任务流程管理技能，维护结构化项目文档库，形成完整迭代闭环。当用户消息中包含"项目文档"、"文档库"、"文档管理"、"project docs"、"doc hub"、"docs manager"、"初始化文档"、"更新文档"、"文档迭代"等关键词时触发
user-invokable: true
---

# project-docs-manager

以文档为中心的 AI 任务流程管理技能。维护结构化项目文档库，让 AI 自主理解项目全貌、历史决策和当前状态，形成"背景 → 分析 → 方案 → 实施 → 效果"的完整闭环。核心原则是：
1. 单一事实源（Single Source of Truth）：所有项目知识沉淀在项目文档库中，不散落在聊天记录里。文档库是 AI 和人类共同的唯一参考。
2. 机器可读优先（Machine-Readable First）：文档使用固定的 section、字段和格式，而非随意叙事。AI 能快速解析、定位和更新。
3. 闭环自更新（Self-Updating Loop）：每次迭代结束后，AI 必须更新文档，确保下一次 session 看到的是最新状态。绝不留"口头约定"。

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
├── changes/                    # 变更详情
│   └── YYYY-MM-DD_xxx.md
└── knowledge/                  # 知识详情
    └── topic_xxx.md
```

### File Responsibilities

| 文件 | 职责 | AI 扫描优先级 |
|------|------|---------------|
| `{docs_path}/_INDEX.md` | 文档库全局目录，列出每个文件路径和一句话说明 | **最高** — 每次 session 首先读取 |
| `{media_path}/OVERVIEW.md` | 项目背景、目标、当前状态、核心指标、团队分工 | 高 — 理解项目全貌 |
| `{media_path}/CHANGELOG.md` | 变更历史索引，每条记录：日期、标题、一句话结果、详情链接 | 高 — 了解迭代历史 |
| `{media_path}/KNOWLEDGE.md` | 知识条目索引，每条：主题、一句话说明、详情链接 | 中 — 按需查阅 |
| `{media_path}/changes/*.md` | 单次变更详情：背景、方案、实施、结果、TODO | 低 — 仅需深入时打开 |
| `{media_path}/knowledge/*.md` | 单个知识主题详情：定义、上下文、相关链接 | 低 — 仅需深入时打开 |

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
- `{docs_path}/_INDEX.md`、`{media_path}/CHANGELOG.md`、`{media_path}/KNOWLEDGE.md` 是索引文件，只放摘要和链接，不放详情
- 索引条目控制在一行以内（< 150 字符）
- 详情一律放在 `{media_path}/changes/` 或 `{media_path}/knowledge/` 子目录

### Update Protocol（更新协议）
每次文档变更必须：
1. 更新 `{docs_path}/_INDEX.md`（如有新文件）
2. 更新 `{media_path}/CHANGELOG.md`（追加变更记录）
3. 更新 `{media_path}/OVERVIEW.md` 中的"当前进展"（如状态变化）
4. 检查并更新相关文档中的交叉引用链接

## Workflow Dispatch

根据用户意图分发到对应流程：

| 用户意图 | 流程 | 说明 |
|----------|------|------|
| 首次创建文档库 | → [INITIALIZE.md](./references/INITIALIZE.md) | 检测 → 创建骨架 → 注册到 CLAUDE.md |
| 记录新的迭代/变更 | → [UPDATE.md](./references/UPDATE.md) | 收集输入 → 分析 → 实施 → 记录 → 更新索引 |
| 查看项目状态 | 直接读取 `{docs_path}/_INDEX.md` → `{media_path}/OVERVIEW.md` | 无需额外流程 |
| 查找历史决策 | 读取 `{media_path}/CHANGELOG.md` → 打开对应 `{media_path}/changes/*.md` | 按需深入 |
| 查阅知识 | 读取 `{media_path}/KNOWLEDGE.md` → 打开对应 `{media_path}/knowledge/*.md` | 按需深入 |

## Supported Document Media

项目仅维护 `{docs_path}/_INDEX.md` 作为入口索引，其余文档（`{media_path}/OVERVIEW.md`、`{media_path}/CHANGELOG.md`、`{media_path}/KNOWLEDGE.md`、`{media_path}/changes/`、`{media_path}/knowledge/`）均创建在用户选择的文档媒介中。

支持的媒介：
- **本地目录**（默认）：文档创建在用户指定的本地路径，`{docs_path}/_INDEX.md` 中以相对/绝对路径链接
- **本地文档库（Obsidian）**：文档创建在 Obsidian vault 内，利用双向链接和标签系统
- **云文档**（钉钉文档、Notion 等）：文档在云端平台维护，`{docs_path}/_INDEX.md` 中以云端 URL 引用

初始化时会询问用户偏好的媒介，差异化处理详见 → [INITIALIZE.md](./references/INITIALIZE.md)。