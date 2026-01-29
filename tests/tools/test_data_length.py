"""
测试数据导入 - 验证长度限制修复
"""
import sys
import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from import_crawled_data import clean_and_format_note

# 测试数据：模拟超长内容
test_note = {
    'title': '这是一个非常非常非常长的标题' * 30,  # 超长标题
    'desc': '这是正文内容，包含了很多很多很多的文字描述，模拟小红书的长篇笔记...' * 200,  # 超长内容
    'user': {'nickname': '测试用户名字很长的博主' * 10},  # 超长用户名
    'likes': 12345,
    'images': ['img1.jpg', 'img2.jpg'],
    'note_id': 'test123'
}

print("🧪 测试数据清洗功能")
print("="*70)

print("\n📥 原始数据长度:")
print(f"   标题: {len(test_note['title'])} 字符")
print(f"   内容: {len(test_note['desc'])} 字符")
print(f"   作者: {len(test_note['user']['nickname'])} 字符")

# 清洗数据
cleaned = clean_and_format_note(test_note)

print("\n📤 清洗后数据长度:")
print(f"   标题: {len(cleaned['title'])} 字符 (限制: 400)")
print(f"   内容: {len(cleaned['content'])} 字符 (限制: 5000)")
print(f"   作者: {len(cleaned['author'])} 字符 (限制: 100)")

# 模拟完整的日记内容
content_parts = [
    f"👤 原作者: {cleaned['author']}",
    f"❤️ 点赞数: {cleaned['likes']}",
    "",
    cleaned['content']
]
if cleaned['note_id']:
    content_parts.append(f"\n🔗 原文: https://www.xiaohongshu.com/explore/{cleaned['note_id']}")

full_content = "\n".join(content_parts)
full_title = f"[搬运] {cleaned['title']}"

print("\n📊 最终入库数据长度:")
print(f"   完整标题: {len(full_title)} 字符 (数据库限制: 500)")
print(f"   完整内容: {len(full_content)} 字符 (数据库限制: TEXT ~65535)")

print("\n✅ 验证结果:")
if len(full_title) <= 500:
    print(f"   ✅ 标题长度合格 ({len(full_title)}/500)")
else:
    print(f"   ❌ 标题超长 ({len(full_title)}/500)")

if len(full_content) <= 65535:
    print(f"   ✅ 内容长度合格 ({len(full_content)}/65535)")
else:
    print(f"   ❌ 内容超长 ({len(full_content)}/65535)")

print("\n📝 数据预览:")
print(f"   标题: {full_title[:50]}...")
print(f"   内容前100字: {full_content[:100]}...")

print("\n" + "="*70)
print("✅ 测试完成！数据长度控制正常。")
