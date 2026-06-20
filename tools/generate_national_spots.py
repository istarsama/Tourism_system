"""从 OpenStreetMap 生成以北京为主的全国景点种子数据。"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "national_spots.json"
DEFAULT_LIMIT = 240
MINIMUM_COUNT = 201  # “> 200”是严格大于，不能写成 200。
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
ATTRIBUTION = "© OpenStreetMap contributors, ODbL 1.0"

# 北京中心城区及近郊。覆盖范围比仅按行政区名称查询更稳定，也能降低 Overpass 压力。
OVERPASS_QUERY = """
[out:json][timeout:180];
(
  nwr["name"]["tourism"~"^(attraction|museum|gallery|viewpoint|theme_park|zoo)$"](39.70,115.95,40.25,116.85);
  nwr["name"]["historic"](39.70,115.95,40.25,116.85);
  nwr["name"]["leisure"~"^(park|garden|nature_reserve)$"](39.70,115.95,40.25,116.85);
);
out center tags;
"""


def fetch_osm(preferred_url: str | None = None) -> list[dict[str, Any]]:
    """请求 Overpass；默认端点繁忙时自动尝试镜像。"""

    urls = (preferred_url,) if preferred_url else OVERPASS_URLS
    body = urllib.parse.urlencode({"data": OVERPASS_QUERY}).encode("utf-8")
    failures: list[str] = []
    for url in urls:
        if not url:
            continue
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "User-Agent": "TourismSystemNationalSpots/1.0",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                return json.load(response).get("elements", [])
        except (OSError, ValueError, urllib.error.URLError) as exc:
            failures.append(f"{url}: {exc}")
    raise RuntimeError("Overpass 请求失败：" + "；".join(failures))


def coordinates(element: dict[str, Any]) -> tuple[float, float] | None:
    center = element.get("center", {})
    latitude = element.get("lat", center.get("lat"))
    longitude = element.get("lon", center.get("lon"))
    if latitude is None or longitude is None:
        return None
    return float(latitude), float(longitude)


def classify(tags: dict[str, str]) -> str:
    tourism = tags.get("tourism")
    if tourism in {"museum", "gallery"}:
        return "博物馆展馆"
    if tourism == "viewpoint":
        return "观景点"
    if tourism in {"theme_park", "zoo"}:
        return "主题景区"
    if tags.get("leisure") in {"park", "garden", "nature_reserve"}:
        return "公园园林"
    if tags.get("historic"):
        return "历史遗迹"
    return "人文景观"


def rating(name: str) -> float:
    """用名称稳定生成 4.2~4.9 的演示评分，避免每次刷新发生漂移。"""

    number = int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8], 16)
    return round(4.2 + number % 8 / 10, 1)


def normalize(elements: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for element in elements:
        tags = element.get("tags", {})
        name = str(tags.get("name:zh") or tags.get("name") or "").strip()
        point = coordinates(element)
        if not name or point is None:
            continue
        latitude, longitude = point
        key = (name, round(latitude, 5), round(longitude, 5))
        if key in seen:
            continue
        seen.add(key)
        spot_type = classify(tags)
        description = str(tags.get("description:zh") or tags.get("description") or "").strip()
        if not description:
            description = f"北京{spot_type}，名称和位置参考 OpenStreetMap。"
        records.append(
            {
                "name": name,
                "type": spot_type,
                "latitude": round(latitude, 7),
                "longitude": round(longitude, 7),
                "description": description,
                "city": "北京市",
                "province": "北京市",
                "rating": rating(name),
                "search_keywords": [name, "北京", spot_type],
                "xhs_query": f"北京 {name} 攻略",
                "source": "OpenStreetMap",
                "osm_type": element.get("type"),
                "osm_id": element.get("id"),
                "osm_tags": {
                    key: tags[key]
                    for key in ("tourism", "historic", "leisure", "heritage")
                    if key in tags
                },
                "attribution": ATTRIBUTION,
            }
        )

    # 中文名称优先，再按类型、名称稳定排序，保证输出可复现且适合中国数据集。
    records.sort(
        key=lambda item: (
            not any("\u4e00" <= char <= "\u9fff" for char in item["name"]),
            item["type"],
            item["name"],
            item["osm_id"] or 0,
        )
    )
    selected = records[:limit]
    validate(selected)
    return selected


def validate(records: Any) -> None:
    if not isinstance(records, list):
        raise ValueError("数据根节点必须是数组")
    if len(records) < MINIMUM_COUNT:
        raise ValueError(f"景点数量为 {len(records)}，要求至少 {MINIMUM_COUNT} 条")
    required = {"name", "type", "latitude", "longitude", "city"}
    for index, item in enumerate(records):
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError(f"第 {index + 1} 条景点缺少必要字段")
    unique = {(item["name"], item["latitude"], item["longitude"]) for item in records}
    if len(unique) != len(records):
        raise ValueError("景点数据存在重复的名称和坐标组合")


def write_snapshot(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成北京为主的 OSM 全国景点 JSON")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="输出 JSON 路径")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="输出数量，默认 240")
    parser.add_argument("--overpass-url", help="指定 Overpass API 地址")
    parser.add_argument("--validate-only", action="store_true", help="只校验现有文件，不访问网络")
    args = parser.parse_args()

    if args.limit < MINIMUM_COUNT:
        parser.error(f"--limit 必须至少为 {MINIMUM_COUNT}")
    if args.validate_only:
        records = json.loads(args.output.read_text(encoding="utf-8"))
        validate(records)
    else:
        records = normalize(fetch_osm(args.overpass_url), args.limit)
        write_snapshot(args.output, records)
    print(f"校验通过：{args.output} 共 {len(records)} 个景点（要求 > 200）")


if __name__ == "__main__":
    main()
