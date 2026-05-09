import json
import os
import re
import sys
from typing import List, Dict, Any
from sqlmodel import Session, select
from models import Diary, User

CRAWLER_PATH = os.path.join(os.path.dirname(__file__), "tools", "Spider_XHS")
print(f"🔍 正在尝试加载爬虫路径: {CRAWLER_PATH}")
if os.path.exists(os.path.join(CRAWLER_PATH, "main.py")):
    print("   ✅ main.py 文件存在！")
else:
    print("   ❌ main.py 不存在！请检查文件夹位置！")

if CRAWLER_PATH not in sys.path:
    sys.path.insert(0, CRAWLER_PATH)

try:
    from main import Data_Spider
    from xhs_utils.common_util import init
    print("✅ 成功导入 Spider_XHS 模块！") # 如果打印这行，说明导入没问题
except ImportError as e:
    print(f"\n❌❌❌ 导入失败 (致命错误): {e}") # 重点看这行！
    print("   (如果是 'No module named loguru' -> 请运行 uv add loguru)")
    print("   (如果是 'cannot import name Data_Spider' -> 说明路径不对，加载了错误的 main.py)\n")
    Data_Spider = None
except Exception as e:
    print(f"\n❌❌❌ 发生未知错误: {e}\n")
    Data_Spider = None


def _parse_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip().replace(",", "")
    if not text:
        return 0

    multiplier = 1
    if text.endswith("万"):
        multiplier = 10000
        text = text[:-1]
    elif text.endswith("千"):
        multiplier = 1000
        text = text[:-1]

    try:
        return int(float(text) * multiplier)
    except ValueError:
        digits = re.findall(r"\d+", text)
        return int("".join(digits)) if digits else 0


def _extract_image_url(image: Any) -> str:
    if isinstance(image, str):
        return image
    if not isinstance(image, dict):
        return ""

    info_list = image.get("info_list")
    if isinstance(info_list, list):
        for image_info in reversed(info_list):
            if isinstance(image_info, dict) and image_info.get("url"):
                return image_info["url"]

    for key in ("url_default", "url_pre", "url", "src"):
        if image.get(key):
            return image[key]
    return ""


def _normalize_images(raw_images: Any) -> list[str]:
    if isinstance(raw_images, str):
        raw_images = raw_images.strip()
        if raw_images.startswith("["):
            try:
                raw_images = json.loads(raw_images)
            except json.JSONDecodeError:
                raw_images = []
        else:
            raw_images = [img.strip() for img in raw_images.split(",") if img.strip()]
    if not isinstance(raw_images, list):
        return []

    images = []
    for image in raw_images:
        image_url = _extract_image_url(image)
        if image_url and image_url not in images:
            images.append(image_url)
    return images


class XHSCrawler:
    def __init__(self):
        self.tool_path = CRAWLER_PATH
        # 初始化爬虫实例
        if Data_Spider:
            self.spider = Data_Spider()
        else:
            self.spider = None

    def search_notes(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        执行真实搜索 (已修改：从 .env 读取 Cookie)
        """
        if not self.spider:
            print("⚠️ 爬虫模块未加载，返回 Mock 数据")
            return self._get_mock_data(keyword, limit)

        print(f"🕷️ 开始爬取小红书关键词: {keyword}, 数量: {limit}...")

        try:
            # =======================================================
            # 🔄 修改开始：从 .env 读取配置，替代原来的 init()
            # =======================================================
            
            # 1. 从环境变量获取 Cookie
            # (注意：我们在 api.py 或 main.py 启动时已经 load_dotenv 过了，这里直接 get 即可)
            cookies_str = os.getenv("XHS_COOKIE")
            
            if not cookies_str:
                print("❌ 错误: 未在 .env 文件中找到 'XHS_COOKIE'。")
                print("   请在 .env 中添加: XHS_COOKIE='你的cookie字符串'")
                return self._get_mock_data(keyword, limit)

            # 后端导入主流程只需要结构化数据入库，不需要保存媒体或 Excel 到本地。
            base_path = {}
            
            # =======================================================
            # 🔄 修改结束
            # =======================================================

            # 3. 调用爬虫 (这里保持不变，只要传入我们构造好的 cookie 和 path 即可)
            note_list, success, msg = self.spider.spider_some_search_note(
                query=keyword,
                require_num=limit,
                cookies_str=cookies_str,
                base_path=base_path,
                save_choice='none',
            )

            if not success:
                print(f"❌ 爬取失败: {msg}")
                # 如果是 Cookie 失效，提示用户
                if "登录" in str(msg) or "401" in str(msg):
                    print("   💡 提示: 可能是 Cookie 过期了，请重新复制浏览器 Cookie 到 .env")
                return []

            # 4. 数据清洗 (Mapping)
            formatted_notes = []
            for item in note_list:
                images = _normalize_images(item.get('images') or item.get('image_list') or [])

                user_info = item.get('user', {})
                if not isinstance(user_info, dict):
                    user_info = {}

                nickname = item.get('nickname') or user_info.get('nickname') or '未知用户'
                user_id = item.get('user_id') or user_info.get('user_id') or ''

                likes = 0
                for key in ('liked_count', 'likes', 'likedCount'):
                    raw_likes = item.get(key)
                    if raw_likes is None:
                        continue
                    likes = _parse_count(raw_likes)
                    break

                note_id = item.get('note_id', '')
                note_url = item.get('note_url') or item.get('url', '')
                if not note_url and note_id:
                    note_url = f"https://www.xiaohongshu.com/explore/{note_id}"
                
                formatted_notes.append({
                    "note_id": note_id,
                    "note_url": note_url,
                    "title": item.get('title', '无标题'),
                    "desc": item.get('desc') or item.get('content') or item.get('title', ''),
                    "user": {
                        "nickname": nickname,
                        "id": user_id
                    },
                    "likes": likes,
                    "images": images
                })
            
            print(f"✅ 成功爬取 {len(formatted_notes)} 条笔记")
            return formatted_notes

        except Exception as e:
            print(f"❌ 爬虫运行异常: {e}")
            import traceback
            traceback.print_exc()
            return self._get_mock_data(keyword, limit)
        
    def _get_mock_data(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """
        返回模拟的小红书笔记数据，用于开发测试
        """
        mock_notes = []
        for i in range(limit):
            mock_notes.append({
                "note_id": f"xhs_{i}",
                "title": f"【{keyword}】必去打卡点推荐 {i+1}",
                "desc": f"今天去了{keyword}，真的太美了！强烈推荐大家去... #旅游 #打卡",
                "user": {"nickname": f"旅游达人{i}", "id": f"user_{i}"},
                "likes": 100 + i * 10,
                "images": ["https://example.com/img1.jpg"]
            })
        return mock_notes

    def save_to_db(self, notes: List[Dict[str, Any]], session: Session, user_id: int, spot_id: int):
        """
        将爬取的笔记保存为系统日记
        """
        count = 0
        for note in notes:
            title = f"[搬运] {note['title']}"
            existing = session.exec(select(Diary).where(Diary.title == title)).first()
            if existing:
                continue

            content_parts = [
                f"作者: {note['user']['nickname']}",
                "",
                note.get("desc", ""),
            ]
            if note.get("note_url"):
                content_parts.append(f"\n原文: {note['note_url']}")

            new_diary = Diary(
                user_id=user_id,
                spot_id=spot_id,
                title=title,
                content="\n".join(content_parts),
                view_count=note['likes'],
                media_json=json.dumps(note.get('images', []), ensure_ascii=False)
            )
            session.add(new_diary)
            count += 1
        
        session.commit()
        return count
