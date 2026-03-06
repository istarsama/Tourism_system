import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from database import engine, init_db
from models import NationalSpot


def _load_json(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("景点种子文件格式错误：根节点必须是数组。")
    return data


def _required_fields() -> set[str]:
    return {"name", "type", "latitude", "longitude", "city"}


def init_national_spots(input_path: str) -> dict[str, int]:
    dataset = _load_json(input_path)
    stats = {"created": 0, "updated": 0, "skipped": 0}
    now = datetime.now()

    with Session(engine) as session:
        for item in dataset:
            if not isinstance(item, dict):
                stats["skipped"] += 1
                continue
            if not _required_fields().issubset(item.keys()):
                stats["skipped"] += 1
                continue

            existing = session.exec(
                select(NationalSpot).where(
                    NationalSpot.name == str(item["name"]),
                    NationalSpot.city == str(item["city"]),
                )
            ).first()

            if existing:
                existing.type = str(item["type"])
                existing.latitude = float(item["latitude"])
                existing.longitude = float(item["longitude"])
                existing.description = item.get("description")
                existing.rating = float(item.get("rating", existing.rating or 4.5))
                existing.is_active = bool(item.get("is_active", True))
                existing.updated_at = now
                session.add(existing)
                stats["updated"] += 1
                continue

            session.add(
                NationalSpot(
                    name=str(item["name"]),
                    type=str(item["type"]),
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                    description=item.get("description"),
                    city=str(item["city"]),
                    rating=float(item.get("rating", 4.5)),
                    is_active=bool(item.get("is_active", True)),
                    created_at=now,
                    updated_at=now,
                )
            )
            stats["created"] += 1

        session.commit()

    return stats


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
        f"✅ 导入完成：新增 {stats['created']} 条，更新 {stats['updated']} 条，跳过 {stats['skipped']} 条。"
    )


if __name__ == "__main__":
    main()
