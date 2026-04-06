"""
全国景点小红书集成工具。

该模块把 Cookie 检查、Spider_XHS 加载、结果标准化收敛到同一个地方，
这样 API、批量导入脚本与 xhs-spider skill 可以共享一套行为与错误提示。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPIDER_DIR = PROJECT_ROOT / "src" / "tools" / "Spider_XHS"

# 统一加载项目根目录的 .env，确保 CLI、脚本、API 共用同一份 Cookie 配置。
load_dotenv(PROJECT_ROOT / ".env")

COOKIE_REFRESH_HINT = "小红书抓取依赖有效 Cookie，请更新 .env 中的 XHS_COOKIE 后重试。"


@dataclass(slots=True)
class XHSFetchResult:
    """统一描述一次小红书抓取结果，便于数据库状态落库。"""

    status: str
    notes: list[dict[str, Any]]
    message: str | None = None
    cookie_needs_refresh: bool = False


def _get_cookie() -> str | None:
    """从环境变量读取小红书 Cookie。"""

    return os.getenv("XHS_COOKIE") or os.getenv("COOKIES")


def _check_cookie_valid(cookie: str) -> bool:
    """用关键字段做轻量校验，提前识别明显无效的 Cookie。"""

    return bool(cookie) and ("web_session" in cookie or "a1" in cookie)


def _load_spider() -> tuple[type[Any] | None, str | None]:
    """
    通过 importlib 精确加载 Spider_XHS/main.py。

    这里不直接 `import main`，因为项目根目录本身也有 `main.py`，
    直接导入很容易与后端启动入口发生命名冲突。
    """

    try:
        spider_main_path = SPIDER_DIR / "main.py"
        if not spider_main_path.exists():
            return None, f"无法加载 Spider_XHS/main.py，请确认文件存在: {SPIDER_DIR}"

        if str(SPIDER_DIR) not in sys.path:
            sys.path.insert(0, str(SPIDER_DIR))
        if str(PROJECT_ROOT / "src") not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT / "src"))

        spec = importlib.util.spec_from_file_location("spider_xhs_main", spider_main_path)
        if spec is None or spec.loader is None:
            return None, f"无法加载 Spider_XHS/main.py，请确认文件存在: {SPIDER_DIR}"

        module = importlib.util.module_from_spec(spec)
        sys.modules["spider_xhs_main"] = module
        spec.loader.exec_module(module)
        data_spider = getattr(module, "Data_Spider", None)
        if data_spider is None:
            return None, "Spider_XHS/main.py 中未找到 Data_Spider 类。"
        return data_spider, None
    except ImportError as exc:
        return (
            None,
            f"导入 Spider_XHS 依赖失败: {exc}\n请在 src/tools/Spider_XHS/ 目录下运行 pip install -r requirements.txt。",
        )
    except Exception as exc:
        return None, f"加载爬虫时发生未知错误: {exc}"


def _build_base_path() -> dict[str, str]:
    """构造 Spider_XHS 所需的输出目录。"""

    downloads_dir = PROJECT_ROOT / "downloads"
    base_path = {
        "media": str(downloads_dir / "media"),
        "excel": str(downloads_dir / "excel"),
    }
    os.makedirs(base_path["media"], exist_ok=True)
    os.makedirs(base_path["excel"], exist_ok=True)
    return base_path


def detect_cookie_issue(message: str | None) -> bool:
    """统一判断错误是否与 Cookie 过期/缺失有关。"""

    if not message:
        return False
    lowered = message.lower()
    keywords = (
        "xhs_cookie",
        "cookie",
        "401",
        "sign_out",
        "登录",
        "web_session",
        "a1",
    )
    return any(keyword in lowered for keyword in keywords)


def normalize_fetch_error(message: str) -> tuple[str, bool]:
    """
    将底层错误转成可直接暴露给前端与脚本日志的用户友好文案。

    返回值:
        (normalized_message, cookie_needs_refresh)
    """

    if detect_cookie_issue(message):
        return f"{message}\n{COOKIE_REFRESH_HINT}", True
    return message, False


def format_xhs_note(note: dict[str, Any]) -> dict[str, Any]:
    """把 Spider_XHS 的原始字典转换成稳定的帖子预览结构。"""

    note_id = str(note.get("note_id") or note.get("id") or "").strip()
    title = str(note.get("title") or "无标题").strip() or "无标题"
    desc = str(note.get("desc") or "")

    images = note.get("image_list", [])
    if isinstance(images, str):
        images = [item.strip() for item in images.split(",") if item.strip()]
    elif not isinstance(images, list):
        images = []

    thumbnail = images[0] if images else None

    user = note.get("user", {})
    if not isinstance(user, dict):
        user = {}

    author_name = str(note.get("nickname") or user.get("nickname") or "未知作者")
    author_id = str(note.get("user_id") or user.get("user_id") or "")

    likes = 0
    for key in ("liked_count", "likes", "likedCount"):
        value = note.get(key)
        if value is None:
            continue
        try:
            likes = int(value)
            break
        except (TypeError, ValueError):
            continue

    xhs_url = str(note.get("note_url") or note.get("url") or "").strip()
    if not xhs_url and note_id:
        xsec_token = str(note.get("xsec_token") or "").strip()
        xhs_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        if xsec_token:
            xhs_url = f"{xhs_url}?xsec_token={xsec_token}"

    return {
        "note_id": note_id,
        "title": title,
        "content_preview": desc[:200] if desc else "",
        "thumbnail_url": thumbnail,
        "xhs_url": xhs_url,
        "author_name": author_name,
        "author_id": author_id,
        "likes": likes,
        "images": images,
    }


def search_xhs_notes(keyword: str, limit: int = 5) -> tuple[list[dict[str, Any]], str | None]:
    """执行真实小红书搜索，并返回标准化后的帖子预览列表。"""

    cookie = _get_cookie()
    if not cookie:
        return [], f"❌ 未找到 XHS_COOKIE。\n{COOKIE_REFRESH_HINT}"

    if not _check_cookie_valid(cookie):
        return [], f"❌ XHS_COOKIE 格式无效（缺少 web_session 或 a1 字段）。\n{COOKIE_REFRESH_HINT}"

    data_spider_class, load_error = _load_spider()
    if load_error:
        return [], load_error

    try:
        spider = data_spider_class()
        note_list, success, message = spider.spider_some_search_note(
            query=keyword,
            require_num=min(max(1, limit), 20),
            cookies_str=cookie,
            base_path=_build_base_path(),
            save_choice="excel",
            excel_name=f"xhs_{keyword[:20]}",
        )
        if not success:
            normalized_message, _ = normalize_fetch_error(f"❌ 搜索失败: {message}")
            return [], normalized_message
        return [format_xhs_note(note) for note in note_list if note], None
    except Exception as exc:
        normalized_message, _ = normalize_fetch_error(f"❌ 爬虫运行异常: {exc}")
        return [], normalized_message


def fetch_xhs_note_previews(keyword: str, limit: int = 5) -> XHSFetchResult:
    """返回包含状态、错误提示与帖子预览的统一抓取结果。"""

    notes, error = search_xhs_notes(keyword, limit=limit)
    if error:
        normalized_message, cookie_needs_refresh = normalize_fetch_error(error)
        return XHSFetchResult(
            status="cookie_expired" if cookie_needs_refresh else "failed",
            notes=[],
            message=normalized_message,
            cookie_needs_refresh=cookie_needs_refresh,
        )

    return XHSFetchResult(
        status="success",
        notes=notes,
        message=f"已同步 {len(notes)} 条小红书帖子预览。",
        cookie_needs_refresh=False,
    )
