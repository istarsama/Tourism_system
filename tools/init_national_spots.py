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


def init_national_spots(input_path: str) -> dict[str, int]:
    """仅导入全国景点基础数据，不触发小红书抓取。"""

    with Session(engine) as session:
        return import_national_spots_from_path(session, input_path, fetch_xhs=False)


def main():
    parser = argparse.ArgumentParser(description="初始化全国景点数据到 national_spot 表")
    parser.add_argument(
        "--input",
        default=os.path.join(PROJECT_ROOT, "data", "national_spots.json"),
        help="景点种子文件路径，默认 data/national_spots.json",
    )
    args = parser.parse_args()

    init_db()
    stats = init_national_spots(args.input)
    print(
        "✅ 导入完成："
        f"新增 {stats['created']} 条，"
        f"更新 {stats['updated']} 条，"
        f"跳过 {stats['skipped']} 条。"
    )


if __name__ == "__main__":
    main()
