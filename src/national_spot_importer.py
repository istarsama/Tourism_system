"""
全国景点与小红书预览的共享导入逻辑。

脚本层只负责参数解析；真正的幂等 upsert、抓取状态落库、预览替换都放在这里，
便于测试直接调用核心函数，而不是依赖 CLI。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from sqlmodel import Session, select

from models import NationalSpot, NationalSpotXHSNote
from national_spot_xhs import XHSFetchResult, fetch_xhs_note_previews

REQUIRED_FIELDS = {"name", "type", "latitude", "longitude", "city"}


def load_national_spot_seed(path: str) -> list[dict[str, Any]]:
    """读取并校验景点种子 JSON。"""

    dataset = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        raise ValueError("景点种子文件格式错误：根节点必须是数组。")
    return dataset


def _dump_json_list(value: Any) -> str:
    """统一把关键词列表等字段存成 JSON 字符串。"""

    if value is None:
        return "[]"
    if isinstance(value, list):
        return json.dumps([str(item) for item in value], ensure_ascii=False)
    return json.dumps([str(value)], ensure_ascii=False)


def build_xhs_query(item: dict[str, Any]) -> str:
    """
    生成默认小红书搜索词。

    优先使用显式配置的 xhs_query；否则回退到“景点名 + 花种/赏花”。
    """

    configured = str(item.get("xhs_query") or "").strip()
    if configured:
        return configured

    name = str(item["name"]).strip()
    flower_type = str(item.get("flower_type") or "").strip()
    city = str(item.get("city") or "").strip()
    if flower_type:
        return f"{city} {name} {flower_type}".strip()
    return f"{city} {name} 赏花".strip()


def upsert_national_spot(session: Session, item: dict[str, Any], now: datetime) -> tuple[NationalSpot, str]:
    """按 name + city 幂等写入全国景点。"""

    if not isinstance(item, dict):
        raise ValueError("景点种子项必须是对象。")
    if not REQUIRED_FIELDS.issubset(item.keys()):
        missing = ", ".join(sorted(REQUIRED_FIELDS - set(item.keys())))
        raise ValueError(f"景点种子缺少必要字段: {missing}")

    existing = session.exec(
        select(NationalSpot).where(
            NationalSpot.name == str(item["name"]),
            NationalSpot.city == str(item["city"]),
        )
    ).first()

    if existing is None:
        existing = NationalSpot(
            name=str(item["name"]),
            city=str(item["city"]),
            created_at=now,
            updated_at=now,
        )
        action = "created"
    else:
        action = "updated"

    existing.type = str(item["type"])
    existing.latitude = float(item["latitude"])
    existing.longitude = float(item["longitude"])
    existing.description = item.get("description")
    existing.province = item.get("province")
    existing.flower_type = item.get("flower_type")
    existing.best_season = item.get("best_season")
    existing.search_keywords_json = _dump_json_list(item.get("search_keywords"))
    existing.xhs_query = build_xhs_query(item)
    existing.source = str(item.get("source", "seed"))
    existing.rating = float(item.get("rating", existing.rating or 4.5))
    existing.is_active = bool(item.get("is_active", True))
    existing.updated_at = now

    session.add(existing)
    session.flush()
    return existing, action


def replace_spot_xhs_notes(
    session: Session,
    spot: NationalSpot,
    previews: list[dict[str, Any]],
    now: datetime,
) -> None:
    """
    用最新抓取结果完整替换某个景点的帖子预览。

    这里使用“先删后插”的方式，是因为前端只需要最新的一小批预览；
    直接整体替换比做字段级 diff 更简单，也能避免残留旧链接。
    """

    existing_notes = session.exec(
        select(NationalSpotXHSNote).where(NationalSpotXHSNote.national_spot_id == spot.id)
    ).all()
    for note in existing_notes:
        session.delete(note)
    session.flush()

    for index, preview in enumerate(previews):
        session.add(
            NationalSpotXHSNote(
                national_spot_id=spot.id,
                xhs_note_id=str(preview.get("note_id") or ""),
                title=str(preview.get("title") or "无标题"),
                content_preview=str(preview.get("content_preview") or ""),
                thumbnail_url=preview.get("thumbnail_url"),
                xhs_url=str(preview.get("xhs_url") or ""),
                author_name=preview.get("author_name"),
                author_id=preview.get("author_id"),
                liked_count=int(preview.get("likes", 0) or 0),
                image_urls_json=_dump_json_list(preview.get("images")),
                rank_order=index,
                created_at=now,
                updated_at=now,
            )
        )

    spot.xhs_note_count = len(previews)
    spot.xhs_fetch_status = "success"
    spot.xhs_fetch_message = f"已同步 {len(previews)} 条小红书帖子预览。"
    spot.xhs_cookie_needs_refresh = False
    spot.xhs_last_fetched_at = now
    spot.updated_at = now
    session.add(spot)


def record_xhs_fetch_failure(session: Session, spot: NationalSpot, result: XHSFetchResult, now: datetime) -> None:
    """显式记录抓取失败状态，保证前端能拿到明确提示。"""

    spot.xhs_fetch_status = result.status
    spot.xhs_fetch_message = result.message
    spot.xhs_cookie_needs_refresh = result.cookie_needs_refresh
    spot.xhs_last_fetched_at = now
    spot.updated_at = now
    session.add(spot)


def sync_spot_xhs_notes(
    session: Session,
    spot: NationalSpot,
    note_limit: int,
    fetcher: Callable[[str, int], XHSFetchResult] = fetch_xhs_note_previews,
) -> XHSFetchResult:
    """
    为单个景点同步小红书帖子预览。

    即使抓取失败，也不会抛弃已导入的景点；失败信息会落到主表状态字段里。
    """

    now = datetime.now()
    try:
        result = fetcher(spot.xhs_query or spot.name, note_limit)
    except Exception as exc:
        result = XHSFetchResult(
            status="failed",
            notes=[],
            message=f"❌ 抓取运行异常: {exc}",
            cookie_needs_refresh=False,
        )

    if result.status == "success":
        replace_spot_xhs_notes(session, spot, result.notes, now)
    else:
        record_xhs_fetch_failure(session, spot, result, now)
    return result


def import_national_spots(
    session: Session,
    dataset: list[dict[str, Any]],
    *,
    fetch_xhs: bool = False,
    note_limit: int = 5,
    fetcher: Callable[[str, int], XHSFetchResult] = fetch_xhs_note_previews,
) -> dict[str, int]:
    """批量导入全国景点，并按需抓取小红书预览。"""

    stats = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "xhs_success": 0,
        "xhs_failed": 0,
        "xhs_cookie_expired": 0,
    }
    now = datetime.now()

    for item in dataset:
        try:
            spot, action = upsert_national_spot(session, item, now)
        except ValueError:
            stats["skipped"] += 1
            continue

        stats[action] += 1

        if not fetch_xhs:
            continue

        result = sync_spot_xhs_notes(session, spot, note_limit, fetcher=fetcher)
        if result.status == "success":
            stats["xhs_success"] += 1
        elif result.status == "cookie_expired":
            stats["xhs_cookie_expired"] += 1
        else:
            stats["xhs_failed"] += 1

    session.commit()
    return stats


def import_national_spots_from_path(
    session: Session,
    input_path: str,
    *,
    fetch_xhs: bool = False,
    note_limit: int = 5,
    fetcher: Callable[[str, int], XHSFetchResult] = fetch_xhs_note_previews,
) -> dict[str, int]:
    """脚本友好的文件路径入口。"""

    dataset = load_national_spot_seed(input_path)
    return import_national_spots(
        session,
        dataset,
        fetch_xhs=fetch_xhs,
        note_limit=note_limit,
        fetcher=fetcher,
    )
