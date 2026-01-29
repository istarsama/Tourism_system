"""
数据库查看工具
用于快速查看 MySQL 数据库中的用户、日记和评论数据
"""
from sqlmodel import Session, select
from src.database import engine
from src.models import User, Diary, Comment

def view_all_data():
    print("\n" + "="*60)
    print("📊 校园旅游系统 - 数据库数据查看")
    print("="*60)
    
    with Session(engine) as session:
        # 1. 查看用户
        print("\n👥 用户列表 (User)")
        print("-" * 60)
        users = session.exec(select(User)).all()
        if users:
            print(f"{'ID':<5} | {'用户名':<15} | {'注册时间'}")
            print("-" * 60)
            for user in users:
                print(f"{user.id:<5} | {user.username:<15} | {user.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"\n共 {len(users)} 个用户")
        else:
            print("❌ 暂无用户数据")
        
        # 2. 查看日记统计
        print("\n" + "="*60)
        print("📝 日记列表 (Diary) - 最近10条")
        print("-" * 60)
        diaries = session.exec(
            select(Diary).order_by(Diary.created_at.desc()).limit(10)
        ).all()
        
        if diaries:
            print(f"{'ID':<5} | {'标题':<20} | {'景点ID':<7} | {'浏览':<6} | {'评分':<6} | {'作者ID'}")
            print("-" * 60)
            for diary in diaries:
                title = diary.title[:18] + '..' if len(diary.title) > 20 else diary.title
                print(f"{diary.id:<5} | {title:<20} | {diary.spot_id:<7} | {diary.view_count:<6} | {diary.score:<6.1f} | {diary.user_id}")
            
            # 统计信息
            total_diaries = session.exec(select(Diary)).all()
            total_views = sum(d.view_count for d in total_diaries)
            avg_score = sum(d.score for d in total_diaries) / len(total_diaries) if total_diaries else 0
            
            print(f"\n📈 统计: 共 {len(total_diaries)} 篇日记 | 总浏览量 {total_views} | 平均评分 {avg_score:.2f}")
        else:
            print("❌ 暂无日记数据")
        
        # 3. 查看评论
        print("\n" + "="*60)
        print("💬 评论列表 (Comment) - 最近10条")
        print("-" * 60)
        comments = session.exec(
            select(Comment).order_by(Comment.created_at.desc()).limit(10)
        ).all()
        
        if comments:
            print(f"{'ID':<5} | {'日记ID':<7} | {'评分':<6} | {'评论内容':<30} | {'用户ID'}")
            print("-" * 60)
            for comment in comments:
                content = comment.content[:28] + '..' if len(comment.content) > 30 else comment.content
                print(f"{comment.id:<5} | {comment.diary_id:<7} | {comment.score:<6.1f} | {content:<30} | {comment.user_id}")
            
            total_comments = session.exec(select(Comment)).all()
            print(f"\n💬 共 {len(total_comments)} 条评论")
        else:
            print("❌ 暂无评论数据")
    
    print("\n" + "="*60)
    print("✅ 数据加载完成")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        view_all_data()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n💡 提示:")
        print("1. 确保 MySQL 服务已启动")
        print("2. 检查 .env 文件中的 DATABASE_URL 配置")
        print("3. 运行 'uv run src/create_tables.py' 创建表")
        print("4. 运行 'uv run src/import_data.py' 导入数据\n")
