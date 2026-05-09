"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕷️ 小红书爬虫数据整合导入工具 (Crawler Data Integration Tool)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【功能说明】
从小红书爬取笔记数据，经过智能处理后导入到旅游系统数据库。

【核心功能】
1. 🔍 数据爬取 - 从小红书API爬取笔记内容
2. 🧹 数据清洗 - 格式化内容，控制长度，提取关键信息
3. 🎯 智能匹配 - 根据关键词自动匹配景点ID（模糊匹配算法）
4. 🗑️ 去重处理 - 避免重复导入相同数据
5. 💾 数据库存储 - 保存为系统日记，供AI RAG检索

【使用方式】
1. 交互式: uv run tools/import_crawled_data.py
2. 批量模式: uv run tools/import_crawled_data.py "关键词1" "关键词2"
3. 菜单入口: uv run python run_tests.py → 输入 c

【技术栈】
- 爬虫：Spider_XHS模块（小红书API封装）
- 匹配：thefuzz模糊匹配算法（Levenshtein距离）
- 数据库：SQLModel + MySQL
- 认证：Cookie机制（从.env读取）

【数据流】
小红书 → 爬虫API → 数据清洗 → 景点匹配 → 去重检查 → MySQL → AI RAG

【注意事项】
1. 需要在.env中配置 XHS_COOKIE
2. Cookie有效期7-30天，过期需重新获取
3. 推荐关键词：北邮食堂、图书馆自习、北邮校园
4. 所有爬虫数据统一使用 spider_bot 账号（ID: 5）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import sys
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from sqlmodel import Session, select

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📦 模块导入和路径配置
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 1. 环境准备 - 添加 src 目录到 Python 路径
# 原因：需要导入 crawler, database, models 等自定义模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "..")
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 2. 导入自定义模块
from crawler import XHSCrawler          # 小红书爬虫封装类
from database import engine             # 数据库引擎
from models import User, Diary          # 数据模型
from auth import get_password_hash      # 密码哈希工具

# 3. 导入工具函数
from utils import load_graph_from_json, get_data_path  # 景点数据加载

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🤖 爬虫账号管理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_or_create_spider_user(session: Session):
    """
    获取或创建爬虫专用账号 (spider_bot)
    
    【功能说明】
    为所有爬虫导入的数据创建一个统一的虚拟用户账号，便于管理和追踪。
    
    【账号信息】
    - 用户名: spider_bot
    - 密码: spider123 (已哈希)
    - 用途: 标识所有从小红书爬取的日记
    - 固定ID: 5 (自动生成)
    
    【设计原因】
    1. 区分真实用户和爬虫数据
    2. 便于统计和管理爬虫内容
    3. 防止混淆数据来源
    4. 支持后续的数据清理和更新
    
    参数:
        session: 数据库会话
    
    返回:
        User: 爬虫账号对象
    """
    # 查询数据库中是否已存在 spider_bot 账号
    user = session.exec(select(User).where(User.username == "spider_bot")).first()
    
    if not user:
        # 不存在则创建新账号
        print("🤖 创建爬虫搬运工账号 'spider_bot'...")
        user = User(
            username="spider_bot", 
            password_hash=get_password_hash("spider123")
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    
    return user

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🗺️ 景点数据管理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_spots():
    """
    从配置文件加载所有景点数据
    
    【功能说明】
    读取 data/campus_map.json 中的景点信息，构建景点字典供匹配使用。
    
    【数据结构】
    返回格式: {spot_id: Spot对象}
    例如: {
        44: Spot(id=44, name="学生食堂", type="spot"),
        57: Spot(id=57, name="图书馆", type="spot"),
        ...
    }
    
    【过滤规则】
    只加载 type="spot" 的景点，排除道路、建筑等其他类型节点。
    
    返回:
        dict: {景点ID: 景点对象} 的字典
    """
    try:
        # 从 JSON 文件加载校园地图数据
        graph = load_graph_from_json(get_data_path())
        
        # 筛选出所有景点（排除道路等节点）
        spots = {spot.id: spot for spot in graph.spots.values() if spot.type == "spot"}
        
        return spots
    except Exception as e:
        print(f"⚠️ 加载景点数据失败: {e}")
        return {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 智能景点匹配算法
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def find_spot_by_keyword(keyword: str, spots: dict):
    """
    根据用户输入的关键词智能匹配对应景点
    
    【功能说明】
    使用两级匹配策略，优先精确匹配，其次模糊匹配。
    
    【匹配策略】
    1. 精确匹配 - 关键词包含景点名或景点名包含关键词
       例如: "北邮食堂" 包含 "食堂" → 匹配成功
    
    2. 模糊匹配 - 使用 Levenshtein 距离算法（编辑距离）
       算法: thefuzz.fuzz.partial_ratio()
       阈值: 相似度 > 60% 认为匹配成功
       
    【匹配示例】
    | 关键词 | 匹配景点 | 相似度 | 策略 |
    |--------|----------|--------|------|
    | "北邮食堂" | 学生食堂 | 85% | 模糊 |
    | "图书馆自习" | 图书馆 | 90% | 模糊 |
    | "食堂" | 学生食堂 | 100% | 精确 |
    | "星塔" | 北邮星塔 | 100% | 精确 |
    
    【算法原理】
    Levenshtein Distance（莱文斯坦距离）:
    计算两个字符串之间需要多少次插入、删除、替换操作才能相互转换。
    距离越小，相似度越高。
    
    参数:
        keyword: 用户输入的搜索关键词
        spots: 景点字典 {id: Spot对象}
    
    返回:
        Spot: 匹配到的景点对象，未匹配返回 None
    """
    keyword_lower = keyword.lower()
    
    # ━━━ 第一轮: 精确匹配 ━━━
    # 检查关键词和景点名是否互相包含
    for spot_id, spot in spots.items():
        if keyword in spot.name or spot.name in keyword:
            return spot
    
    # ━━━ 第二轮: 模糊匹配 ━━━
    # 使用 thefuzz 库计算相似度
    from thefuzz import fuzz
    
    best_match = None    # 最佳匹配的景点
    best_score = 0       # 最高相似度分数
    
    # 遍历所有景点，计算相似度
    for spot_id, spot in spots.items():
        # partial_ratio: 部分匹配算法，处理长度不等的字符串
        score = fuzz.partial_ratio(keyword, spot.name)
        if score > best_score:
            best_score = score
            best_match = spot
    
    # 判断是否达到匹配阈值（60%）
    if best_score > 60:
        print(f"   🎯 智能匹配到景点: {best_match.name} (相似度: {best_score}%)")
        return best_match
    
    # 未找到匹配
    return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧹 数据清洗与格式化
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def clean_and_format_note(note: dict) -> dict:
    """
    清洗和格式化从小红书爬取的笔记数据
    
    【功能说明】
    对原始JSON数据进行规范化处理，确保符合数据库字段要求。
    
    【处理流程】
    1. 提取核心字段（标题、内容、作者）
    2. 长度控制（防止超出数据库限制）
    3. 截断超长部分并添加省略号
    4. 返回标准化的字典数据
    
    【长度限制】
    - 标题: 400字符（数据库VARCHAR(500)，留100字余量）
    - 内容: 5000字符（数据库TEXT类型支持65K，但避免过长）
    - 作者: 100字符
    - 图片: 最多9张
    
    【数据库升级背景】
    - 原来: content VARCHAR(255) ❌ 太短，导入失败
    - 现在: content TEXT ✅ 支持65K字符，足够存储完整笔记
    
    参数:
        note: 原始笔记数据字典
    
    返回:
        dict: 清洗后的标准化数据
    """
    # 1. 从原始数据中提取字段
    title = note.get('title', '无标题').strip()
    content = note.get('desc', '').strip()
    user_info = note.get('user') if isinstance(note.get('user'), dict) else {}
    author = user_info.get('nickname', '未知用户')
    raw_likes = note.get('likes', 0)
    try:
        likes = int(raw_likes)
    except (TypeError, ValueError):
        likes = 0
    
    # 2. 标题长度控制（最多400字符，留余量）
    if len(title) > 400:
        title = title[:397] + '...'  # 截断并添加省略号
    
    # 3. 内容长度控制（最多5000字符）
    # 虽然TEXT类型支持更长，但避免单条数据过大
    if len(content) > 5000:
        content = content[:4997] + '...'  # 截断并添加省略号
    
    # 4. 返回标准化数据
    return {
        'title': title,
        'content': content,
        'author': author[:100],  # 作者名最多100字符
        'likes': likes,
        'images': note.get('images', [])[:9],  # 最多保留9张图片
        'note_id': note.get('note_id', ''),
        'note_url': note.get('note_url', ''),
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 💾 数据库存储
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def save_notes_to_db(notes: list, session: Session, user_id: int, spot_id: int, keyword: str):
    """
    批量保存爬取的笔记数据到MySQL数据库
    
    【功能说明】
    将清洗后的笔记数据转换为 Diary 模型并存入数据库，同时处理去重和错误。
    
    【处理流程】
    1. 数据清洗 - 调用 clean_and_format_note()
    2. 去重检查 - 通过标题判断是否已存在
    3. 内容构建 - 添加作者、点赞、原文链接等信息
    4. 创建记录 - 生成 Diary 对象
    5. 批量提交 - 保存到数据库
    6. 错误处理 - 单条失败不影响其他数据
    
    【去重策略】
    通过标题去重，标题格式: "[搬运] 原标题"
    相同标题认为是重复数据，自动跳过。
    
    【Diary表字段映射】
    | 字段 | 来源 | 说明 |
    |------|------|------|
    | user_id | 参数 | 固定使用spider_bot (ID: 5) |
    | spot_id | 参数 | 智能匹配的景点ID |
    | title | 笔记标题 | 添加[搬运]前缀标记 |
    | content | 笔记内容 | 包含作者、点赞、正文、链接 |
    | view_count | 点赞数 | 用小红书点赞数作为初始浏览量 |
    | media_json | 图片列表 | JSON数组格式存储 |
    | score | 固定4.0 | 默认评分（可后续调整）|
    | created_at | 当前时间 | 导入时间 |
    
    【内容格式示例】
    ```
    👤 原作者: 美食博主小王
    ❤️ 点赞数: 1234
    
    今天去学一食堂吃了红烧肉，真的太好吃了！
    窗口在二楼，价格也很实惠...
    
    🔗 原文: https://www.xiaohongshu.com/explore/abc123
    ```
    
    参数:
        notes: 清洗后的笔记数据列表
        session: 数据库会话
        user_id: 用户ID（spider_bot账号）
        spot_id: 景点ID（智能匹配结果）
        keyword: 搜索关键词（用于日志）
    
    返回:
        int: 成功导入的数量
    """
    if not notes:
        print("❌ 没有数据可以保存")
        return 0
    
    success_count = 0
    error_count = 0
    
    print(f"\n📝 开始写入数据库...")
    print(f"   关键词: {keyword}")
    print(f"   景点ID: {spot_id}")
    print(f"   数据量: {len(notes)} 条")
    print("-" * 60)
    
    for i, note in enumerate(notes, 1):
        try:
            # 清洗数据
            cleaned = clean_and_format_note(note)
            
            # 检查是否已存在（通过标题去重）
            existing = session.exec(
                select(Diary).where(
                    Diary.title == f"[搬运] {cleaned['title']}"
                )
            ).first()
            
            if existing:
                print(f"   ⏭️  {i}. 跳过重复: {cleaned['title'][:30]}...")
                continue
            
            # 构建日记内容（现在可以保存完整内容了）
            content_parts = [
                f"👤 原作者: {cleaned['author']}",
                f"❤️ 点赞数: {cleaned['likes']}",
                "",
                cleaned['content']
            ]
            
            source_url = cleaned['note_url']
            if not source_url and cleaned['note_id']:
                source_url = f"https://www.xiaohongshu.com/explore/{cleaned['note_id']}"
            if source_url:
                content_parts.append(f"\n🔗 原文: {source_url}")
            
            content = "\n".join(content_parts)
            
            # 创建日记
            new_diary = Diary(
                user_id=user_id,
                spot_id=spot_id,
                title=f"[搬运] {cleaned['title']}",
                content=content,
                view_count=cleaned['likes'],  # 用点赞数作为初始浏览量
                media_json=json.dumps(cleaned['images']),
                score=4.0,  # 默认评分
                created_at=datetime.now()
            )
            
            session.add(new_diary)
            session.commit()
            session.refresh(new_diary)
            
            print(f"   ✅ {i}. 成功导入: {cleaned['title'][:30]}... (ID: {new_diary.id})")
            success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"   ❌ {i}. 导入失败: {str(e)[:50]}")
            session.rollback()
            continue
    
    print("-" * 60)
    print(f"✅ 导入完成: 成功 {success_count} 条, 失败 {error_count} 条\n")
    return success_count

def interactive_mode():
    """
    交互式模式：引导用户一步步导入数据
    """
    print("\n" + "="*60)
    print("🕷️  小红书数据爬取与导入工具")
    print("="*60)
    
    # 1. 检查环境
    load_dotenv()
    cookie = os.getenv("XHS_COOKIE")
    if not cookie:
        print("\n❌ 错误: 未在 .env 文件中找到 XHS_COOKIE")
        print("请按以下步骤配置:")
        print("1. 在浏览器中登录小红书 (xiaohongshu.com)")
        print("2. 按 F12 打开开发者工具")
        print("3. 切换到 Network 标签")
        print("4. 刷新页面，找到任意请求")
        print("5. 复制 Cookie 字段的完整内容")
        print("6. 在 .env 文件中添加: XHS_COOKIE='你的cookie内容'\n")
        return
    
    print("✅ Cookie 配置已检测到")
    
    # 2. 加载景点数据
    spots = load_spots()
    if spots:
        print(f"✅ 已加载 {len(spots)} 个景点数据")
    
    # 3. 初始化爬虫
    crawler = XHSCrawler()
    
    # 4. 用户输入
    print("\n" + "-"*60)
    keyword = input("📌 请输入搜索关键词（如 '北邮食堂' '图书馆自习'）: ").strip()
    if not keyword:
        print("❌ 关键词不能为空")
        return
    
    # 5. 智能匹配景点
    spot = find_spot_by_keyword(keyword, spots)
    spot_id = 0
    
    if spot:
        confirm = input(f"   是否绑定到该景点？(Y/n): ").strip().lower()
        if confirm != 'n':
            spot_id = spot.id
            print(f"   ✅ 已绑定到: {spot.name} (ID: {spot_id})")
    else:
        print("   ⚠️  未找到匹配的景点，将作为独立日记保存")
        manual_id = input("   如需手动指定景点ID，请输入（直接回车跳过）: ").strip()
        if manual_id.isdigit():
            spot_id = int(manual_id)
    
    # 6. 爬取数量
    count_input = input("📊 爬取数量（默认5条，最多20条）: ").strip()
    limit = int(count_input) if count_input.isdigit() else 5
    limit = min(limit, 20)  # 限制最大数量
    
    # 7. 开始爬取
    print(f"\n🚀 开始从小红书爬取关键词【{keyword}】的笔记...")
    print("   (这可能需要10-30秒，请耐心等待...)\n")
    
    try:
        notes = crawler.search_notes(keyword, limit=limit)
        
        if not notes:
            print("❌ 未能获取到数据，可能原因:")
            print("   1. Cookie 已过期，请重新获取")
            print("   2. 网络连接问题")
            print("   3. 小红书接口变动")
            return
        
        print(f"✅ 成功爬取 {len(notes)} 条笔记")
        
        # 8. 预览数据
        print("\n📄 数据预览:")
        print("-" * 60)
        for i, note in enumerate(notes[:3], 1):  # 只预览前3条
            print(f"{i}. {note.get('title', '无标题')}")
            print(f"   作者: {note.get('user', {}).get('nickname', '未知')} | 点赞: {note.get('likes', 0)}")
        if len(notes) > 3:
            print(f"... 还有 {len(notes) - 3} 条")
        print("-" * 60)
        
        # 9. 确认导入
        confirm = input("\n是否导入到数据库？(Y/n): ").strip().lower()
        if confirm == 'n':
            print("❌ 已取消导入")
            return
        
        # 10. 保存到数据库
        with Session(engine) as session:
            bot_user = get_or_create_spider_user(session)
            count = save_notes_to_db(notes, session, bot_user.id, spot_id, keyword)
            
            if count > 0:
                print("🎉 数据导入成功！")
                print(f"\n💡 提示: 现在你可以:")
                print(f"   1. 运行 'uv run view_database.py' 查看数据")
                print(f"   2. 启动后端问 AI: '{keyword}怎么样？'")
                print(f"   3. 查看景点ID={spot_id}的相关日记\n")
    
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

def batch_mode(keywords: list):
    """
    批量模式：自动爬取多个关键词
    """
    print("\n🚀 批量导入模式启动...")
    load_dotenv()
    
    if not os.getenv("XHS_COOKIE"):
        print("❌ 缺少 Cookie 配置")
        return
    
    crawler = XHSCrawler()
    spots = load_spots()
    
    total_imported = 0
    
    with Session(engine) as session:
        bot_user = get_or_create_spider_user(session)
        
        for keyword in keywords:
            print(f"\n{'='*60}")
            print(f"处理关键词: {keyword}")
            print(f"{'='*60}")
            
            # 智能匹配景点
            spot = find_spot_by_keyword(keyword, spots)
            spot_id = spot.id if spot else 0
            
            # 爬取
            notes = crawler.search_notes(keyword, limit=5)
            if notes:
                count = save_notes_to_db(notes, session, bot_user.id, spot_id, keyword)
                total_imported += count
    
    print(f"\n🎉 批量导入完成！共导入 {total_imported} 条数据")

def main():
    import sys
    
    if len(sys.argv) > 1:
        # 批量模式：python import_crawled_data.py "关键词1" "关键词2" ...
        keywords = sys.argv[1:]
        batch_mode(keywords)
    else:
        # 交互模式
        interactive_mode()

if __name__ == "__main__":
    main()
