import json
import os
import sys
import subprocess
from typing import List, Dict, Any
from sqlmodel import Session
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

            # 2. 手动构造保存路径 (base_path)
            # 原来的 init() 会读取 yaml 配置路径，我们这里直接指定到项目的 downloads 文件夹
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 回退两层到根目录
            download_dir = os.path.join(project_root, "downloads")
            
            base_path = {
                "media": os.path.join(download_dir, "media"), # 图片/视频保存路径
                "excel": os.path.join(download_dir, "excel")  # Excel 保存路径
            }
            
            # 自动创建文件夹，防止报错
            os.makedirs(base_path["media"], exist_ok=True)
            os.makedirs(base_path["excel"], exist_ok=True)
            
            # =======================================================
            # 🔄 修改结束
            # =======================================================

            # 3. 调用爬虫 (这里保持不变，只要传入我们构造好的 cookie 和 path 即可)
            note_list, success, msg = self.spider.spider_some_search_note(
                query=keyword,
                require_num=limit,
                cookies_str=cookies_str,
                base_path=base_path,
                save_choice='excel', # 我们选择保存一份 Excel 作为备份，也可以改代码支持 'none'
                excel_name=f"search_{keyword}"
            )

            if not success:
                print(f"❌ 爬取失败: {msg}")
                # 如果是 Cookie 失效，提示用户
                if "登录" in str(msg) or "401" in str(msg):
                    print("   💡 提示: 可能是 Cookie 过期了，请重新复制浏览器 Cookie 到 .env")
                return []

            # 4. 数据清洗 (Mapping) - 保持不变
            formatted_notes = []
            for item in note_list:
                images = item.get('image_list', [])
                if isinstance(images, str):
                    images = images.split(',')
                
                formatted_notes.append({
                    "note_id": item.get('note_id', ''),
                    "title": item.get('title', '无标题'),
                    "desc": item.get('desc', ''),
                    "user": {
                        "nickname": item.get('user', {}).get('nickname', '未知用户'),
                        "id": item.get('user', {}).get('user_id', '')
                    },
                    "likes": int(item.get('liked_count', 0)),
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
            # 简单的排重逻辑 (实际可能需要更复杂的判断)
            # 这里直接创建新日记
            new_diary = Diary(
                user_id=user_id,
                spot_id=spot_id,
                title=f"[搬运] {note['title']}",
                content=f"作者: {note['user']['nickname']}\n\n{note['desc']}",
                view_count=note['likes'],
                media_json=json.dumps(note.get('images', []))
            )
            session.add(new_diary)
            count += 1
        
        session.commit()
        return count
