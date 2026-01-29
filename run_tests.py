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
TOOLS_DIR = "tools"
TEST_TOOLS_DIR = "tests/tools"

# 定义菜单： (显示名称, 文件路径, 描述)
MENU_ITEMS = [
    # 业务测试
    ("1", "注册测试", "tests/test_register.py", "测试用户注册流程"),
    ("2", "登录测试", "tests/test_login.py", "测试用户登录 & Token 获取"),
    ("3", "导航测试", "tests/test_nav.py", "测试最短路径算法 & 地图坐标"),
    ("4", "搜索测试", "tests/test_search.py", "测试地点模糊搜索"),
    ("5", "评论流程", "tests/test_comment.py", "测试发表评论与打分"),
    ("6", "业务流测试", "tests/test_flow.py", "模拟用户完整操作流"),
    ("7", "AI 闲聊", "tests/test_ai.py", "测试 AI 助手基础对话"),
    ("8", "AI RAG", "tests/test_rag.py", "测试 AI 结合地图知识库"),
    
    # 数据库工具
    ("d", "查看数据库", "tools/view_database.py", "查看数据库中的用户/日记/评论"),
    ("s", "查看景点", "tests/tools/check_ids.py", "查看所有景点ID和坐标"),
    ("t", "查看表结构", "tests/tools/check_table_structure.py", "查看数据库表结构"),
    ("u", "升级数据库", "tests/tools/upgrade_database.py", "升级数据库表结构"),
    
    # 爬虫工具
    ("c", "爬取数据", "tools/import_crawled_data.py", "从小红书爬取并导入数据"),
    ("w", "测试爬虫", "tests/tools/test_spider_run.py", "测试爬虫连接"),
    ("l", "测试长度", "tests/tools/test_data_length.py", "测试数据长度控制"),
    
    # 批量测试
    ("a", "运行全部", "ALL_TESTS", "运行所有业务测试"),
]

def run_script(filepath):
    """运行指定的 Python 脚本"""
    if not os.path.exists(filepath):
        console.print(f"[bold red]❌ 错误：找不到文件 {filepath}[/bold red]")
        input("按 Enter 键返回主菜单...")
        return

    console.print(f"\n[bold green]🚀 正在启动 {os.path.basename(filepath)}...[/bold green]")
    console.print("[dim]" + "="*60 + "[/dim]")
    
    try:
        cmd = ["uv", "run", filepath]
        subprocess.run(cmd, check=False) 
    except Exception as e:
        console.print(f"[bold red]运行出错: {e}[/bold red]")
    
    console.print("[dim]" + "="*60 + "[/dim]")
    console.print(f"[bold green]✅ 运行结束[/bold green]\n")
    input("按 Enter 键返回主菜单...")

def run_all_tests():
    """运行所有业务测试"""
    test_files = [
        "tests/test_register.py",
        "tests/test_login.py",
        "tests/test_nav.py",
        "tests/test_search.py",
        "tests/test_comment.py",
        "tests/test_ai.py",
        "tests/test_flow.py",
    ]
    
    passed = 0
    failed = 0
    
    console.print("\n[bold cyan]" + "="*60 + "[/bold cyan]")
    console.print("[bold cyan]🧪 运行所有业务测试[/bold cyan]")
    console.print("[bold cyan]" + "="*60 + "[/bold cyan]\n")
    
    for test_file in test_files:
        if os.path.exists(test_file):
            console.print(f"\n[yellow]▶ 运行: {test_file}[/yellow]")
            try:
                result = subprocess.run(["uv", "run", test_file], check=False)
                if result.returncode == 0:
                    console.print(f"[green]✅ {test_file} - 通过[/green]")
                    passed += 1
                else:
                    console.print(f"[red]❌ {test_file} - 失败[/red]")
                    failed += 1
            except Exception as e:
                console.print(f"[red]❌ {test_file} - 异常: {e}[/red]")
                failed += 1
        else:
            console.print(f"[red]⚠️ 跳过: {test_file} (文件不存在)[/red]")
    
    console.print(f"\n[bold]{'='*60}[/bold]")
    console.print(f"[bold]测试总结: 通过 {passed}, 失败 {failed}, 总计 {passed+failed}[/bold]")
    console.print(f"[bold]{'='*60}[/bold]\n")
    input("按 Enter 键返回主菜单...")

def show_menu():
    """显示漂亮的菜单"""
    table = Table(title="🛠️  校园旅游系统 - 统一测试与工具平台")
    table.add_column("ID", style="cyan", justify="center", width=4)
    table.add_column("功能", style="magenta", width=12)
    table.add_column("说明", style="white")

    # 分组显示
    console.print("\n[bold cyan]📋 业务测试[/bold cyan]")
    business_tests = [item for item in MENU_ITEMS if item[2].startswith("tests/test_")]
    for idx, name, file, desc in business_tests:
        table.add_row(idx, name, desc)
    
    console.print(table)
    
    # 工具命令单独显示
    console.print("\n[bold green]🔧 数据库工具[/bold green]")
    console.print("  [cyan]d[/cyan] - 查看数据库  [cyan]s[/cyan] - 查看景点  [cyan]t[/cyan] - 查看表结构  [cyan]u[/cyan] - 升级数据库")
    
    console.print("\n[bold yellow]🕷️  爬虫工具[/bold yellow]")
    console.print("  [cyan]c[/cyan] - 爬取数据  [cyan]w[/cyan] - 测试爬虫  [cyan]l[/cyan] - 测试长度")
    
    console.print("\n[bold magenta]🚀 批量操作[/bold magenta]")
    console.print("  [cyan]a[/cyan] - 运行全部测试")
    
    console.print("\n[dim]输入 'q' 或 '0' 退出[/dim]")

def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        show_menu()
        choice = input("\n👉 请输入功能 ID: ").strip().lower()

        if choice in ['q', '0', 'exit']:
            console.print("[bold yellow]👋 再见！[/bold yellow]")
            break
        
        # 特殊命令：运行全部测试
        if choice == 'a':
            run_all_tests()
            continue
            
        selected = next((item for item in MENU_ITEMS if item[0] == choice), None)
        
        if selected:
            if selected[2] == "ALL_TESTS":
                run_all_tests()
            else:
                run_script(selected[2])
        else:
            console.print("[red]⚠️  输入无效，请重新选择[/red]")
            import time
            time.sleep(1)

if __name__ == "__main__":
    main()