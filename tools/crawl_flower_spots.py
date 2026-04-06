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
from national_spot_importer import import_national_spots, load_national_spot_seed


def crawl_flower_spots(
    input_path: str,
    *,
    city: str | None = None,
    note_limit: int = 6,
    skip_fetch: bool = False,
) -> dict[str, int]:
    dataset = load_national_spot_seed(input_path)
    if city:
        dataset = [
            item
            for item in dataset
            if str(item.get("city") or "").strip().lower() == city.strip().lower()
        ]

    with Session(engine) as session:
        return import_national_spots(
            session,
            dataset,
            fetch_xhs=not skip_fetch,
            note_limit=note_limit,
        )


def main():
    parser = argparse.ArgumentParser(description="按城市抓取赏花景点并同步小红书帖子预览")
    parser.add_argument(
        "--input",
        default=os.path.join(PROJECT_ROOT, "data", "national_flower_spots.json"),
        help="赏花景点种子文件路径，默认 data/national_flower_spots.json",
    )
    parser.add_argument("--city", default=None, help="只抓取指定城市的景点，例如 武汉")
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
    stats = crawl_flower_spots(
        args.input,
        city=args.city,
        note_limit=max(1, min(args.note_limit, 20)),
        skip_fetch=args.skip_fetch,
    )
    scope_label = f"{args.city}赏花景点" if args.city else "全国赏花景点"
    print(
        f"✅ {scope_label}同步完成："
        f"新增 {stats['created']} 条，"
        f"更新 {stats['updated']} 条，"
        f"跳过 {stats['skipped']} 条，"
        f"小红书抓取成功 {stats['xhs_success']} 条，"
        f"Cookie 失效 {stats['xhs_cookie_expired']} 条，"
        f"其他失败 {stats['xhs_failed']} 条。"
    )


if __name__ == "__main__":
    main()
