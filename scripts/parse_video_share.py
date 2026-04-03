#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

API_URL = "https://parse.ideaflow.top/video/share/url/parse"
SHORTENER_API_URL = "https://is.gd/create.php"
TINYURL_API_URL = "https://tinyurl.com/api-create.php"
USER_AGENT = "Mozilla/5.0"
URL_RE = re.compile(r"https?://\S+")
TRAILING_CHARS = ")]}>.,;!?\"'，。；！？】》」』”’"
DEFAULT_TIMEOUT_SECONDS = "30"
DOWNLOAD_TIMEOUT_SECONDS = "600"
SHORT_LINK_TEST_TIMEOUT_SECONDS = "20"

EXT_BY_MIME_HINT = {
    "video_mp4": ".mp4",
    "image_jpeg": ".jpg",
    "image_png": ".png",
    "image_webp": ".webp",
    "image_gif": ".gif",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract the first URL from shared video text, parse it, and optionally "
            "download the preferred media file."
        )
    )
    parser.add_argument("share_text", nargs="?", help="Shared text or direct URL")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print structured JSON instead of formatted text",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the preferred direct media link to disk",
    )
    parser.add_argument(
        "--shorten",
        action="store_true",
        help="Shorten the preferred direct media link for user-facing output",
    )
    parser.add_argument(
        "--output",
        help=(
            "Output file path or directory used with --download. "
            "Defaults to the current directory."
        ),
    )
    return parser.parse_args()


def read_share_text(arg: str | None) -> str:
    if arg:
        return arg.strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    raise ValueError("Please provide share text as an argument or via stdin.")


def extract_url(text: str) -> str:
    match = URL_RE.search(text)
    if not match:
        raise ValueError("No valid http/https URL found in the provided text.")
    return match.group(0).rstrip(TRAILING_CHARS)


def run_curl_request(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def build_api_cmd(url: str, insecure: bool = False) -> list[str]:
    cmd = [
        "curl",
        "-sS",
        "-G",
        API_URL,
        "--data-urlencode",
        f"url={url}",
        "-H",
        f"User-Agent: {USER_AGENT}",
        "-H",
        "Accept: application/json",
        "--connect-timeout",
        "10",
        "--max-time",
        DEFAULT_TIMEOUT_SECONDS,
    ]
    if insecure:
        cmd.insert(1, "-k")
    return cmd


def build_shortener_cmd(url: str, provider: str = "isgd") -> list[str]:
    if provider == "tinyurl":
        return [
            "curl",
            "-fsSL",
            "--get",
            TINYURL_API_URL,
            "--data-urlencode",
            f"url={url}",
            "-A",
            USER_AGENT,
            "--connect-timeout",
            "10",
            "--max-time",
            "20",
        ]

    return [
        "curl",
        "-fsSL",
        "--get",
        SHORTENER_API_URL,
        "--data-urlencode",
        "format=simple",
        "--data-urlencode",
        f"url={url}",
        "-A",
        USER_AGENT,
        "--connect-timeout",
        "10",
        "--max-time",
        "20",
    ]


def call_api(url: str) -> dict[str, Any]:
    result = run_curl_request(build_api_cmd(url, insecure=False))
    if result.returncode != 0:
        retry = run_curl_request(build_api_cmd(url, insecure=True))
        if retry.returncode != 0:
            detail = retry.stderr.strip() or result.stderr.strip() or "curl failed"
            raise RuntimeError(f"Parser request failed: {detail}")
        result = retry

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        snippet = result.stdout[:200].strip()
        raise RuntimeError(f"Parser returned invalid JSON: {snippet}") from exc

    if payload.get("code") != 200:
        msg = payload.get("msg") or "Unknown parser error"
        raise RuntimeError(f"Parser returned an error: {msg}")

    return payload


def collect_media_candidates(data: dict[str, Any]) -> list[dict[str, str]]:
    video_url = str(data.get("video_url") or "").strip()
    if video_url:
        return [{"url": video_url, "kind": "video", "source": "video_url"}]

    image_links: list[dict[str, str]] = []
    for index, item in enumerate(data.get("images") or []):
        if not isinstance(item, dict):
            continue
        live_photo_url = str(item.get("live_photo_url") or "").strip()
        image_url = str(item.get("url") or "").strip()

        for source_name, candidate in (
            (f"images[{index}].live_photo_url", live_photo_url),
            (f"images[{index}].url", image_url),
        ):
            if candidate and all(existing["url"] != candidate for existing in image_links):
                image_links.append(
                    {
                        "url": candidate,
                        "kind": "image",
                        "source": source_name,
                    }
                )
    if image_links:
        return image_links

    cover_url = str(data.get("cover_url") or "").strip()
    if cover_url:
        return [{"url": cover_url, "kind": "cover", "source": "cover_url"}]

    return []


def build_output(source_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") or {}
    title = str(data.get("title") or "").strip() or "(untitled)"
    author = data.get("author") or {}
    author_name = ""
    if isinstance(author, dict):
        author_name = str(author.get("name") or "").strip()

    candidates = collect_media_candidates(data)
    links = [candidate["url"] for candidate in candidates]
    preferred = candidates[0] if candidates else {}

    return {
        "title": title,
        "author": author_name,
        "source_url": source_url,
        "download_link": preferred.get("url", ""),
        "download_short_link": "",
        "download_link_source": preferred.get("source", ""),
        "media_kind": preferred.get("kind", "none"),
        "video_url": str(data.get("video_url") or "").strip(),
        "cover_url": str(data.get("cover_url") or "").strip(),
        "links": links,
        "raw": payload,
    }


def short_link_resolves_to_media(short_link: str, expected_url: str) -> bool:
    probe_cmd = [
        "curl",
        "-fsSIL",
        "-o",
        "/dev/null",
        "-w",
        "%{url_effective}",
        "-L",
        "-A",
        USER_AGENT,
        "--connect-timeout",
        "10",
        "--max-time",
        SHORT_LINK_TEST_TIMEOUT_SECONDS,
        short_link,
    ]
    probe = run_curl_request(probe_cmd)
    if probe.returncode != 0:
        return False

    final_url = probe.stdout.strip()
    if not final_url:
        return False

    if final_url == expected_url:
        return True

    expected_host = urllib.parse.urlparse(expected_url).netloc
    final_host = urllib.parse.urlparse(final_url).netloc
    return bool(expected_host and final_host and expected_host == final_host)


def shorten_download_link(result: dict[str, Any]) -> None:
    download_link = str(result.get("download_link") or "").strip()
    if not download_link:
        return

    for provider in ("isgd", "tinyurl"):
        shortener_result = run_curl_request(build_shortener_cmd(download_link, provider=provider))
        if shortener_result.returncode != 0:
            continue

        short_link = shortener_result.stdout.strip()
        if not (short_link.startswith("http://") or short_link.startswith("https://")):
            continue
        if not short_link_resolves_to_media(short_link, download_link):
            continue

        result["download_short_link"] = short_link
        result["download_short_link_provider"] = provider
        return


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name).strip()
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", cleaned)
    cleaned = cleaned.strip(" ._")
    return cleaned[:120] or "video-share"


def guess_extension(result: dict[str, Any]) -> str:
    preferred_link = str(result.get("download_link") or "").strip()
    if not preferred_link:
        return ".bin"

    parsed = urllib.parse.urlparse(preferred_link)
    query = urllib.parse.parse_qs(parsed.query)
    mime_hint = (query.get("mime_type") or [""])[0].strip().lower()
    if mime_hint in EXT_BY_MIME_HINT:
        return EXT_BY_MIME_HINT[mime_hint]

    suffix = Path(parsed.path).suffix
    if suffix and len(suffix) <= 8:
        return suffix

    media_kind = result.get("media_kind")
    if media_kind == "video":
        return ".mp4"
    if media_kind in {"image", "cover"}:
        return ".jpg"
    return ".bin"


def resolve_output_path(result: dict[str, Any], output: str | None) -> Path:
    default_name = sanitize_filename(str(result.get("title") or "video-share")) + guess_extension(result)

    if not output:
        return Path.cwd() / default_name

    raw_path = Path(output).expanduser()
    if output.endswith(os.sep) or (raw_path.exists() and raw_path.is_dir()):
        return raw_path / default_name

    if raw_path.suffix:
        return raw_path

    return raw_path / default_name


def download_media(result: dict[str, Any], output: str | None) -> Path:
    preferred_link = str(result.get("download_link") or "").strip()
    if not preferred_link:
        raise RuntimeError("No downloadable media link returned by the parser.")

    target_path = resolve_output_path(result, output)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "-A",
        USER_AGENT,
        "--connect-timeout",
        "10",
        "--max-time",
        DOWNLOAD_TIMEOUT_SECONDS,
        preferred_link,
        "-o",
        str(target_path),
    ]
    download_result = run_curl_request(cmd)
    if download_result.returncode != 0:
        detail = download_result.stderr.strip() or "curl download failed"
        raise RuntimeError(f"Download failed: {detail}")

    return target_path


def print_text(result: dict[str, Any]) -> None:
    print(f"标题：{result['title']}")

    download_link = str(result.get("download_short_link") or result.get("download_link") or "").strip()
    if not download_link:
        print("下载链接：未返回可用媒体链接")
        return

    print(f"下载链接：{download_link}")


def main() -> int:
    args = parse_args()
    try:
        share_text = read_share_text(args.share_text)
        source_url = extract_url(share_text)
        payload = call_api(source_url)
        result = build_output(source_url, payload)
        if args.shorten:
            shorten_download_link(result)
        if args.download:
            downloaded_file = download_media(result, args.output)
            result["downloaded_file"] = str(downloaded_file)
    except Exception as exc:  # noqa: BLE001
        print(f"解析失败：{exc}", file=sys.stderr)
        return 1

    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
        if args.download:
            print(f"本地文件：{result['downloaded_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
