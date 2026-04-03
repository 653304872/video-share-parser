---
name: video-share-parser
description: Parse Douyin, Xiaohongshu, and similar social-media share text or direct short links into a clean title and direct media links by calling the parse.ideaflow.top parser API. Use when the user sends a copied share caption or short link and wants the parsed title plus direct no-watermark media URLs, or explicitly asks to download the parsed media.
---

# Video Share Parser

接收整段分享文案或直接链接，自动提取其中的真实 URL，调用解析接口，并优先返回可直接下载的媒体直链；用户侧默认优先返回该直链对应的短链（以浏览器可访问为目标），真正稳定交付继续以视频文件本体为准。

## Workflow

1. 保留用户原始分享文案，不要手动删改，直接把整段内容交给脚本。
2. 优先运行脚本，不要手写重复的 `curl + JSON` 解析逻辑：

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
   - 把 `video_url` 视为第一优先级下载链接
   - 若没有视频，则回退到 `images[*].live_photo_url`
   - 再回退到 `images[*].url`
   - 最后才回退到 `cover_url`
4. 默认向用户回复时，把“下载链接”理解为**解析结果里的直链或其短链**，不是本地上传后的云盘链接。
5. 如果用户明确要求“下载给我 / 发出来 / 保存到本地”，按固定顺序执行：先回标题和解析下载链接，再基于首选直链继续下载文件，并把视频文件发回当前聊天（如果运行环境支持发送附件）。
6. 如果接口报错、没有找到链接、或返回空媒体地址，要明确说明原因。

## Output Rules

- 正常场景下不要粘贴原始 JSON，除非用户明确要求。
- 默认优先给用户这两行，而且顺序固定：
  - `标题：...`
  - `下载链接：...`
- 其中“下载链接”应优先对应解析结果中的 `video_url`；如果能成功生成**浏览器可访问并已校验可跳转到媒体资源**的短链，则默认返回该短链；只有短链生成失败或跳转校验失败时才回退到原始长直链。只有没有视频时才回退到图集或封面。
- 短链的目标是“浏览器可访问、可跳转到视频资源”，不保证像站内按钮那样由前端脚本直接触发保存下载。
- 如果返回多个图集链接，按顺序编号列出，不要只保留第一条。
- 如果用户只给了一段分享文案，不需要先让用户手动提取短链。
- 如果用户还要求把视频或图集文件发出来，也要明确区分：
  - `下载链接` = 解析后的媒体直链
  - 上传附件/云盘链接 = 交付文件本体

## Download Flow

当用户明确要求把视频或图集“下载给我”时：

1. 先用脚本解析出首选媒体直链。
2. 如果可用，先把首选媒体直链压缩为短链，并实际校验该短链在浏览器中可访问且能跳转到媒体资源；默认先试 `is.gd`，失败或校验不通过时自动回退到 `tinyurl`。
3. 先向用户返回：

```text
标题：{title}
下载链接：{download_link}
```

4. 优先使用脚本的 `--download` 能力直接下载：

```bash
python3 scripts/parse_video_share.py --shorten --download --output /absolute/output/dir '<分享文案>'
```

5. 如果运行环境支持发送附件，把下载后的本地文件继续发回当前聊天。
6. 如果运行环境不支持直接发附件，再使用对应平台的文件上传能力处理本地文件。
7. 无论是否上传了文件，继续把解析直链对应的短链作为“下载链接”返回；只有短链失败时才回退到 `video_url` 原始长链，不要被上传后的文件链接替代。
8. 如果用户真正关注“能不能下载到本地文件”，优先直接把视频文件发回聊天，不要把短链当成唯一交付物。

## Script

优先使用 `scripts/parse_video_share.py`。

示例：

```bash
python3 scripts/parse_video_share.py '9.79 ULW:/ ... https://v.douyin.com/yqnVFy34WoU/ ...'
python3 scripts/parse_video_share.py --json 'https://v.douyin.com/yqnVFy34WoU/'
python3 scripts/parse_video_share.py --shorten 'https://v.douyin.com/yqnVFy34WoU/'
python3 scripts/parse_video_share.py --shorten --download --output /tmp/downloads 'https://v.douyin.com/yqnVFy34WoU/'
```

说明：

- `--json`：输出结构化结果，适合调试或二次集成
- `--shorten`：把首选下载直链压缩成更短的用户可读链接；默认先试 `is.gd`，若失败或校验不通过则自动尝试 `tinyurl`，都失败才回退长链
- `--download`：直接下载首选媒体文件
- `--output`：指定下载文件或目录；目录不存在时会自动创建

默认文本输出应适合直接转发给用户。下载场景下，脚本还会输出本地文件路径，便于继续上传或发送附件。

## JSON Fields

`--json` 输出时，优先关注：

- `title`
- `download_link`
- `download_short_link`
- `download_link_source`
- `media_kind`
- `video_url`
- `links`
- `downloaded_file`（仅 `--download` 时出现）

其中：

- `download_link` 是原始解析下载直链
- `download_short_link` 是面向用户优先展示的短链；若为空则说明短链生成失败，应回退 `download_link`
- 对视频内容，`download_link` 应等于 `video_url`
- 只有当 `video_url` 为空时，才允许回退到其他媒体地址

## Reply Template

默认推荐回复：

```text
标题：{title}
下载链接：{download_short_link or download_link}
```

如果用户明确要求“把视频下载给我”或“把视频发出来”，则在发出上面两行之后，再继续发送文件本体。短链只作为浏览器访问入口，不替代文件交付。

如果还附带上传后的文件，可以在后面另加一句说明，但不要把云盘链接冒充成解析下载链接。

例如：

```text
标题：{title}
下载链接：{download_link}
附件：视频文件已发送 / 已上传，可直接下载
```

如果解析失败，直接说明失败原因，不要输出空链接。
