import sys
import os
from dotenv import load_dotenv
from sqlmodel import Session, select

# 1. 环境准备
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 导入我们的模块
from crawler import XHSCrawler
from database import engine
from models import User, Spot

def get_or_create_spider_user(session: Session):
    """
    创建一个专门的 '搬运工' 账号，用于发布爬来的日记
    """
    user = session.exec(select(User).where(User.username == "spider_bot")).first()
    if not user:
        print("🤖 创建 'spider_bot' 搬运工账号...")
        # 密码随便设，反正不登录
        from auth import get_password_hash
        user = User(username="spider_bot", password_hash=get_password_hash("123456"))
        session.add(user)
        session.commit()
        session.refresh(user)
    return user

def main():
    load_dotenv()
    print("🕷️ [小红书 -> 数据库] 导入工具启动...")

    # 1. 检查爬虫环境
    crawler = XHSCrawler()
    if not os.getenv("XHS_COOKIE"):
        print("❌ 错误: .env 中未找到 XHS_COOKIE，无法运行真实爬虫。")
        return

    with Session(engine) as session:
        # 2. 准备搬运工账号
        bot_user = get_or_create_spider_user(session)
        
        # 3. 让用户输入爬取目标
        keyword = input("\n请输入搜索关键词 (例如 '北邮食堂'): ").strip()
        if not keyword:
            print("❌ 关键词不能为空")
            return
            
        # 4. 让用户选择绑定到哪个景点
        # (因为爬下来的数据通过关键词匹配，最好挂载到具体的地图点位上，方便 RAG 检索)
        spot_id_input = input("请输入绑定的景点 ID (默认为 0，表示不绑定特定点): ").strip()
        spot_id = int(spot_id_input) if spot_id_input.isdigit() else 0
        
        # 检查景点是否存在
        if spot_id != 0:
            spot = session.get(Spot, spot_id)
            if spot:
                print(f"📍 将绑定到景点: {spot.name} (ID: {spot.id})")
            else:
                print(f"⚠️ 警告: 景点 ID {spot_id} 不存在，将使用 ID=0")
                spot_id = 0

        limit = input("请输入爬取数量 (默认 5): ").strip()
        limit = int(limit) if limit.isdigit() else 5

        # 5. 开始爬取
        print(f"\n🚀 正在从网络抓取关于【{keyword}】的笔记...")
        notes = crawler.search_notes(keyword, limit=limit)
        
        if not notes:
            print("❌ 未抓取到数据，终止。")
            return

        print(f"✅ 抓取成功，准备写入数据库...")
        
        # 6. 写入数据库
        # 这里我们调用 crawler.py 里写好的 save_to_db
        count = crawler.save_to_db(notes, session, user_id=bot_user.id, spot_id=spot_id)
        
        print(f"\n🎉 成功导入 {count} 条日记！")
        print("现在你可以去问 AI：'北邮食堂大家都推荐吃什么？'")

if __name__ == "__main__":
    main()