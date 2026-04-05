#!/usr/bin/env python3
"""
音视频转文字
- 使用 faster-whisper 进行语音识别
- 使用 av 库从视频中提取音频流
- 支持输出纯文本 (.txt) 和带时间戳字幕 (.srt)

用法:
    python transcribe.py <input_path> [options]

示例:
    python transcribe.py video.mp4 --output-txt out.txt --output-srt out.srt --model medium
"""

import argparse
import os
import re
import sys
import wave
import tempfile
from dataclasses import dataclass, field
from typing import Optional, List

try:
    import av
except ImportError:
    print("错误: 需要安装 av 库: pip install av")
    sys.exit(1)

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("错误: 需要安装 faster-whisper: pip install faster-whisper")
    sys.exit(1)


@dataclass
class Segment:
    """转录片段（含时间戳）"""
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    """转录结果"""
    segments: List[Segment] = field(default_factory=list)
    language: str = ''
    language_probability: float = 0.0

    @property
    def text(self) -> str:
        """拼接所有片段为纯文本"""
        return ''.join(seg.text for seg in self.segments)

    def to_srt(self) -> str:
        """生成 SRT 格式字幕"""
        lines = []
        for i, seg in enumerate(self.segments, 1):
            lines.append(str(i))
            lines.append(f"{_fmt_srt_time(seg.start)} --> {_fmt_srt_time(seg.end)}")
            lines.append(seg.text.strip())
            lines.append('')
        return '\n'.join(lines)


def _fmt_srt_time(seconds: float) -> str:
    """秒数转 SRT 时间格式 hh:mm:ss,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round(seconds % 1, 3) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class Transcriber:
    """音视频转文字"""

    def __init__(
        self,
        model_size: str = 'base',
        device: str = 'auto',
        compute_type: str = 'auto',
    ):
        """
        初始化转录器
        :param model_size: 模型大小，可选 tiny/base/small/medium/large-v2/large-v3
        :param device: 运行设备，auto/cpu/cuda
        :param compute_type: 计算类型，auto/int8/float16/float32
        """
        if device == 'auto':
            try:
                import torch
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
            except ImportError:
                device = 'cpu'

        if compute_type == 'auto':
            compute_type = 'int8' if device == 'cpu' else 'float16'

        print(f"加载 Whisper 模型: {model_size}，设备: {device}，精度: {compute_type}")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def _load_from_srt(self, srt_path: str) -> TranscriptResult:
        """从现有 SRT 文件加载转录结果"""
        from typing import List
        segments: List[Segment] = []

        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        blocks = content.strip().split('\n\n')
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
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
            segments.append(Segment(start=start, end=end, text=text))

        result = TranscriptResult(segments=segments, language='unknown', language_probability=1.0)
        print(f"从现有文件加载，共 {len(segments)} 个片段")
        return result

    def _extract_audio(self, input_path: str, tmp_wav: str) -> None:
        """
        用 av 从视频/音频文件提取音频，重采样为 16kHz 单声道 16-bit WAV
        :param input_path: 输入文件路径
        :param tmp_wav: 临时 WAV 输出路径
        """
        chunks: List[bytes] = []
        resampler = av.AudioResampler(format='s16p', layout='mono', rate=16000)

        with av.open(input_path) as src:
            audio_streams = src.streams.audio
            if not audio_streams:
                raise ValueError(f"文件中无音频流: {input_path}")

            for frame in src.decode(audio_streams[0]):
                for out_frame in resampler.resample(frame):
                    chunks.append(bytes(out_frame.planes[0]))

        # 冲洗重采样器中残留的帧
        for out_frame in resampler.resample(None):
            chunks.append(bytes(out_frame.planes[0]))

        raw = b''.join(chunks)
        with wave.open(tmp_wav, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)   # s16 = 2 bytes
            wf.setframerate(16000)
            wf.writeframes(raw)

    def transcribe(
        self,
        input_path: str,
        language: Optional[str] = None,
        output_txt: Optional[str] = None,
        output_srt: Optional[str] = None,
        skip_existing: bool = True,
    ) -> TranscriptResult:
        """
        转录音视频文件
        :param input_path: 输入文件路径（视频或音频）
        :param language: 语言代码，如 'zh'/'en'，None 则自动检测
        :param output_txt: 纯文本输出路径，None 则不保存
        :param output_srt: SRT 字幕输出路径，None 则不保存
        :param skip_existing: 如果输出文件已存在则跳过转录（默认 True）
        :return: TranscriptResult
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"文件不存在: {input_path}")

        # 检查输出文件是否已存在
        if skip_existing and output_srt and os.path.exists(output_srt):
            print(f"字幕文件已存在，跳过转录: {output_srt}")
            # 从现有 SRT 文件加载结果
            return self._load_from_srt(output_srt)

        print(f"提取音频: {os.path.basename(input_path)}")
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_wav = tmp.name

        try:
            self._extract_audio(input_path, tmp_wav)

            print("开始转录...")
            segments_iter, info = self.model.transcribe(
                tmp_wav,
                language=language,
                beam_size=5,
                vad_filter=True,
            )

            result = TranscriptResult(
                language=info.language,
                language_probability=info.language_probability,
            )

            for seg in segments_iter:
                result.segments.append(Segment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                ))
                print(f"  [{_fmt_srt_time(seg.start)} --> {_fmt_srt_time(seg.end)}] {seg.text.strip()}")

        finally:
            if os.path.exists(tmp_wav):
                os.remove(tmp_wav)

        print(f"\n转录完成，语言: {result.language} ({result.language_probability:.0%})")
        print(f"共 {len(result.segments)} 个片段")

        if output_txt:
            os.makedirs(os.path.dirname(output_txt) or '.', exist_ok=True)
            with open(output_txt, 'w', encoding='utf-8') as f:
                f.write(result.text)
            print(f"文本已保存: {output_txt}")

        if output_srt:
            os.makedirs(os.path.dirname(output_srt) or '.', exist_ok=True)
            with open(output_srt, 'w', encoding='utf-8') as f:
                f.write(result.to_srt())
            print(f"字幕已保存: {output_srt}")

        return result


def main():
    parser = argparse.ArgumentParser(description='音视频转文字')
    parser.add_argument('input_path', help='输入音视频文件路径')
    parser.add_argument('--output-txt', '-t', help='输出纯文本文件路径（默认：与输入文件同名 .txt）')
    parser.add_argument('--output-srt', '-s', help='输出SRT字幕文件路径（默认：与输入文件同名 .srt）')
    parser.add_argument('--model', '-m', default='medium',
                        choices=['tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3'],
                        help='Whisper模型大小 (默认: medium)')
    parser.add_argument('--skip-existing', '-k', action='store_true',
                        help='如果输出文件已存在则跳过转录')
    parser.add_argument('--device', '-d', default='auto',
                        choices=['auto', 'cpu', 'cuda'],
                        help='运行设备 (默认: auto)')
    parser.add_argument('--language', '-l', help='语言代码，如 zh/en，不指定则自动检测')

    args = parser.parse_args()

    # 设置默认输出路径（与输入文件同级目录）
    input_dir = os.path.dirname(args.input_path) or '.'
    input_name = os.path.splitext(os.path.basename(args.input_path))[0]
    output_txt = args.output_txt or os.path.join(input_dir, f"{input_name}.txt")
    output_srt = args.output_srt or os.path.join(input_dir, f"{input_name}.srt")

    transcriber = Transcriber(model_size=args.model, device=args.device)
    transcriber.transcribe(
        input_path=args.input_path,
        language=args.language,
        output_txt=output_txt,
        output_srt=output_srt,
        skip_existing=args.skip_existing,
    )


if __name__ == '__main__':
    main()
