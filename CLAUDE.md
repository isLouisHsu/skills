# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal Claude Code skills repository containing utility Python scripts for media processing and project management.

### Skills Structure

Each skill is a self-contained directory under `skills/` with its own documentation and scripts:

| Skill | Purpose | Location |
|-------|---------|----------|
| `project-interview` | Interactive project interview for generating structured documentation | `skills/project-interview/` |
| `project-docs-manager` | Document-centric AI task flow management | `skills/project-docs-manager/` |
| `bilibili-downloader` | Download Bilibili videos (single or album) | `skills/bilibili-downloader/` |
| `video-knowledge-purify` | Convert videos to structured Markdown notes | `skills/video-knowledge-purify/` |

Each skill follows this structure:
```
skills/<skill-name>/
├── SKILL.md          # Skill documentation with usage instructions
├── scripts/          # Python implementation
└── references/       # Reference documentation (for complex skills)
```

## Dependencies

Skills have their own dependency requirements. Install as needed:

```bash
# bilibili-downloader
pip install requests tenacity av openpyxl

# video-knowledge-purify
pip install faster-whisper av openai python-dotenv

# Optional GPU acceleration for video-knowledge-purify
pip install torch
```

## Environment Configuration

The `video-knowledge-purify` skill requires API keys for LLM/VLM services. Configure via `.env` file:

```bash
cp skills/video-knowledge-purify/scripts/.env.example skills/video-knowledge-purify/scripts/.env
# Edit .env with your API keys
```

## Usage Patterns

Each skill is invoked directly via Python:

```bash
# bilibili-downloader - single video
python skills/bilibili-downloader/scripts/download_video.py single BV1hKywBAEkq ./downloads

# bilibili-downloader - album
python skills/bilibili-downloader/scripts/download_video.py album <MID> <SEASON_ID> ./downloads

# video-knowledge-purify - full pipeline
python skills/video-knowledge-purify/scripts/purify_video.py video.mp4 ./notes

# video-knowledge-purify - individual steps
python skills/video-knowledge-purify/scripts/transcribe.py video.mp4
python skills/video-knowledge-purify/scripts/segment_video.py transcript.srt
python skills/video-knowledge-purify/scripts/merge_segments.py video.mp4 segments.json ./notes
```

## Code Style

- Python 3.10+ with type hints
- Scripts use `argparse` for CLI interfaces
- Data classes (`@dataclass`) for structured data
- Tenacity for retry logic in network operations
- PyAV (`av`) for video/audio processing
