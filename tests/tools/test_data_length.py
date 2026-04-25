import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
tools_path = os.path.join(project_root, "tools")
if tools_path not in sys.path:
    sys.path.insert(0, tools_path)

from import_crawled_data import clean_and_format_note


def test_clean_and_format_note_limits():
    test_note = {
        "title": "这是一个非常非常非常长的标题" * 30,
        "desc": "这是正文内容，包含了很多很多很多的文字描述，模拟小红书的长篇笔记..." * 200,
        "user": {"nickname": "测试用户名字很长的博主" * 10},
        "likes": 12345,
        "images": ["img1.jpg", "img2.jpg"],
        "note_id": "test123",
    }

    cleaned = clean_and_format_note(test_note)

    content_parts = [
        f"原作者: {cleaned['author']}",
        f"点赞数: {cleaned['likes']}",
        "",
        cleaned["content"],
    ]
    if cleaned["note_id"]:
        content_parts.append(f"\n原文: https://www.xiaohongshu.com/explore/{cleaned['note_id']}")

    full_content = "\n".join(content_parts)
    full_title = f"[搬运] {cleaned['title']}"

    assert len(cleaned["title"]) <= 400
    assert len(cleaned["content"]) <= 5000
    assert len(cleaned["author"]) <= 100
    assert len(full_title) <= 500
    assert len(full_content) <= 65535
