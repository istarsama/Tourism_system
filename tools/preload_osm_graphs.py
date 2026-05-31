"""预加载并持久化 OSM 城市路网 GraphML 缓存。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from time import perf_counter

from sqlalchemy import delete
from sqlmodel import Session, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from database import engine, init_db  # noqa: E402
from models import NationalSpot, RouteCache  # noqa: E402
from osm_service import OSMService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="预加载 OSM 城市路网 GraphML 缓存")
    parser.add_argument("--city", help="仅预加载指定城市，例如 北京")
    parser.add_argument(
        "--transport",
        choices=("walk", "bike"),
        help="仅预加载指定交通方式；默认同时加载 walk 和 bike",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新联网下载 GraphML，并清理对应 OSM 路线结果缓存",
    )
    return parser.parse_args()


def get_active_cities(session: Session, requested_city: str | None) -> list[str]:
    if requested_city:
        return [requested_city.strip()]

    rows = session.exec(
        select(NationalSpot.city)
        .where(NationalSpot.is_active == True)  # noqa: E712
        .distinct()
        .order_by(NationalSpot.city)
    ).all()
    return [city for city in rows if city]


def clear_route_cache(session: Session, city: str, transport: str) -> int:
    prefix = f"osm:v1:{city}:{transport}:"
    result = session.execute(delete(RouteCache).where(RouteCache.cache_key.startswith(prefix)))
    session.commit()
    return int(result.rowcount or 0)


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.2f}{unit}"
        value /= 1024
    return f"{size}B"


def main() -> None:
    args = parse_args()
    init_db()
    service = OSMService()
    transports = [args.transport] if args.transport else ["walk", "bike"]
    total_size = 0
    completed = 0

    with Session(engine) as session:
        cities = get_active_cities(session, args.city)
        if not cities:
            print("未找到已启用的全国景点城市，请先导入 NationalSpot 数据。")
            return

        print(f"准备处理 {len(cities)} 个城市，交通方式: {', '.join(transports)}")
        for city in cities:
            for transport in transports:
                if args.force:
                    removed = clear_route_cache(session, city, transport)
                    print(f"[{city}/{transport}] 已清理 {removed} 条路线结果缓存")

                started_at = perf_counter()
                print(f"[{city}/{transport}] 开始加载路网...")
                try:
                    graph = service.get_city_graph(
                        city,
                        transport,
                        force_refresh=args.force,
                    )
                except ValueError as exc:
                    print(f"[{city}/{transport}] 失败: {exc}")
                    continue

                info = service.get_graph_cache_info(city, transport)
                total_size += int(info["file_size_bytes"])
                completed += 1
                print(
                    f"[{city}/{transport}] 完成: "
                    f"nodes={graph.number_of_nodes()}, "
                    f"edges={graph.number_of_edges()}, "
                    f"size={format_bytes(info['file_size_bytes'])}, "
                    f"elapsed={perf_counter() - started_at:.2f}s"
                )

    print(f"完成 {completed} 个路网缓存，总 GraphML 占用: {format_bytes(total_size)}")
    print(f"GraphML 目录: {os.path.abspath(service.cache_dir)}")


if __name__ == "__main__":
    main()
