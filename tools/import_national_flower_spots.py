import argparse
import os
import sys

from sqlmodel import Session

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from database import engine, init_db
from national_spot_importer import import_national_spots_from_path


def import_national_flower_spots(
    input_path: str,
    *,
    note_limit: int = 6,
    skip_fetch: bool = False,
) -> dict[str, int]:
    """
    批量导入跨城市赏花景点，并按需抓取小红书帖子预览。

    该脚本设计为可重复执行：
    - 景点按 name + city 幂等 upsert
    - 抓取成功时替换预览
    - 抓取失败时保留景点并记录失败状态/提示
    """

    with Session(engine) as session:
        return import_national_spots_from_path(
            session,
            input_path,
            fetch_xhs=not skip_fetch,
            note_limit=note_limit,
        )


def main():
    parser = argparse.ArgumentParser(description="批量导入全国赏花景点并抓取小红书帖子预览")
    parser.add_argument(
        "--input",
        default=os.path.join(PROJECT_ROOT, "data", "national_flower_spots.json"),
        help="赏花景点种子文件路径，默认 data/national_flower_spots.json",
    )
    parser.add_argument(
        "--note-limit",
        type=int,
        default=6,
        help="每个景点最多抓取多少条帖子预览，默认 6",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="只导入景点，不执行小红书抓取",
    )
    args = parser.parse_args()

    init_db()
    stats = import_national_flower_spots(
        args.input,
        note_limit=max(1, min(args.note_limit, 20)),
        skip_fetch=args.skip_fetch,
    )
    print(
        "✅ 赏花景点导入完成："
        f"新增 {stats['created']} 条，"
        f"更新 {stats['updated']} 条，"
        f"跳过 {stats['skipped']} 条，"
        f"小红书抓取成功 {stats['xhs_success']} 条，"
        f"Cookie 失效 {stats['xhs_cookie_expired']} 条，"
        f"其他失败 {stats['xhs_failed']} 条。"
    )


if __name__ == "__main__":
    main()
