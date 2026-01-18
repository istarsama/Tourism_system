import os
import sys
import subprocess
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 如果你还没装 rich，可以运行 uv add rich，或者把下面用到 rich 的地方改成普通 print
# 这里为了好看，我假设你愿意装个 rich (uv add rich)

try:
    from rich import print
    console = Console()
except ImportError:
    print("建议安装 rich 库以获得更好体验: uv add rich")
    # 简易版兼容
    class MockConsole:
        def print(self, *args, **kwargs): __builtins__.print(*args)
    console = MockConsole()

TEST_DIR = "tests"

# 定义测试菜单： (显示名称, 文件名, 描述)
MENU_ITEMS = [
    ("1", "注册测试", "test_register.py", "测试用户注册流程 (User Registration)"),
    ("2", "登录测试", "test_login.py", "测试用户登录 & Token 获取 (Login & Auth)"),
    ("3", "导航测试", "test_nav.py", "测试最短路径算法 & 地图坐标 (Navigation)"),
    ("4", "搜索测试", "test_search.py", "测试地点模糊搜索 (Fuzzy Search)"),
    ("5", "评论流程", "test_comment.py", "测试发表评论与打分 (Comments)"),
    ("6", "业务流测试", "test_flow.py", "模拟用户完整操作流 (Full Workflow)"),
    ("7", "AI 闲聊", "test_ai.py", "测试 AI 助手基础对话 (LLM Chat)"),
    ("8", "AI RAG", "test_rag.py", "测试 AI 结合地图知识库 (RAG Knowledge)"),
]

def run_script(filename):
    """运行指定的 Python 脚本"""
    filepath = os.path.join(TEST_DIR, filename)
    if not os.path.exists(filepath):
        console.print(f"[bold red]❌ 错误：找不到文件 {filepath}[/bold red]")
        return

    console.print(f"\n[bold green]🚀 正在启动 {filename}...[/bold green]")
    console.print("[dim]----------------------------------------[/dim]")
    
    # 使用 uv run 来运行，确保环境一致
    try:
        # 兼容 Windows/Linux
        cmd = ["uv", "run", filepath]
        subprocess.run(cmd, check=False) 
    except Exception as e:
        console.print(f"[bold red]运行出错: {e}[/bold red]")
    
    console.print("[dim]----------------------------------------[/dim]")
    console.print(f"[bold green]✅ {filename} 运行结束[/bold green]\n")
    input("按 Enter 键返回主菜单...")

def show_menu():
    """显示漂亮的菜单"""
    table = Table(title="🛠️  校园旅游系统 - 超级测试工具箱")
    table.add_column("ID", style="cyan", justify="center")
    table.add_column("功能名称", style="magenta")
    table.add_column("脚本文件", style="green")
    table.add_column("功能描述", style="white")

    for idx, name, file, desc in MENU_ITEMS:
        table.add_row(idx, name, file, desc)

    console.print(table)
    console.print("\n[dim]输入 'q' 或 '0' 退出[/dim]")

def main():
    while True:
        # 清屏 (兼容 Windows/Mac/Linux)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        show_menu()
        choice = input("\n👉 请输入功能 ID: ").strip()

        if choice in ['q', 'Q', '0', 'exit']:
            console.print("[bold yellow]👋 再见！[/bold yellow]")
            break
            
        selected = next((item for item in MENU_ITEMS if item[0] == choice), None)
        
        if selected:
            run_script(selected[2])
        else:
            console.print("[red]⚠️  输入无效，请重新选择[/red]")
            import time
            time.sleep(1)

if __name__ == "__main__":
    main()