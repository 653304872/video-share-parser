# Video Share Parser Skill

一个面向 Codex 的本地 skill，用来把抖音、小红书等平台的分享文案或短链解析为标题和可直接访问的媒体链接。

当前实现默认调用：

```text
https://parse.ideaflow.top/video/share/url/parse
```

适合下面这类输入：

- 抖音分享文案
- 小红书分享文案
- 只包含一个短链的纯链接文本
- 需要从整段口令文案中自动提取 URL 的场景

## 功能特性

- 自动从整段分享文案中提取第一个 `http/https` 链接
- 调用解析接口并返回结构化结果
- 默认输出适合直接回复用户的文本格式
- 支持 `--json` 输出，便于调试或二次集成
- 优先返回视频链接
- 没有视频时自动回退到图集链接或封面链接
- 可直接作为 Codex skill 使用

## 目录结构

```text
video-share-parser/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
└── scripts/
    └── parse_video_share.py
```

## Skill 说明

这个仓库本身就是一个完整 skill，核心入口文件是：

- `SKILL.md`

UI 元数据文件：

- `agents/openai.yaml`

可执行脚本：

- `scripts/parse_video_share.py`

## 快速开始

### 1. 直接运行脚本

```bash
python3 scripts/parse_video_share.py '9.79 ULW:/ Q@k.Cu 05/25 两个不被看好的组合，在世界顶级赛场，写下热血传奇 https://v.douyin.com/yqnVFy34WoU/ 复制此链接，打开Dou音搜索，直接观看视频！'
```

### 2. 从剪贴板读取

macOS:

```bash
pbpaste | python3 scripts/parse_video_share.py
```

### 3. 输出 JSON

```bash
python3 scripts/parse_video_share.py --json 'https://v.douyin.com/yqnVFy34WoU/'
```

## 示例输出

默认文本输出：

```text
标题: 两个不被看好的组合，在世界顶级赛场，写下热血传奇 #张雪 #张雪机车 #德比斯 #WSBK
作者: Moto咆哮
解析后链接: https://...
```

JSON 输出：

```json
{
  "title": "两个不被看好的组合，在世界顶级赛场，写下热血传奇 #张雪 #张雪机车 #德比斯 #WSBK",
  "links": [
    "https://..."
  ],
  "source_url": "https://v.douyin.com/yqnVFy34WoU/",
  "author": "Moto咆哮"
}
```

## 安装为本地 Codex Skill

如果你希望 Codex 自动发现这个 skill，可以把整个目录复制或移动到：

```text
~/.codex/skills/video-share-parser
```

或者软链接到该位置：

```bash
ln -s /absolute/path/to/video-share-parser ~/.codex/skills/video-share-parser
```

安装后，Codex 在识别到“分享文案解析”“视频去水印解析”“短链提取真实媒体链接”等意图时，就可以触发这个 skill。

## 工作流程

脚本内部流程如下：

1. 接收用户输入的整段分享文案或直接链接
2. 提取第一个 `http/https` URL
3. 调用解析接口
4. 解析返回 JSON
5. 从结果中优先选取：
   - `video_url`
   - `images[*].live_photo_url`
   - `images[*].url`
   - `cover_url`
6. 输出标题和链接

## 接口说明

当前默认解析接口：

```text
GET /video/share/url/parse?url=<encoded_url>
```

完整地址：

```text
https://parse.ideaflow.top/video/share/url/parse
```

请求方式由脚本通过 `curl` 发起，并附带浏览器风格的 `User-Agent`。

## 参数说明

### `scripts/parse_video_share.py`

位置参数：

- `share_text`
  - 分享文案或直接链接
  - 可省略；省略时从标准输入读取

可选参数：

- `--json`
  - 输出结构化 JSON
  - 适合调试或集成到其他脚本

## 依赖要求

- macOS / Linux
- Python 3
- `curl`

脚本不依赖第三方 Python 包，便于直接运行。

## 异常处理

脚本会在以下场景返回错误：

- 输入文案里没有 `http/https` 链接
- 解析接口不可访问
- 接口返回非 JSON
- 接口返回业务错误
- 返回结果中没有任何可用媒体链接

## 适用范围与限制

- 当前主要针对分享口令或短链解析
- 解析结果依赖第三方接口可用性
- 媒体直链可能带签名并具有时效性
- 平台侧风控、接口变更或 CDN 策略变化可能导致解析失效

## 开发与验证

本仓库已验证以下路径：

- 使用完整抖音分享文案进行解析
- 使用纯短链进行解析
- 使用 `--json` 模式返回结构化结果

推荐手动回归命令：

```bash
python3 scripts/parse_video_share.py '你的分享文案'
python3 scripts/parse_video_share.py --json '你的短链'
```

## 后续可扩展方向

- 增加对更多平台的兼容说明
- 支持批量解析
- 提供更短的纯 API 模式输出
- 增加单元测试或回归样例

## 致谢

这个 skill 的解析能力当前建立在 `parse.ideaflow.top` 提供的接口之上，仓库本身负责把解析链路封装为可复用的 Codex skill 和本地脚本。

## 一句话安装

需要先把仓库拉到本地并进入仓库根目录，例如：

```bash
git clone https://github.com/653304872/video-share-parser.git
cd video-share-parser
```

然后按你使用的工具执行对应安装命令：

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

安装完成后重开会话即可。
