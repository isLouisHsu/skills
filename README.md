# Skills writen by Louis

个人 Agent 技能库，包含媒体处理和项目管理的实用工具。

## Skills 列表

| Skill | 描述 | 位置 |
|-------|------|------|
| **project-interview** | 通过交互式问答采访，引导用户梳理项目信息，详情见[Project Interview Skill：用一场对话，把模糊的项目变成结构清晰的文档](https://louishsu.xyz/2026/05/09/skill_project_interview.html) | `skills/project-interview/` |
| **project-docs-manager** | 以文档为中心的 AI 任务流程管理，详情见[Project Docs Manager Skill：让 AI 自主驱动项目迭代的文档引擎](https://louishsu.xyz/2026/04/05/project_docs_manager_skill.html) | `skills/project-docs-manager/` |
| **video-knowledge-purify** | 将视频内容转换为结构化 Markdown 笔记，详情见[Video Knowledge Purify Skill：让视频变成可检索的结构化知识笔记](https://louishsu.xyz/2026/04/02/skill_video_knowledge_purify.html) | `skills/video-knowledge-purify/` |
| **bilibili-downloader** | 下载 B 站视频（单个或专辑/合集） | `skills/bilibili-downloader/` |

## 快速开始

每个 skill 都是独立的，包含自己的文档和脚本。

### 安装 Skills

通过 `npx skills` 从 GitHub 安装 skill 到 Agent：

```bash
# 安装指定 skill
npx skills add https://github.com/isLouisHsu/skills --skill project-docs-manager

# 安装所有 skills
npx skills add https://github.com/isLouisHsu/skills
```

### 查看 Skill 文档

```bash
cat skills/<skill-name>/SKILL.md
```

### 安装依赖

```bash
# bilibili-downloader
pip install requests tenacity av openpyxl

# video-knowledge-purify
pip install faster-whisper av openai python-dotenv
```

### 使用示例

```bash
# 下载 B 站视频
python skills/bilibili-downloader/scripts/download_video.py single BV1hKywBAEkq ./downloads

# 视频转笔记
python skills/video-knowledge-purify/scripts/purify_video.py video.mp4 ./notes
```

## 项目结构

```
skills/
├── <skill-name>/
│   ├── SKILL.md          # Skill 文档（使用说明）
│   ├── scripts/          # Python 实现
│   └── references/       # 参考文档（复杂 skills）
```

## 开发规范

- Python 3.10+，使用类型注解
- CLI 使用 `argparse`
- 结构化数据使用 `@dataclass`
- 网络请求使用 `tenacity` 处理重试
- 视频处理使用 `PyAV`

## 相关文件

- [CLAUDE.md](./CLAUDE.md) - Claude Code 操作指南
