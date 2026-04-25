"""
小红书旅游规划路由：/plan/xhs_trip
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from loguru import logger

from database import get_session
from schemas.navigation import XHSPlanRequest
from poi_service import get_or_create_virtual_poi
import ai as ai_module

router = APIRouter(prefix="/plan", tags=["旅游规划"])


@router.post("/xhs_trip")
async def plan_xhs_trip(request: XHSPlanRequest, session: Session = Depends(get_session)):
    """
    1. 调用爬虫抓取小红书笔记
    2. AI 分析笔记提取景点
    """
    from crawler import XHSCrawler

    logger.info("🚀 开始执行小红书旅游规划: {}", request.keyword)

    crawler = XHSCrawler()
    notes = crawler.search_notes(request.keyword, limit=10)

    if not notes:
        return {"msg": "未找到相关笔记", "spots": []}

    poi = get_or_create_virtual_poi(
        session,
        request.keyword,
        description="网络搜索生成的虚拟景点",
    )
    if poi.legacy_spot_id is None:
        raise HTTPException(status_code=500, detail="虚拟景点创建成功但未生成 legacy_spot_id")

    saved_count = crawler.save_to_db(notes, session, user_id=1, spot_id=poi.legacy_spot_id)

    all_text = "\n".join([n["desc"] for n in notes])
    extracted_spots = await ai_module.extract_spots_from_text(all_text)

    return {
        "status": "success",
        "msg": f"成功抓取 {len(notes)} 条笔记，并存入数据库。",
        "saved_diaries": saved_count,
        "ai_extracted_spots": extracted_spots,
        "notes_preview": notes[:2],
    }
