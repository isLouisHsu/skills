# INITIALIZE — 项目文档库初始化

← 返回 [SKILL.md](../SKILL.md)

## Purpose

检测当前项目是否已有文档库，如果没有则创建标准骨架并注册到项目配置中。支持**全新项目**和**已有项目**两种场景。

## Initialization Flow

### Step 1: 检测现有文档库

```
检查项目根目录下是否存在以下任一标志：
- {docs_path}/_INDEX.md
- CLAUDE.md 中包含 "project-docs" 引用

如果已存在 → 提示用户"文档库已初始化"，询问是否需要修复/补全
如果不存在 → 继续 Step 2
```

### Step 2: 判断项目类型

通过以下信号判断当前是全新项目还是已有项目：

| 信号 | 检测方式 |
|------|----------|
| git 历史 | `git log --oneline -1`：有提交记录 → 已有项目 |
| 代码文件 | `ls` / `Glob`：存在源代码文件 → 已有项目 |
| README / CLAUDE.md | 存在项目说明文件 → 已有项目 |
| 依赖文件 | 存在 package.json / requirements.txt / go.mod 等 → 已有项目 |

```
如果是全新项目 → 走 Step 3A（全新项目流程）
如果是已有项目 → 走 Step 3B（已有项目流程）
```

### Step 3A: 全新项目 — 收集信息

向用户收集以下信息（用 AskUserQuestion 或从上下文推断）：

1. **项目名称**：用于 `{media_path}/OVERVIEW.md` 标题
2. **项目简介**：一句话描述项目目标
3. **文档媒介偏好**：本地目录（默认） / Obsidian / 云文档
4. **文档库路径**：默认为 `{项目根目录}/project-docs/`

→ 然后跳到 Step 4 创建骨架（模板中的内容留空待用户填写）

### Step 3B: 已有项目 — 自动探测与知识提炼

已有项目的初始化不应该留一堆"待补充"的空模板，而是 **AI 主动从项目中提取知识，预填充文档**。

#### 3B.1 向用户确认基本信息

先快速确认（部分可从 README / package.json 等自动推断）：

1. **项目名称**：从 README 标题、package.json name、目录名推断，让用户确认
2. **项目简介**：从 README 首段推断，让用户确认或补充
3. **文档媒介偏好**：本地目录（默认） / Obsidian / 云文档
4. **文档库路径**：默认为 `{项目根目录}/project-docs/`

#### 3B.2 自动探测项目现状

按以下顺序扫描，提取项目知识：

**① 项目结构扫描**
```
- 用 Glob 扫描目录结构（排除 node_modules、.git、dist 等）
- 识别项目类型：前端/后端/全栈/数据/脚本/库
- 识别技术栈：语言、框架、构建工具、包管理器
- 识别项目分层：src 结构、模块划分
```

**② 已有文档扫描**
```
扫描以下文件，提取可用信息：
- README.md / README：项目介绍、安装步骤、使用方法
- CLAUDE.md：已有的 AI 协作规范
- CONTRIBUTING.md：贡献指南、开发流程
- docs/ 目录：已有文档
- .env.example：环境变量说明
- Makefile / Justfile / scripts/：可用的脚本命令
```

**③ Git 历史分析**
```
- git log --oneline -20：获取最近 20 条提交，了解开发节奏和重点
- git log --oneline --since="3 months ago" --format="%ad %s" --date=short：
  最近 3 个月的提交，按时间排列
- git log --all --oneline | wc -l：总提交数，判断项目成熟度
- git branch -a：分支情况，了解并行开发状态
- git tag：版本发布历史
```

**④ 依赖与配置扫描**
```
- package.json / requirements.txt / go.mod / Cargo.toml：依赖清单
- 配置文件（tsconfig、webpack、vite、eslint 等）：项目约定
- CI/CD 配置（.github/workflows、.gitlab-ci.yml）：部署流程
```

#### 3B.3 AI 提炼与预填充

基于探测结果，AI 主动填充文档内容（而非留空）：

**`{media_path}/OVERVIEW.md` 预填充**：
- **项目信息**：从探测结果自动填写名称、目标、技术栈、项目类型
- **当前进展**：从 git 最近提交和分支状态推断当前开发阶段
- **技术架构**：从目录结构和代码分层自动生成架构概述
- **核心指标**：根据项目类型建议合适的指标（如 API 项目建议响应时间/错误率，前端项目建议包体积/性能分数）

**`{media_path}/CHANGELOG.md` 预填充**：
- 从 git 历史中提取 **关键里程碑**（不是逐条搬运 commit）
- 筛选策略：
  - git tag 对应的版本发布
  - merge commit（代表功能合入）
  - 提交信息中含 feat/fix/breaking 等关键词的重要变更
- 每条记录：日期、标题、一句话摘要
- 最多提取最近 10 条关键变更，避免信息过载

**`{media_path}/KNOWLEDGE.md` 预填充**：
- 从探测到的技术栈、架构模式、项目约定中提炼知识条目
- 常见的初始知识条目：
  - 技术栈概述（语言、框架、核心依赖）
  - 项目结构说明（目录分层、模块职责）
  - 开发环境配置（如何启动、如何测试）
  - 部署流程（如有 CI/CD 配置）

对于每个预填充的知识条目，在 `{media_path}/knowledge/` 下创建对应的详情文件。

#### 3B.4 用户审核

将预填充的文档内容展示给用户审核：

```
向用户展示：
1. {media_path}/OVERVIEW.md 预填充内容摘要
2. {media_path}/CHANGELOG.md 提取的关键变更列表
3. {media_path}/KNOWLEDGE.md 识别的知识条目列表

询问：
- 是否有需要修正的信息？
- 是否有遗漏的重要背景需要补充？
- 是否有不需要的条目需要删除？

用户确认后 → 继续 Step 4
```

### Step 4: 创建文档库骨架

按以下结构创建文件：

```
{docs_path}/                    # 仓库内（入口索引）
└── _INDEX.md                   # 链接指向 {media_path} 下的文档

{media_path}/                   # 文档媒介（实际文档）
├── OVERVIEW.md
├── CHANGELOG.md
├── KNOWLEDGE.md
├── changes/
│   └── .gitkeep
└── knowledge/
    └── .gitkeep
```

各文件模板 → 详见 [templates/](./templates/) 目录：

| 文件 | 模板 |
|------|------|
| `_INDEX.md` | [templates/_INDEX.md](./templates/_INDEX.md) |
| `OVERVIEW.md` | [templates/OVERVIEW.md](./templates/OVERVIEW.md) |
| `CHANGELOG.md` | [templates/CHANGELOG.md](./templates/CHANGELOG.md) |
| `KNOWLEDGE.md` | [templates/KNOWLEDGE.md](./templates/KNOWLEDGE.md) |

使用模板时，将以下占位符替换为实际值：

| 占位符 | 说明 |
|--------|------|
| `{项目名称}` | 项目名称 |
| `{项目简介}` | 一句话项目目标 |
| `{YYYY-MM-DD}` | 当前日期 |
| `{docs_path}` | 仓库内文档库路径（存放 `_INDEX.md` 的目录） |
| `{media_path}` | 文档媒介路径，即实际文档存放位置。本地目录模式下为用户指定的本地路径，Obsidian 模式下为 vault 内路径，云文档模式下替换为云端 URL |

#### 文档媒介差异化处理

根据用户在 Step 3 中选择的媒介，Step 4 的创建行为有所不同。所有媒介下，项目 `{docs_path}/` 仅维护 `_INDEX.md` 作为入口索引，其余文档均创建在用户选择的媒介中。

**本地目录（默认）**：
- 文档创建在用户指定的本地路径（如 `~/docs/project-name/`）
- `{docs_path}/_INDEX.md` 中以相对或绝对路径链接到该目录下的文件

**本地文档库（Obsidian）**：
- 文档创建在用户指定的 Obsidian vault 内（如 `{vault_path}/project-docs/`）
- 仓库中仅保留 `{docs_path}/_INDEX.md`，通过路径链接指向 vault 内的对应文件
- vault 内的文档使用 Obsidian 双向链接语法 `[[文件名]]` 替代 Markdown 相对路径
- vault 内文件顶部添加 Obsidian 元数据：`tags: [project-docs, {类型}]`
- 知识文件（`{media_path}/knowledge/*.md`）利用标签系统：`tags: [knowledge, {主题}]`
- 确认 vault 路径存在后再创建文件，否则提示用户先创建 vault

**云文档（钉钉文档、Notion 等）**：
- `{docs_path}/` 仅创建 `_INDEX.md`，其余文档均在云端平台维护
- `_INDEX.md` 中的链接指向云端 URL，初始格式为 `[待填写云端链接]()`，由用户在云端创建对应文档后回填
- `{media_path}/changes/` 和 `{media_path}/knowledge/` 目录不在本地创建，在 `{docs_path}/_INDEX.md` 中以云端链接形式维护
- `{docs_path}/_INDEX.md` 顶部追加说明：`> 本文档库采用"本地索引 + 云端详情"模式，详情文档请在云端平台查看。`

### Step 5: 注册到 CLAUDE.md

在项目根目录的 `CLAUDE.md` 中添加以下内容（如果 CLAUDE.md 不存在则创建）：

```markdown
## 项目文档库

本项目使用结构化文档库管理项目知识。
- 仓库索引：`{docs_path}/_INDEX.md`
- 文档媒介：`{media_path}/`

**AI 操作规范**：
1. 每次 session 开始时，先读取 `{docs_path}/_INDEX.md` 了解文档库全貌
2. 需要了解项目背景时，读取 `{media_path}/OVERVIEW.md`
3. 每次完成迭代后，必须更新相关文档（`{media_path}/OVERVIEW.md`、`{media_path}/CHANGELOG.md`、`{docs_path}/_INDEX.md`）
4. 新增文件时，必须同步更新 `{docs_path}/_INDEX.md`
5. 文档中的交叉引用链接必须保持有效
```

### Step 6: 输出初始化报告

向用户展示：
- 创建的文件列表
- 文档库路径
- 下一步建议（补充 `{media_path}/OVERVIEW.md`、记录第一次迭代）

## Error Handling

| 场景 | 处理 |
|------|------|
| 文档库已存在 | 提示用户，询问是否补全缺失文件 |
| 无写入权限 | 提示用户检查目录权限 |
| CLAUDE.md 已有文档库配置 | 跳过 Step 4，避免重复 |
| 用户选择云文档媒介 | 创建本地索引骨架，详情链接留空待用户填写云端 URL |
| git 仓库无提交历史 | 视为全新项目，走 Step 3A |
| git 历史过多（>1000 commits） | 只分析最近 3 个月 + tag 发布记录，避免耗时过长 |
| 探测到的信息与用户反馈冲突 | 以用户反馈为准，更新预填充内容 |
| 已有文档（README 等）内容过时 | 在 `{media_path}/OVERVIEW.md` 中标注"以下信息基于 README 提取，可能需要更新"，加入 TODO |
| 项目为 monorepo 多子项目 | 询问用户是建一个统一文档库还是每个子项目独立文档库 |