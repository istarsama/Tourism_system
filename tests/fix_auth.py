from sqlmodel import Session, select, text
from src.database import engine
from src.models import User
from passlib.context import CryptContext

# 配置密码加密器
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def fix_user_auth():
    print("🚑 开始诊断与修复账户问题...")
    
    with Session(engine) as session:
        # 1. 查找问题用户
        username = "student_A"
        user = session.exec(select(User).where(User.username == username)).first()
        
        if user:
            print(f"🔍 发现用户 [{username}]")
            print(f"   当前数据库里的哈希值: {user.password_hash}")
            
            # 尝试校验（预计这里会报错）
            try:
                is_valid = pwd_context.verify("123456", user.password_hash)
                print(f"   ✅ 校验结果: {'通过' if is_valid else '失败'}")
            except Exception as e:
                print(f"   ❌ 校验时报错: {e}")
                print("   (这说明数据库里的数据确实损坏了)")

            # 2. 执行修复：直接更新密码
            print("\n🛠️  正在执行强制修复...")
            new_hash = pwd_context.hash("123456")
            user.password_hash = new_hash
            session.add(user)
            session.commit()
            print(f"   ✨ 密码已重置! 新哈希值: {new_hash}")
            
        else:
            print(f"⚠️ 用户 [{username}] 不存在，正在创建...")
            new_hash = pwd_context.hash("123456")
            new_user = User(username=username, password_hash=new_hash)
            session.add(new_user)
            session.commit()
            print(f"   ✨ 用户已创建! 哈希值: {new_hash}")

    # 3. 最终验证
    print("\n🔍 进行最终自检...")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "student_A")).first()
        try:
            if pwd_context.verify("123456", user.password_hash):
                print("✅✅✅ 修复成功！现在你可以正常登录了！")
            else:
                print("❌ 修复后依然校验失败，请检查环境。")
        except Exception as e:
            print(f"❌ 依然报错: {e}")

if __name__ == "__main__":
    fix_user_auth()