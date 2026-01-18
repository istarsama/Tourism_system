import json
import os
from sqlmodel import Session, select
from database import engine, init_db
from models import User, Diary, Comment
from passlib.context import CryptContext

# 密码加密工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def import_mock_data():
    # 1. 确保表存在
    init_db()
    
    # 2. 读取 JSON 文件
    file_path = "src/mock_data.json"
    if not os.path.exists(file_path):
        print(f"❌ 找不到文件: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with Session(engine) as session:
        print("🚀 开始导入数据...")
        
        # --- A. 导入/创建用户 ---
        user_map = {} # username -> user_id 的映射
        
        for username in data.get("users", []):
            # 检查用户是否存在
            existing_user = session.exec(select(User).where(User.username == username)).first()
            if not existing_user:
                new_user = User(
                    username=username, 
                    password_hash=pwd_context.hash("123456") # 默认密码 123456
                )
                session.add(new_user)
                session.commit()
                session.refresh(new_user)
                user_map[username] = new_user.id
                print(f"   👤 创建用户: {username}")
            else:
                user_map[username] = existing_user.id

        # --- B. 导入日记 ---
        for item in data.get("diaries", []):
            author_id = user_map.get(item["username"])
            if not author_id:
                print(f"   ⚠️ 跳过日记，找不到用户: {item['username']}")
                continue

            # 创建日记
            diary = Diary(
                user_id=author_id,
                spot_id=item["spot_id"],
                title=item["title"],
                content=item["content"],
                score=item.get("score", 5.0),
                view_count=item.get("view_count", 0),
                media_json="[]" # 暂时留空
            )
            session.add(diary)
            session.commit()
            session.refresh(diary)
            print(f"   📝 发布日记: {diary.title} (ID: {diary.id})")

            # --- C. 导入评论 ---
            for c in item.get("comments", []):
                commenter_id = user_map.get(c["username"])
                if not commenter_id:
                    continue # 如果评论者不存在，就跳过
                    
                comment = Comment(
                    user_id=commenter_id,
                    diary_id=diary.id,
                    content=c["content"],
                    score=c.get("score", 5.0)
                )
                session.add(comment)
            
            session.commit() # 提交评论

    print("✅ 所有数据导入完成！")

if __name__ == "__main__":
    import_mock_data()