#!/usr/bin/env python3
"""
视频分段内容汇总
- 提取视频帧
- 使用 VLM 结合字幕和视频帧生成 Markdown 笔记

用法:
    python merge_segments.py <video_path> <segments_json> <output_dir> [options]

示例:
    python merge_segments.py video.mp4 segments.json ./notes --max-frames 4
"""

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# 加载 .env 文件（从脚本目录向上查找）
try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent.resolve()
    skill_dir = script_dir.parent
    for env_path in [script_dir / '.env', skill_dir / '.env', Path.cwd() / '.env']:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass  # python-dotenv 未安装时跳过

try:
    import av
except ImportError:
    print("错误: 需要安装 av 库: pip install av")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("错误: 需要安装 openai: pip install openai")
    sys.exit(1)


@dataclass
class SrtSegment:
    """SRT字幕片段"""
    index: int
    start: float
    end: float
    text: str


@dataclass
class KnowledgeChunk:
    """知识片段"""
    note: str                          # VLM 整理的知识要点
    frame_paths: List[str]             # 对应帧图片路径
    start_time: float                  # 段落起始时间（秒）
    end_time: float                    # 段落结束时间（秒）
    summary: str = ''                  # 压缩摘要


_SYSTEM_PROMPT = """\
你是知识提取助手。任务是：从视频内容中提取有价值的知识点，整理成结构化笔记。

## 输入说明
1. 【已整理摘要】：前文内容的压缩摘要（提供上下文，可能为空）
2. 【当前段落】：当前主题段落的字幕文本（含时间戳）和关键帧图片

## 输出要求
严格返回 JSON 格式：
{"note": "...", "summary": "..."}

### note 字段要求（重点）
提取并整理段落中的**核心知识点**，格式要求：
- 使用 Markdown 格式（段落标题加粗，而不是用'#'、'##'、'###'、'####'）
- 聚焦：概念定义、方法论、 actionable insights、对比结论、数据观点
- **禁止**：描述画面场景、人物动作、视频形式、讲师外貌、"视频中提到"
- **禁止**：复述"讲师说/提到/指出"，直接陈述知识点本身

**正确示例**：
```markdown
## 小红书 vs 抖音的核心差异

| 维度 | 小红书 | 抖音 |
|------|--------|------|
| 流量逻辑 | 内容分发为主 | 账号关注驱动 |
| 内容属性 | 分享、实用、干货、教学 | 娱乐、热点、消遣 |
| 价值产生 | 单篇内容可独立获客 | 依赖账号整体粉丝量 |

### 关键结论
- 小红书适合**精准获客**，单篇优质内容即可产生价值
- 做小红书应聚焦**内容质量**而非账号粉丝数
```

**错误示例**：
```
视频中，一位戴眼镜的男性讲师正在讲解小红书与抖音的区别。画面展示了思维导图...
```

### summary 字段要求
更新整个视频的滚动摘要（300字以内），用于给后续段落提供上下文。保留关键主题、核心论点、尚未解决的问题。

## 重要提醒
- 你的输出是**知识笔记**，不是**视频描述**
- 读者通过你的笔记获取知识，不需要知道"视频里有什么画面"
- 直接输出知识点本身，去掉"视频中/讲师说/我们可以看到"等引导词\
"""


def parse_srt(path: str) -> List[SrtSegment]:
    """解析 SRT 文件"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    segments = []
    blocks = re.split(r'\n\s*\n', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        try:
            index = int(lines[0].strip())
        except ValueError:
            continue

        time_line = lines[1].strip()
        match = re.match(
            r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
            time_line
        )
        if not match:
            continue

        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, match.groups())
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000

        text = ' '.join(lines[2:]).strip()
        segments.append(SrtSegment(index=index, start=start, end=end, text=text))

    return sorted(segments, key=lambda s: s.index)


def extract_frames(video_path: str, segments: List[SrtSegment], output_dir: str) -> List[Optional[str]]:
    """从视频中提取帧，每个片段提取一帧（中点时间）"""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    os.makedirs(output_dir, exist_ok=True)
    paths = []

    with av.open(video_path) as container:
        stream = container.streams.video[0]
        fps = stream.average_rate
        time_base = stream.time_base

        for seg in segments:
            mid_time = (seg.start + seg.end) / 2
            frame_path = os.path.join(output_dir, f"frame_{seg.index:04d}_{mid_time:.3f}.jpg")

            if os.path.exists(frame_path):
                paths.append(frame_path)
                continue

            try:
                # 定位到目标时间附近
                target_pts = int(mid_time / time_base)
                container.seek(target_pts, stream=stream)

                # 解码获取帧
                for frame in container.decode(stream):
                    frame_pts = float(frame.pts * time_base)
                    if frame_pts >= mid_time:
                        frame.to_image().save(frame_path, quality=85)
                        paths.append(frame_path)
                        break
                else:
                    paths.append(None)
            except Exception as e:
                print(f"  提取帧失败 [{seg.index}]: {e}")
                paths.append(None)

    return paths


def _encode_image(path: str) -> Optional[str]:
    """将图片编码为 base64"""
    try:
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except OSError:
        return None


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class SrtMerger:
    """SRT内容汇总器"""

    def __init__(self):
        missing = [k for k in ("SRT_MERGER_BASE_URL", "SRT_MERGER_API_KEY", "SRT_MERGER_MODEL") if not os.getenv(k)]
        if missing:
            raise EnvironmentError(f"缺少必要的环境变量：{', '.join(missing)}")

        self.client = OpenAI(
            base_url=os.getenv("SRT_MERGER_BASE_URL"),
            api_key=os.getenv("SRT_MERGER_API_KEY"),
        )
        self.model = os.getenv("SRT_MERGER_MODEL")

    def merge(
        self,
        video_path: str,
        topic_groups: List[List[SrtSegment]],
        output_dir: str,
        max_frames: int = 4,
        video_title: str = "",
    ) -> List[KnowledgeChunk]:
        """完整流水线：逐语义段落提取帧、合并字幕、调用 VLM，返回 KnowledgeChunk 列表。

        :param video_path: 视频文件路径
        :param topic_groups: 按主题分组的字幕列表
        :param output_dir: 输出目录
        :param max_frames: 每段落最大采样帧数
        :param video_title: 视频标题（主题），用于帮助 VLM 理解整体语境
        """
        chunks: List[KnowledgeChunk] = []
        compressed_summary = ''
        frames_dir = os.path.join(output_dir, 'frames')
        total = len(topic_groups)

        for idx, group in enumerate(topic_groups, 1):
            print(f"处理段落 {idx}/{total}（字幕 {group[0].index}–{group[-1].index}，共 {len(group)} 条）...")

            raw_frames = extract_frames(video_path, group, frames_dir)
            merged_segs, sampled_frames = _build_merged_pairs(group, raw_frames, max_frames)

            note, compressed_summary = self.process_group(merged_segs, sampled_frames, compressed_summary, video_title)

            chunks.append(KnowledgeChunk(
                note=note,
                frame_paths=sampled_frames,
                start_time=group[0].start,
                end_time=group[-1].end,
                summary=compressed_summary,
            ))

        return chunks

    def process_group(
        self,
        segments: List[SrtSegment],
        frame_paths: List[str],
        compressed_summary: str = '',
        video_title: str = '',
    ) -> Tuple[str, str]:
        """处理一个大段落（语义主题），返回 (note, updated_summary)

        :param segments: 字幕片段列表
        :param frame_paths: 帧图片路径列表
        :param compressed_summary: 前文内容的压缩摘要
        :param video_title: 视频标题（主题），用于帮助 VLM 理解整体语境
        """
        content = self._build_content(segments, frame_paths, compressed_summary, video_title)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            # temperature=0.3,
        )

        raw = response.choices[0].message.content

        print(f"System Prompt: \n{_SYSTEM_PROMPT}")
        print(f"Response: \n{raw}")

        return _parse_response(raw, fallback_note=_segments_to_text(segments))

    def _build_content(
        self,
        segments: List[SrtSegment],
        frame_paths: List[str],
        compressed_summary: str,
        video_title: str = '',
    ) -> list:
        parts = []

        if video_title:
            parts.append({
                "type": "text",
                "text": f"【视频主题】{video_title}\n",
            })

        if compressed_summary:
            parts.append({
                "type": "text",
                "text": f"【已整理摘要】\n{compressed_summary}\n",
            })

        parts.append({"type": "text", "text": "【当前段落】"})

        for seg, path in zip(segments, frame_paths):
            parts.append({
                "type": "text",
                "text": f"[{_fmt_time(seg.start)}–{_fmt_time(seg.end)}] {seg.text.strip()}",
            })
            b64 = _encode_image(path)
            if b64:
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                })

        return parts


def _build_merged_pairs(
    group: List[SrtSegment],
    raw_frames: List[Optional[str]],
    max_frames: int,
) -> Tuple[List[SrtSegment], List[str]]:
    """按采样帧将 group 切分并合并，返回 (merged_segs, frame_paths)，两者等长一一对应。"""
    valid = [(i, fp) for i, fp in enumerate(raw_frames) if fp is not None]
    if len(valid) > max_frames:
        if max_frames == 1:
            valid = [valid[len(valid) // 2]]
        else:
            indices = [round(i * (len(valid) - 1) / (max_frames - 1)) for i in range(max_frames)]
            valid = [valid[i] for i in indices]

    sampled_indices = [i for i, _ in valid]
    cut_points = [0] + [(a + b) // 2 + 1 for a, b in zip(sampled_indices, sampled_indices[1:])] + [len(group)]
    merged_segs = [_merge_segment(group[s:e]) for s, e in zip(cut_points, cut_points[1:])]
    return merged_segs, [fp for _, fp in valid]


def _merge_segment(segs: List[SrtSegment]) -> SrtSegment:
    return SrtSegment(
        index=segs[0].index,
        start=segs[0].start,
        end=segs[-1].end,
        text=' '.join(s.text.strip() for s in segs),
    )


def _parse_response(text: str, fallback_note: str) -> Tuple[str, str]:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            note = data.get('note', '').strip()
            summary = data.get('summary', '').strip()
            if note:
                return note, summary
        except json.JSONDecodeError:
            pass
    return text.strip() or fallback_note, ''


def _segments_to_text(segments: List[SrtSegment]) -> str:
    return '\n'.join(f"[{_fmt_time(s.start)}] {s.text.strip()}" for s in segments)


def build_note(title: str, chunks: List[KnowledgeChunk]) -> str:
    """组装 Markdown 笔记"""
    lines = [
        "---",
        f"title: {title}",
        f"segments: {len(chunks)}",
        "---",
        "",
        f"# {title}",
        "",
    ]

    for i, chunk in enumerate(chunks, 1):
        lines.append(f"## 段落 {i}")
        lines.append("")
        lines.append(f"**时间**: {_fmt_time(chunk.start_time)} - {_fmt_time(chunk.end_time)}")
        lines.append("")
        lines.append("### 笔记")
        lines.append("")
        lines.append(chunk.note)
        lines.append("")

        if chunk.frame_paths:
            lines.append("### 关键帧")
            lines.append("")
            for fp in chunk.frame_paths:
                rel_path = os.path.join("frames", os.path.basename(fp))
                lines.append(f"![{os.path.basename(fp)}]({rel_path})")
            lines.append("")

        lines.append("---")
        lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='视频分段内容汇总')
    parser.add_argument('video_path', help='视频文件路径')
    parser.add_argument('segments_json', help='分段JSON文件路径（或SRT文件路径）')
    parser.add_argument('output_dir', nargs='?', help='输出目录（默认：视频所在目录）')
    parser.add_argument('--max-frames', '-f', type=int, default=4, help='每段落最大采样帧数 (默认: 4)')
    parser.add_argument('--srt-path', '-s', help='SRT文件路径（如果segments_json不是SRT则必须提供）')
    parser.add_argument('--skip-existing', '-k', action='store_true', help='如果笔记文件已存在则跳过')

    args = parser.parse_args()

    # 设置默认输出目录（视频文件所在目录）
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = os.path.dirname(args.video_path) or '.'

    # 检查笔记文件是否已存在
    note_path = os.path.join(output_dir, "note.md")
    if args.skip_existing and os.path.exists(note_path):
        print(f"笔记文件已存在，跳过处理: {note_path}")
        return

    # 判断输入是SRT还是JSON
    srt_path = args.srt_path or args.segments_json
    if not srt_path.endswith('.srt'):
        print("错误: 需要提供SRT文件路径")
        sys.exit(1)

    # 解析SRT
    segments = parse_srt(srt_path)

    # 从JSON加载分组信息或按简单规则分组
    if args.segments_json.endswith('.json') and os.path.exists(args.segments_json):
        with open(args.segments_json, 'r') as f:
            groups_data = json.load(f)

        topic_groups = []
        for g in groups_data:
            start_idx = g['start_index']
            end_idx = g['end_index']
            group = [s for s in segments if start_idx <= s.index <= end_idx]
            if group:
                topic_groups.append(group)
    else:
        # 默认：所有字幕作为一个组
        topic_groups = [segments]

    print(f"共 {len(topic_groups)} 个段落待处理")

    # 汇总
    merger = SrtMerger()
    video_title = os.path.splitext(os.path.basename(args.video_path))[0]
    chunks = merger.merge(args.video_path, topic_groups, output_dir, args.max_frames, video_title=video_title)

    # 生成笔记
    title = os.path.splitext(os.path.basename(args.video_path))[0]
    note_content = build_note(title=title, chunks=chunks)

    os.makedirs(output_dir, exist_ok=True)
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(note_content)

    print(f"\n笔记已生成: {note_path}")


if __name__ == '__main__':
    main()
