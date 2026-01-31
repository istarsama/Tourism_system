
import sys
import os
import json
from loguru import logger

# 获取当前脚本所在的目录路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 将该目录添加到系统路径中，确保可以导入当前目录下的模块（如 apis, xhs_utils 等）
sys.path.append(current_dir)

# 导入小红书 API 封装类
from apis.xhs_pc_apis import XHS_Apis

def test_spider():
    """
    测试爬虫核心功能的函数
    尝试调用搜索接口并打印结果，用于验证环境配置是否正确
    """
    print("🚀 开始测试小红书爬虫...")
    
    # 尝试从环境变量读取 Cookie，如果没有则使用空字符串
    # 注意：小红书的大部分接口都需要有效的登录 Cookie 才能正常返回数据
    # 在 .env 文件中配置 COOKIES='' 即可
    cookies = os.getenv("COOKIES", "")
    if not cookies:
        print("⚠️ 警告: 未找到 COOKIES 环境变量，尝试使用空 Cookie 进行测试。")
        print("   如果失败，请在 .env 文件中填入有效的小红书 Cookie。")
    
    # 初始化爬虫 API 类实例
    spider = XHS_Apis()
    
    # 定义测试用的搜索关键词
    keyword = "广州塔"
    print(f"🔍 正在搜索关键词: {keyword}")
    
    try:
        # 调用搜索接口
        # query: 关键词
        # require_num: 需要获取的笔记数量（这里设为 1 用于快速测试）
        # cookies_str: 用户 Cookie
        success, msg, notes = spider.search_some_note(
            query=keyword, 
            require_num=1, 
            cookies_str=cookies
        )
        
        # 判断请求是否成功
        if success:
            print(f"✅ 搜索成功！获取到 {len(notes)} 条笔记。")
            # 如果有返回笔记数据，打印第一条的详细信息
            if notes:
                first_note = notes[0]
                # 使用 .get() 安全获取字段，防止字段缺失导致报错
                print(f"📝 笔记标题: {first_note.get('title', '无标题')}")
                print(f"👤 作者: {first_note.get('user', {}).get('nickname', '未知')}")
                print(f"🔗 ID: {first_note.get('id', '未知')}")
                # 打印部分 JSON 数据以便调试查看结构
                print(f"📄 完整数据片段: {json.dumps(first_note, ensure_ascii=False)[:200]}...")
            else:
                print("❓ 搜索成功但未返回任何笔记。")
        else:
            # 如果请求失败，打印错误信息
            print(f"❌ 搜索失败: {msg}")
            # 根据错误信息给出智能提示
            if "Node" in str(msg) or "execjs" in str(msg):
                print("💡 提示: 请检查 Node.js 是否安装正确。爬虫依赖 Node.js 执行 JS 签名。")
            elif "登录" in str(msg) or "cookie" in str(msg).lower():
                print("💡 提示: 可能需要有效的 Cookie 才能搜索。请在 .env 文件中更新 COOKIES。")
                
    except Exception as e:
        # 捕获并打印所有未预期的异常
        print(f"❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 如果作为主程序运行，则执行测试函数
    test_spider()
