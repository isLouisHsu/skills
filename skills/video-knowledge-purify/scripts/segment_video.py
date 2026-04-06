#!/usr/bin/env python3
"""
视频字幕内容分段
- 使用 LLM 按主题对 SRT 字幕进行语义分段

用法:
    python segment_video.py <srt_path> <output_json>

示例:
    python segment_video.py transcript.srt segments.json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

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
    from openai import OpenAI
except ImportError:
    print("错误: 需要安装 openai: pip install openai")
    sys.exit(1)


@dataclass
class SrtSegment:
    """SRT字幕片段"""
    index: int
    start: float   # seconds
    end: float     # seconds
    text: str


_SYSTEM_PROMPT = """\
你是视频内容分析助手。给定一段视频的完整字幕文本，请按内容主题将其划分为若干个段落。

分段原则：
1. 每个段落应围绕一个相对独立的主题、知识点或操作步骤展开
2. 当视频中有明确的序号标记（如"第一/第二/第三"、"首先/其次/最后"、"步骤1/步骤2"等）时，应按这些标记切分
3. 同一主题下的多个并列要点应分为不同段落
4. 段落数量由内容自然决定，不要强行合并，也不要过度切割
5. 过渡的句子不要单独成段落，可以和上一段或下一段合并

严格返回 JSON，格式为字幕序号的闭区间列表，不要有任何多余文字：
{"sections": [[1, 15], [16, 30], [31, 49]]}\
"""


def parse_srt(path: str) -> List[SrtSegment]:
    """解析 SRT 文件为 SrtSegment 列表"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"SRT文件不存在: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    segments = []
    blocks = re.split(r'\n\s*\n', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        # 解析序号
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue

        # 解析时间戳行
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

        # 合并剩余行为文本
        text = ' '.join(lines[2:]).strip()

        segments.append(SrtSegment(index=index, start=start, end=end, text=text))

    return sorted(segments, key=lambda s: s.index)


class SrtTopicSegmenter:
    """SRT主题分段器"""

    def __init__(self):
        missing = [k for k in ("SRT_SEGMENTER_BASE_URL", "SRT_SEGMENTER_API_KEY", "SRT_SEGMENTER_MODEL") if not os.getenv(k)]
        if missing:
            raise EnvironmentError(f"缺少必要的环境变量：{', '.join(missing)}")

        self.client = OpenAI(
            base_url=os.getenv("SRT_SEGMENTER_BASE_URL"),
            api_key=os.getenv("SRT_SEGMENTER_API_KEY"),
        )
        self.model = os.getenv("SRT_SEGMENTER_MODEL")

    def segment(self, segments: List[SrtSegment], video_title: str = "") -> List[List[SrtSegment]]:
        """调用 LLM 按内容主题对 SRT 片段分组，返回分组后的段落列表。

        :param segments: SRT 字幕片段列表
        :param video_title: 视频标题（主题），用于帮助 LLM 理解整体语境
        """
        if not segments:
            return []

        # 构建用户输入内容，包含视频标题
        content_parts = []
        if video_title:
            content_parts.append(f"【视频主题】{video_title}\n")
        content_parts.append("【字幕内容】")
        content_parts.extend(
            f"[{s.index}] [{_fmt_time(s.start)}] {s.text.strip()}"
            for s in segments
        )
        srt_text = '\n'.join(content_parts)

        print(f"[srt_segmenter] 发送 {len(segments)} 条字幕给 LLM 进行语义分段...")
        if video_title:
            print(f"[srt_segmenter] 视频主题: {video_title}")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": srt_text},
            ],
            # temperature=0.2,
        )
        raw = response.choices[0].message.content

        print(f"System Prompt: \n{_SYSTEM_PROMPT}")
        print(f"Response: \n{raw}")

        groups = self._parse_sections(raw, segments)
        print(f"[srt_segmenter] 分段完成：{len(groups)} 个大段落")
        return groups

    def _parse_sections(
        self,
        text: str,
        segments: List[SrtSegment],
    ) -> List[List[SrtSegment]]:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                raw_sections = data.get('sections', [])
                result = []
                for pair in raw_sections:
                    start_idx, end_idx = int(pair[0]), int(pair[1])
                    group = [s for s in segments if start_idx <= s.index <= end_idx]
                    if group:
                        result.append(group)
                if result:
                    return result
            except (json.JSONDecodeError, ValueError, TypeError, IndexError):
                pass

        print("[srt_segmenter] 解析分段结果失败，降级为单段处理")
        return [segments]


def save_segments_json(groups: List[List[SrtSegment]], output_path: str) -> None:
    """将分段结果保存为 JSON"""
    data = []
    for i, group in enumerate(groups, 1):
        data.append({
            "segment_id": i,
            "start_index": group[0].index,
            "end_index": group[-1].index,
            "start_time": group[0].start,
            "end_time": group[-1].end,
            "text_count": len(group),
            # "preview": group[0].text[:100] + "..." if len(group[0].text) > 100 else group[0].text,
            "preview": group[0].text,
        })

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"分段结果已保存: {output_path}")


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main():
    parser = argparse.ArgumentParser(description='视频字幕内容分段')
    parser.add_argument('srt_path', help='输入SRT字幕文件路径')
    parser.add_argument('output_json', nargs='?', help='输出JSON文件路径（默认：与SRT文件同名 .json）')
    parser.add_argument('--skip-existing', '-k', action='store_true', help='如果输出文件已存在则跳过')

    args = parser.parse_args()

    # 设置默认输出路径（与SRT文件同级目录）
    if args.output_json:
        output_json = args.output_json
    else:
        srt_dir = os.path.dirname(args.srt_path) or '.'
        srt_name = os.path.splitext(os.path.basename(args.srt_path))[0]
        output_json = os.path.join(srt_dir, f"{srt_name}.json")

    # 检查输出文件是否已存在
    if args.skip_existing and os.path.exists(output_json):
        print(f"分段结果已存在，跳过处理: {output_json}")
        # 加载并显示分段信息
        with open(output_json, 'r', encoding='utf-8') as f:
            groups_data = json.load(f)
        print(f"\n分段结果 ({len(groups_data)} 个段落):")
        for g in groups_data:
            print(f"  段落 {g['segment_id']}: 字幕 {g['start_index']}-{g['end_index']} ({g['text_count']}条) "
                  f"[{_fmt_time(g['start_time'])} - {_fmt_time(g['end_time'])}]")
        return

    # 解析SRT
    segments = parse_srt(args.srt_path)
    print(f"解析到 {len(segments)} 条字幕")

    # 分段
    segmenter = SrtTopicSegmenter()
    video_title = os.path.splitext(os.path.basename(args.srt_path))[0]
    groups = segmenter.segment(segments, video_title=video_title)

    # 保存结果
    save_segments_json(groups, output_json)

    print(f"\n分段结果:")
    for i, group in enumerate(groups, 1):
        print(f"  段落 {i}: 字幕 {group[0].index}-{group[-1].index} ({len(group)}条) "
              f"[{_fmt_time(group[0].start)} - {_fmt_time(group[-1].end)}]")


if __name__ == '__main__':
    main()
