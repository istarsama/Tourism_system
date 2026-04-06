#!/usr/bin/env python3
"""
xhs_search.py — 小红书景点帖子搜索 CLI 工具

用法:
  python .github/skills/xhs-spider/xhs_search.py <keyword> [--limit N] [--json]

退出码:
  0 - 成功
  1 - Cookie 失效或未配置
  2 - 爬虫模块加载失败
  3 - 其他错误
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from national_spot_xhs import fetch_xhs_note_previews


def main():
    parser = argparse.ArgumentParser(
        description="小红书景点帖子搜索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("keyword", help="搜索关键词（景点名称）")
    parser.add_argument("--limit", type=int, default=5, metavar="N", help="最大爬取数量（默认 5，最大 20）")
    parser.add_argument("--json", dest="output_json", action="store_true", help="以 JSON 格式输出")
    args = parser.parse_args()

    limit = min(max(1, args.limit), 20)
    result = fetch_xhs_note_previews(args.keyword, limit)

    if result.status != "success":
        if args.output_json:
            print(
                json.dumps(
                    {
                        "success": False,
                        "status": result.status,
                        "error": result.message,
                        "notes": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(result.message, file=sys.stderr)

        if result.status == "cookie_expired":
            sys.exit(1)
        if result.message and ("导入" in result.message or "加载" in result.message):
            sys.exit(2)
        sys.exit(3)

    if args.output_json:
        print(
            json.dumps(
                {
                    "success": True,
                    "keyword": args.keyword,
                    "count": len(result.notes),
                    "status": result.status,
                    "notes": result.notes,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"\n🔍 搜索关键词: {args.keyword}")
        print(f"📊 找到 {len(result.notes)} 条帖子\n")
        for index, note in enumerate(result.notes, 1):
            print(f"{'─' * 60}")
            print(f"[{index}] {note['title']}")
            print(f"    作者: {note['author_name']}")
            print(f"    点赞: {note['likes']}")
            if note["content_preview"]:
                preview = note["content_preview"][:80].replace("\n", " ")
                print(f"    预览: {preview}...")
            if note["thumbnail_url"]:
                print(f"    缩略图: {note['thumbnail_url']}")
            print(f"    链接: {note['xhs_url']}")
        print(f"{'─' * 60}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
