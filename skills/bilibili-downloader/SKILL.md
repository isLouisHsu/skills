---
name: bilibili-downloader
description: 下载B站视频（单个视频或整个专辑/合集）。当用户需要下载B站视频、批量下载UP主的专辑视频、获取视频列表时触发此skill。支持通过MID和SEASON_ID下载专辑，或通过BV号下载单个视频。
---

# B站视频下载器

提供B站视频下载功能，支持单个视频和专辑/合集批量下载。

## 依赖安装

使用前确保安装依赖：

```bash
pip install requests tenacity av openpyxl
```

## 使用方式

### 1. 下载单个视频

```bash
python scripts/download_video.py single <BV号> [输出目录]
```

**示例：**
```bash
python scripts/download_video.py single BV1hKywBAEkq ./downloads
```

输出：
- `downloads/<bvid>/<bvid>.mp4` - 视频文件
- `downloads/<bvid>/<bvid>.jpg` - 封面图片
- `downloads/<bvid>/video_<bvid>.xlsx` - 视频信息Excel

### 2. 下载整个专辑/合集

```bash
python scripts/download_video.py album <MID> <SEASON_ID> [输出目录]
```

**参数说明：**
- `MID`: UP主的用户ID（打开UP主空间，URL中的数字）
- `SEASON_ID`: 专辑ID（打开专辑页面，URL中的 `sid=` 后面的数字）

**示例：**
```bash
python scripts/download_video.py album 3546856309131659 6823908 ./downloads
```

输出：
- `downloads/album/<season_id>/covers/` - 封面图片目录
- `downloads/album/<season_id>/<专辑名称>.xlsx` - 视频列表Excel
- 视频文件将下载到用户指定的目录（脚本会输出视频下载命令）

**获取MID和SEASON_ID的方法：**
1. 打开UP主空间页面 `https://space.bilibili.com/<MID>`
2. 点击"合集和列表"
3. 进入目标专辑，URL中会显示 `sid=<SEASON_ID>`

### 3. 仅获取专辑视频列表（不下载）

```python
from scripts.download_video import BilibiliCrawler

crawler = BilibiliCrawler(delay=1.5)
season_title, videos = crawler.fetch_album_videos(mid=3546856309131659, season_id=6823908)

for v in videos:
    print(f"{v.bvid}: {v.title} ({v.duration})")
```

## 设计说明

- **反爬处理**：默认1.5秒请求间隔，带指数退避重试（最多4次）
- **视频质量**：下载720p（qn=80），如需更高质量需登录态
- **视频格式**：使用DASH格式（视频+音频分离下载后合并），不重新编码
- **断点续传**：已存在的文件会自动跳过

## 限制说明

- 需要B站视频未设置地区限制或会员专属
- 公开视频可直接下载，部分视频可能需要登录态（未实现）
- 下载速度受网络环境影响，大专辑请耐心等待
