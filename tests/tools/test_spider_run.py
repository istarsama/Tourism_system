import sys
import os
from dotenv import load_dotenv

# 1. 确保能导入 src 下的模块
# 将 src 目录加入到 Python 搜索路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "..", "..")
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from crawler import XHSCrawler
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("   请确保你是在项目根目录下运行此脚本，且 src/crawler.py 存在。")
    sys.exit(1)

def main():
    print("🕷️ [爬虫集成测试] 正在启动...")
    
    # 2. 检查 Cookie 是否配置
    load_dotenv()
    cookie = os.getenv("XHS_COOKIE")
    if not cookie:
        print("⚠️  警告: .env 中未检测到 'XHS_COOKIE'！")
        print("   >>> 爬虫将无法连接小红书，可能会返回 Mock (模拟) 数据。")
    else:
        print("✅ 检测到 Cookie 配置，准备进行真实爬取...")

    # 3. 初始化爬虫
    crawler = XHSCrawler()
    
    # 4. 执行搜索
    # 关键词建议选一个不容易变的热门词，比如 "故宫" 或 "北京邮电大学"
    keyword = "北京邮电大学"
    limit_count = 3
    
    print(f"\n🔍 正在搜索关键词: 【{keyword}】 (获取 {limit_count} 条)...")
    print("   (这可能需要几秒钟，请耐心等待...)\n")
    
    try:
        results = crawler.search_notes(keyword, limit=limit_count)
        
        # 5. 打印结果
        if not results:
            print("❌ 未获取到任何数据。请检查网络或 Cookie 是否过期。")
            return

        print(f"✅ 成功获取 {len(results)} 条笔记！数据结构预览：\n")
        print("=" * 50)
        
        for i, note in enumerate(results):
            print(f"📄 笔记 #{i+1}")
            print(f"   🆔 ID:   {note.get('note_id')}")
            print(f"   📌 标题: {note.get('title')}")
            print(f"   👤 作者: {note.get('user', {}).get('nickname')}")
            print(f"   ❤️ 点赞: {note.get('likes')}")
            print(f"   🖼️ 图片: {len(note.get('images', []))} 张")
            # 打印前50个字的描述
            desc = note.get('desc', '').replace('\n', ' ')
            print(f"   📝 摘要: {desc[:50]}...")
            print("-" * 50)
            
        print("\n🎉 测试通过！Crawler 模块工作正常。")
        print("   数据已准备好，随时可以调用 save_to_db() 存入数据库。")

    except Exception as e:
        print(f"\n❌ 运行时发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()