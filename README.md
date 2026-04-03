# Video Share Parser

一个面向 Codex / Claude Code / 龙虾(OpenClaw) / Gemini CLI 的解析型 skill，用来把抖音、小红书等平台的分享文案或短链解析成：

- `标题：...`
- `下载链接：...`

新版实现还支持：

- 优先生成更适合用户转发的短链下载地址
- 直接把媒体文件下载到本地
- 区分“解析下载链接”和“附件/云盘交付链接”
- 给 Claude Code 与 Gemini CLI 提供单独的命令文件

## 核心能力

- 自动从整段分享文案中提取第一个 `http/https` 链接
- 调用 `https://parse.ideaflow.top/video/share/url/parse`
- 按优先级选择媒体地址：
  - `video_url`
  - `images[*].live_photo_url`
  - `images[*].url`
  - `cover_url`
- 默认输出固定为：
  - `标题：...`
  - `下载链接：...`
- 可选把下载直链缩短为更适合用户点击的短链
- 可选直接下载媒体文件到本地
- 支持结构化 JSON 输出，便于二次集成

## 仓库结构

```text
video-share-parser/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── claude-code/
│   └── video-share-parser.md
├── gemini-cli/
│   └── video-share-parser.toml
└── scripts/
    └── parse_video_share.py
```

## 工作方式

这个 skill 的默认工作流程是：

1. 接收用户粘贴的整段分享文案或短链
2. 自动提取其中的真实 URL
3. 调用解析接口拿到媒体直链
4. 优先把 `video_url` 视为“下载链接”
5. 如果启用 `--shorten`，优先尝试生成短链：
   - 先试 `is.gd`
   - 失败后回退 `tinyurl`
   - 都失败再回退原始长直链
6. 如果启用 `--download`，继续把首选媒体文件下载到本地

## 快速开始

### 1. 直接解析

```bash
python3 scripts/parse_video_share.py '9.79 ULW:/ ... https://v.douyin.com/yqnVFy34WoU/ ...'
```

示例输出：

```text
标题：两个不被看好的组合，在世界顶级赛场，写下热血传奇 #张雪 #张雪机车 #德比斯 #WSBK
下载链接：https://is.gd/xxxxxx
```

### 2. 输出 JSON

```bash
python3 scripts/parse_video_share.py --json 'https://v.douyin.com/yqnVFy34WoU/'
```

### 3. 生成短链

```bash
python3 scripts/parse_video_share.py --shorten 'https://v.douyin.com/yqnVFy34WoU/'
```

### 4. 直接下载到本地

```bash
python3 scripts/parse_video_share.py --shorten --download --output /tmp/downloads 'https://v.douyin.com/yqnVFy34WoU/'
```

## 命令参数

脚本入口：`scripts/parse_video_share.py`

支持的主要参数：

- `--json`
  - 输出结构化 JSON
- `--shorten`
  - 为首选下载直链生成短链
- `--download`
  - 下载首选媒体文件到本地
- `--output`
  - 指定下载文件路径或目录

## JSON 输出字段

使用 `--json` 时，重点关注这些字段：

- `title`
- `download_link`
- `download_short_link`
- `download_link_source`
- `media_kind`
- `video_url`
- `links`
- `downloaded_file`

字段说明：

- `download_link`
  - 解析出的原始下载直链
- `download_short_link`
  - 面向用户优先展示的短链；为空时表示短链生成失败
- `download_link_source`
  - 当前下载链接来源，比如 `video_url` 或 `images[0].url`
- `media_kind`
  - `video` / `image` / `cover`
- `downloaded_file`
  - 仅在 `--download` 时出现，表示本地保存路径

## 默认回复格式

这个 skill 的默认推荐回复格式是：

```text
标题：{title}
下载链接：{download_short_link or download_link}
```

如果用户还要求“把视频发出来 / 下载给我 / 保存到本地”，则在返回上面两行后，再继续交付文件本体。

注意区分：

- `下载链接`
  - 解析结果中的媒体直链或其短链
- `附件 / 云盘链接`
  - 文件交付方式，不应冒充解析下载链接

## 依赖

- Python 3
- `curl`
- 可访问：
  - `parse.ideaflow.top`
  - `is.gd`
  - `tinyurl.com`

脚本不依赖第三方 Python 包。

## 验证建议

建议至少验证以下命令：

```bash
python3 scripts/parse_video_share.py '你的分享文案'
python3 scripts/parse_video_share.py --json '你的短链'
python3 scripts/parse_video_share.py --shorten '你的短链'
python3 scripts/parse_video_share.py --shorten --download --output /tmp/downloads '你的短链'
```

## 安装

### 先拉源码

安装前通常需要先把仓库拉到本地，因为后面的安装动作本质上是在为不同工具创建软链接：

```bash
git clone https://github.com/653304872/video-share-parser.git ~/.skills-src/video-share-parser
cd ~/.skills-src/video-share-parser
```

如果本地已经有这份源码，直接进入该目录即可。

### 一句话安装

在仓库根目录执行对应命令：

```bash
# Codex
mkdir -p ~/.codex/skills
ln -snf "$PWD" ~/.codex/skills/video-share-parser

# Claude Code
mkdir -p ~/.claude/commands
ln -snf "$PWD/claude-code/video-share-parser.md" ~/.claude/commands/video-share-parser.md

# 龙虾 / OpenClaw
mkdir -p ~/.openclaw/skills
ln -snf "$PWD" ~/.openclaw/skills/video-share-parser

# Gemini CLI
mkdir -p ~/.gemini/commands
ln -snf "$PWD/gemini-cli/video-share-parser.toml" ~/.gemini/commands/video-share-parser.toml
```

安装完成后重开当前会话即可。

## 通用安装提示词

如果你想直接交给 AI 工具执行安装，可以使用下面这版通用提示词：

```text
请帮我安装 Skill: video-share-parser

- 仓库地址: https://github.com/653304872/video-share-parser
- 建议源码目录: ~/.skills-src/video-share-parser/
- Codex 安装目录: ~/.codex/skills/video-share-parser/
- Claude Code 安装目录: ~/.claude/commands/video-share-parser.md
- 龙虾 / OpenClaw 安装目录: ~/.openclaw/skills/video-share-parser/
- Gemini CLI 安装目录: ~/.gemini/commands/video-share-parser.toml

安装要求:
1. 如果本地没有源码，先执行 git clone https://github.com/653304872/video-share-parser.git ~/.skills-src/video-share-parser
2. 如果源码已存在，先进入 ~/.skills-src/video-share-parser
3. 按当前工具创建对应软链接
4. 安装完成后提示我重开当前会话
```

## 适用范围与限制

- 当前主要服务于抖音、小红书等分享文案解析
- 解析能力依赖第三方接口稳定性
- 短链能力依赖 `is.gd` / `tinyurl`
- 媒体直链通常带签名，可能存在时效性
- “短链可访问”不等于一定能像站内按钮那样直接触发浏览器下载

## 致谢

本项目当前的解析能力建立在 `parse.ideaflow.top` 提供的解析接口之上，仓库负责把这条能力链路封装成可复用的 skill、脚本和多工具安装入口。
