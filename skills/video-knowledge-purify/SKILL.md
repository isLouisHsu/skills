---
name: video-knowledge-purify
description: 将视频内容整理为结构化的 Markdown 知识笔记。当用户需要"整理视频内容"、"视频转笔记"、"生成视频摘要"、"提取视频知识"、"视频转文字并分段"时触发此 skill。支持音频转录、智能分段、视频帧提取、VLM 汇总生成 Markdown 笔记。
---

# 视频知识提纯器

将视频（配合 SRT 字幕）转换为结构化的 Markdown 知识笔记。流程：转录 → 分段 → 汇总。

## 依赖安装

使用前确保安装依赖：

```bash
pip install faster-whisper av openai python-dotenv torch
```

## 环境变量配置

需要配置模型 API 密钥（支持 OpenAI 格式）。**推荐使用 `scripts/.env` 文件**：

```bash
cp scripts/.env.example scripts/.env
# 编辑 scripts/.env 填入你的配置
```

### 配置示例（阿里云百炼）

```bash
# 用于视频内容分段（文本 LLM，建议用便宜快速的模型，如 qwen-turbo）
SRT_SEGMENTER_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
SRT_SEGMENTER_API_KEY=sk-your-api-key
SRT_SEGMENTER_MODEL=qwen-turbo

# 用于视频内容汇总（VLM，需要视觉能力，如 qwen-vl-plus）
SRT_MERGER_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
SRT_MERGER_API_KEY=sk-your-api-key
SRT_MERGER_MODEL=qwen-vl-plus
```

### 配置示例（OpenAI）

```bash
SRT_SEGMENTER_BASE_URL=https://api.openai.com/v1
SRT_SEGMENTER_API_KEY=sk-your-api-key
SRT_SEGMENTER_MODEL=gpt-4o-mini

SRT_MERGER_BASE_URL=https://api.openai.com/v1
SRT_MERGER_API_KEY=sk-your-api-key
SRT_MERGER_MODEL=gpt-4o
```

脚本会自动查找 `.env` 文件（优先使用 skill 目录下的 `.env`，其次是当前工作目录的 `.env`）。

## 批量处理规则

当用户需要对**多个视频**进行批量处理时（例如传入一个目录）：

1. **先写一个批量处理脚本**，而不是直接修改现有脚本
2. **脚本逻辑**：
   - 递归扫描目录，找出所有视频文件（支持 `.mp4`, `.mkv`, `.mov`, `.avi`, `.flv`, `.wmv`, `.m4v`, `.webm` 等格式）
   - 遍历每个视频，调用 `purify_video.py` 进行单独处理
   - 保持原有目录结构输出（或统一输出到指定目录）
   - 支持跳过已处理的视频，支持生成处理报告

## 使用方式

### 完整流程（一键生成笔记）

```bash
python scripts/purify_video.py <video_path> [srt_path] [output_dir] [options]
```

**参数说明：**
- `video_path`: 视频文件路径 (.mp4/.mkv/.mov 等)
- `srt_path`: SRT 字幕文件路径（可选，不提供则自动转录）
- `output_dir`: 输出目录（可选，默认与视频同目录）
- `--max-frames`: 每段落最大采样帧数（默认 8）
- `--whisper-model`: Whisper 模型大小（默认 medium，可选 tiny/base/small/medium/large-v2/large-v3）
- `--no-skip`: 禁用跳过已存在文件，强制重新处理（默认会跳过已存在的文件）

**示例：**
```bash
# 已有字幕，输出到视频同目录
python scripts/purify_video.py video.mp4 transcript.srt

# 已有字幕，指定输出目录
python scripts/purify_video.py video.mp4 transcript.srt ./notes

# 无字幕，自动转录后提纯（输出到视频同目录）
python scripts/purify_video.py video.mp4

# 无字幕，指定输出目录
python scripts/purify_video.py video.mp4 ./notes

# 指定更多帧和更大的 Whisper 模型
python scripts/purify_video.py video.mp4 --max-frames 12 --whisper-model medium

# 强制重新处理（不跳过已存在的文件）
python scripts/purify_video.py video.mp4 ./notes --no-skip
```

输出：
- `<output_dir>/note.md` - 最终的 Markdown 笔记
- `<output_dir>/frames/` - 提取的视频帧图片

### 分步执行

如果你需要更精细的控制，可以分步执行：

#### 步骤 1: 音频转录

```bash
python scripts/transcribe.py <input_path> [options]
```

**参数说明：**
- `--output-txt`, `-t`: 纯文本输出路径（可选，默认与输入同名 .txt）
- `--output-srt`, `-s`: SRT 字幕输出路径（可选，默认与输入同名 .srt）
- `--model`, `-m`: Whisper 模型大小（默认 medium，可选 tiny/base/small/medium/large-v2/large-v3）
- `--skip-existing`, `-k`: 如果输出文件已存在则跳过转录

**示例：**
```bash
# 默认输出到视频同目录（video.txt 和 video.srt）
python scripts/transcribe.py video.mp4

# 指定输出路径和模型
python scripts/transcribe.py video.mp4 --output-txt transcript.txt --output-srt transcript.srt --model large-v3

# 文件已存在时跳过
python scripts/transcribe.py video.mp4 -k
```

输出：
- `<input_dir>/<input_name>.txt`: 纯文本转录
- `<input_dir>/<input_name>.srt`: SRT 格式字幕（含时间戳）

#### 步骤 2: 内容分段

```bash
python scripts/segment_video.py <srt_path> [output_json] [options]
```

**参数说明：**
- `output_json`: 输出 JSON 路径（可选，默认与 SRT 同名 .json）
- `--skip-existing`, `-k`: 如果输出文件已存在则跳过

**示例：**
```bash
# 默认输出到 SRT 同目录（transcript.json）
python scripts/segment_video.py transcript.srt

# 指定输出路径
python scripts/segment_video.py transcript.srt segments.json

# 文件已存在时跳过
python scripts/segment_video.py transcript.srt -k
```

输出：
- `<srt_dir>/<srt_name>.json`: 按主题分段后的字幕组

**分段逻辑：**
调用 LLM 分析字幕内容，按主题边界划分为若干段落。每个段落围绕一个独立的知识点展开。

#### 步骤 3: 内容汇总（生成笔记）

```bash
python scripts/merge_segments.py <video_path> <segments_json> [output_dir] [options]
```

**参数说明：**
- `output_dir`: 输出目录（可选，默认视频所在目录）
- `--max-frames`, `-f`: 每段落最大采样帧数（默认 8）
- `--skip-existing`, `-k`: 如果笔记文件已存在则跳过

**示例：**
```bash
# 默认输出到视频同目录
python scripts/merge_segments.py video.mp4 segments.json

# 指定输出目录
python scripts/merge_segments.py video.mp4 segments.json ./notes --max-frames 8

# 文件已存在时跳过
python scripts/merge_segments.py video.mp4 segments.json ./notes -k
```

输出：
- `<output_dir>/note.md`: Markdown 笔记
- `<output_dir>/frames/`: 视频帧图片

**汇总逻辑：**
1. 对每个主题段落，均匀采样视频帧
2. 将字幕文本与视频帧一起发送给 VLM
3. 使用滚动压缩摘要提供跨段落上下文
4. 生成 Markdown 格式的知识要点

### Python API 调用

```python
from scripts.purify_video import purify_video

# 一键提纯
note_path = purify_video(
    video_path="video.mp4",
    srt_path="transcript.srt",  # 可选，None 则自动转录
    output_dir="./notes",
    max_frames=8,
)

print(f"笔记已生成: {note_path}")
```

或分步调用：

```python
from scripts.transcribe import Transcriber
from scripts.segment_video import SrtTopicSegmenter, parse_srt
from scripts.merge_segments import SrtMerger, build_note

# 1. 转录
transcriber = Transcriber(model_size='medium')
result = transcriber.transcribe('video.mp4', output_srt='transcript.srt')

# 2. 分段
segments = parse_srt('transcript.srt')
topic_groups = SrtTopicSegmenter().segment(segments)

# 3. 汇总
chunks = SrtMerger().merge('video.mp4', topic_groups, './notes', max_frames=8)
note_content = build_note(title="视频标题", chunks=chunks)
```

## 笔记格式

生成的 `note.md` 使用 YAML frontmatter：

```markdown
---
title: 视频标题
duration: 1200
segments: 5
frames_dir: frames
---

# 视频标题

## 段落 1

**时间**: 00:00:00 - 00:02:30

### 笔记

[LLM 生成的知识要点 Markdown]

### 关键帧

![帧1](frames/segment_1_001.jpg)
![帧2](frames/segment_1_002.jpg)

---

## 段落 2
...
```

## 设计说明

- **转录**: 使用 faster-whisper，支持本地运行，可选 GPU 加速
- **分段**: 使用文本 LLM（便宜快速），按语义主题切分
- **汇总**: 使用 VLM（支持视觉），结合字幕+视频帧生成笔记
- **滚动摘要**: 段落间传递压缩摘要，保持上下文连贯性
- **帧采样**: 每段落均匀采样，避免信息过载

## 限制说明

- 转录质量取决于 faster-whisper 模型大小和音频清晰度
- 分段质量取决于 LLM 对内容的理解
- 汇总质量取决于 VLM 的视觉理解能力
- 长视频处理时间较长，建议分段处理或使用更快的模型
