---
name: video-share-parser
description: Parse Douyin, Xiaohongshu, and similar social-media share text or direct short links into a clean title and direct media links by calling the parse.ideaflow.top parser API. Use when the user sends a copied share caption or short link and wants the parsed title plus direct no-watermark media URLs instead of the original share text.
---

# Video Share Parser

接收整段分享文案或直接链接，自动提取其中的真实 URL，调用解析接口，并返回标题与可直接访问的媒体直链。

## Workflow

1. 保留用户原始分享文案，不要手动删改，直接把整段内容交给脚本。
2. 运行脚本：

```bash
python3 scripts/parse_video_share.py '<分享文案>'
```

也可以通过标准输入传入：

```bash
pbpaste | python3 scripts/parse_video_share.py
```

3. 脚本会自动：
   - 提取文案中的第一个 `http/https` 链接
   - 调用 `https://parse.ideaflow.top/video/share/url/parse`
   - 优先返回 `video_url`
   - 若没有视频，则回退到图集链接；若仍没有，则回退到封面链接
4. 用简体中文向用户回复，默认只返回：
   - `标题`
   - `解析后链接`
5. 如果返回多个图集链接，逐条列出，不要只保留第一条。
6. 如果接口报错、没有找到链接、或返回空媒体地址，要明确说明原因。

## Output Rules

- 正常场景下不要粘贴原始 JSON，除非用户明确要求。
- 单个媒体链接时，直接输出标题和链接即可。
- 多个媒体链接时，按顺序编号列出。
- 如果用户只给了一段分享文案，不需要先让用户手动提取短链。

## Script

优先使用 `scripts/parse_video_share.py`，不要重复手写调用逻辑。

示例：

```bash
python3 scripts/parse_video_share.py '9.79 ULW:/ ... https://v.douyin.com/yqnVFy34WoU/ ...'
python3 scripts/parse_video_share.py --json 'https://v.douyin.com/yqnVFy34WoU/'
```

`--json` 仅在需要结构化结果或调试时使用。默认输出已经适合直接转发给用户。
