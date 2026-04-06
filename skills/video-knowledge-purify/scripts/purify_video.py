#!/usr/bin/env python3
"""
视频知识提纯 - 完整流程
转录 -> 分段 -> 汇总 -> 生成 Markdown 笔记

用法:
    python purify_video.py <video_path> [srt_path] <output_dir> [options]

示例:
    # 已有字幕
    python purify_video.py video.mp4 transcript.srt ./notes

    # 无字幕（自动转录）
    python purify_video.py video.mp4 ./notes

    # 更多选项
    python purify_video.py video.mp4 ./notes --max-frames 12 --whisper-model large-v3
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional

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

# 导入同目录下的模块
from transcribe import Transcriber
from segment_video import SrtTopicSegmenter, parse_srt as parse_srt_file, save_segments_json
from merge_segments import SrtMerger, build_note


def purify_video(
    video_path: str,
    srt_path: Optional[str],
    output_dir: str,
    max_frames: int = 8,
    whisper_model: str = 'medium',
    skip_existing: bool = True,
) -> str:
    """
    视频提纯完整流程

    :param video_path: 视频文件路径
    :param srt_path: SRT字幕路径，None则自动转录
    :param output_dir: 输出目录
    :param max_frames: 每段落最大采样帧数
    :param whisper_model: Whisper模型大小
    :param skip_existing: 如果输出文件已存在则跳过对应步骤（默认 True）
    :return: 生成的笔记文件路径
    """

    video_name = os.path.splitext(os.path.basename(video_path))[0]
    os.makedirs(output_dir, exist_ok=True)

    # 检查最终输出是否已存在
    note_path = os.path.join(output_dir, "note.md")
    if skip_existing and os.path.exists(note_path):
        print(f"笔记文件已存在，跳过全部处理: {note_path}")
        return note_path

    # 步骤1: 转录（如果没有提供SRT）
    if not srt_path:
        srt_path = os.path.join(output_dir, f"{video_name}.srt")

        if skip_existing and os.path.exists(srt_path):
            print(f"字幕文件已存在，跳过转录: {srt_path}")
        else:
            print("=" * 60)
            print("步骤 1/3: 音频转录")
            print("=" * 60)

            txt_path = os.path.join(output_dir, f"{video_name}.txt")

            transcriber = Transcriber(model_size=whisper_model)
            transcriber.transcribe(
                input_path=video_path,
                language='zh',
                output_txt=txt_path,
                output_srt=srt_path,
            )
    else:
        print(f"使用现有字幕: {srt_path}")

    # 步骤2: 分段
    print("\n" + "=" * 60)
    print("步骤 2/3: 内容分段")
    print("=" * 60)

    segments = parse_srt_file(srt_path)
    print(f"解析到 {len(segments)} 条字幕")

    segments_json_path = os.path.join(output_dir, f"{video_name}.json")

    # 提取视频标题（使用完整路径，让LLM能从目录结构获取主题信息）
    video_title = os.path.abspath(video_path)

    if skip_existing and os.path.exists(segments_json_path):
        print(f"分段结果已存在，跳过 LLM 分段: {segments_json_path}")
        # 从 JSON 加载分组信息
        import json
        with open(segments_json_path, 'r', encoding='utf-8') as f:
            groups_data = json.load(f)
        topic_groups = []
        for g in groups_data:
            start_idx = g['start_index']
            end_idx = g['end_index']
            group = [s for s in segments if start_idx <= s.index <= end_idx]
            if group:
                topic_groups.append(group)
        print(f"已加载 {len(topic_groups)} 个段落")
    else:
        segmenter = SrtTopicSegmenter()
        topic_groups = segmenter.segment(segments, video_title=video_title)
        save_segments_json(topic_groups, segments_json_path)

    # 步骤3: 汇总
    print("\n" + "=" * 60)
    print("步骤 3/3: 内容汇总")
    print("=" * 60)

    merger = SrtMerger()
    chunks = merger.merge(video_path, topic_groups, output_dir, max_frames, video_title=video_title)

    # 生成笔记
    title = os.path.splitext(os.path.basename(video_path))[0]
    note_content = build_note(title=title, chunks=chunks)

    with open(note_path, "w", encoding="utf-8") as f:
        f.write(note_content)

    print(f"\n笔记已生成: {note_path}")
    return note_path


def main():
    parser = argparse.ArgumentParser(description='视频知识提纯 - 完整流程')
    parser.add_argument('video_path', help='视频文件路径')
    parser.add_argument('arg2', nargs='?', help='SRT字幕路径 或 输出目录（默认：视频所在目录）')
    parser.add_argument('arg3', nargs='?', help='输出目录（如果arg2是SRT）')
    parser.add_argument('--max-frames', '-f', type=int, default=8, help='每段落最大采样帧数 (默认: 8)')
    parser.add_argument('--whisper-model', '-m', default='medium',
                        choices=['tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3'],
                        help='Whisper模型大小 (默认: medium)')
    parser.add_argument('--no-skip', action='store_true', help='禁用跳过已存在文件，强制重新处理')

    args = parser.parse_args()

    # 解析参数
    video_path = args.video_path

    # 设置默认输出目录（视频所在目录）
    default_output_dir = os.path.dirname(video_path) or '.'

    # 判断 arg2 是 SRT 文件还是输出目录
    if args.arg2 and args.arg2.endswith('.srt') and os.path.exists(args.arg2):
        srt_path = args.arg2
        output_dir = args.arg3 or default_output_dir
    elif args.arg2:
        # arg2 存在但不是 SRT，则视为输出目录
        srt_path = None
        output_dir = args.arg2
    else:
        # arg2 不存在，使用默认输出目录
        srt_path = None
        output_dir = default_output_dir

    # 执行提纯
    note_path = purify_video(
        video_path=video_path,
        srt_path=srt_path,
        output_dir=output_dir,
        max_frames=args.max_frames,
        whisper_model=args.whisper_model,
        skip_existing=not args.no_skip,
    )

    print(f"\n完成！笔记保存在: {note_path}")


if __name__ == '__main__':
    main()
