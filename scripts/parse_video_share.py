#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Any

API_URL = "https://parse.ideaflow.top/video/share/url/parse"
URL_RE = re.compile(r"https?://\S+")
TRAILING_CHARS = ")]}>.,;!?\"'，。；！？】》」』”’"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract the first URL from shared video text and parse it."
    )
    parser.add_argument("share_text", nargs="?", help="Shared text or direct URL")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print structured JSON instead of formatted text",
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


def run_curl(url: str, insecure: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [
        "curl",
        "-sS",
        "-G",
        API_URL,
        "--data-urlencode",
        f"url={url}",
        "-H",
        "User-Agent: Mozilla/5.0",
        "-H",
        "Accept: application/json",
        "--connect-timeout",
        "10",
        "--max-time",
        "30",
    ]
    if insecure:
        cmd.insert(1, "-k")
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def call_api(url: str) -> dict[str, Any]:
    result = run_curl(url, insecure=False)
    if result.returncode != 0:
        retry = run_curl(url, insecure=True)
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


def collect_links(data: dict[str, Any]) -> list[str]:
    video_url = str(data.get("video_url") or "").strip()
    if video_url:
        return [video_url]

    image_links: list[str] = []
    for item in data.get("images") or []:
        if not isinstance(item, dict):
            continue
        live_photo_url = str(item.get("live_photo_url") or "").strip()
        image_url = str(item.get("url") or "").strip()
        for candidate in (live_photo_url, image_url):
            if candidate and candidate not in image_links:
                image_links.append(candidate)
    if image_links:
        return image_links

    cover_url = str(data.get("cover_url") or "").strip()
    return [cover_url] if cover_url else []


def build_output(source_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") or {}
    title = str(data.get("title") or "").strip() or "(untitled)"
    links = collect_links(data)
    author = data.get("author") or {}
    author_name = ""
    if isinstance(author, dict):
        author_name = str(author.get("name") or "").strip()

    return {
        "title": title,
        "links": links,
        "source_url": source_url,
        "author": author_name,
        "raw": payload,
    }


def print_text(result: dict[str, Any]) -> None:
    print(f"标题: {result['title']}")
    if result["author"]:
        print(f"作者: {result['author']}")

    links = result["links"]
    if not links:
        print("解析后链接: 未返回可用媒体链接")
        return

    if len(links) == 1:
        print(f"解析后链接: {links[0]}")
        return

    print("解析后链接:")
    for index, link in enumerate(links, start=1):
        print(f"{index}. {link}")


def main() -> int:
    args = parse_args()
    try:
        share_text = read_share_text(args.share_text)
        source_url = extract_url(share_text)
        payload = call_api(source_url)
        result = build_output(source_url, payload)
    except Exception as exc:  # noqa: BLE001
        print(f"解析失败: {exc}", file=sys.stderr)
        return 1

    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
