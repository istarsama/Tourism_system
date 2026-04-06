---
name: xhs-spider
description: 小红书景点帖子爬取工具。当用户需要搜索小红书赏花/景点帖子、爬取 XHS 笔记数据、或为景点添加小红书贴子时，使用此 Skill。
allowed-tools: shell
---

# XHS Spider Skill — 小红书景点爬虫

## 概述

本 Skill 封装了项目内置的 `Spider_XHS` 爬虫工具，允许 Copilot 直接搜索小红书景点帖子，获取帖子标题、缩略图、预览文字和跳转链接。

**适用场景：**
- 为景点数据库添加小红书帖子数据
- 批量爬取赏花景点的小红书笔记
- 验证 XHS Cookie 是否有效

---

## 使用方式

### 基本搜索命令

在项目根目录执行：

```bash
# 搜索景点帖子（可读格式）
uv run python .github/skills/xhs-spider/xhs_search.py "景点名称 赏花" --limit 5

# 搜索并以 JSON 格式输出（适合程序解析）
uv run python .github/skills/xhs-spider/xhs_search.py "望京海棠花溪" --limit 5 --json

# 示例搜索
uv run python .github/skills/xhs-spider/xhs_search.py "故宫博物院 春季赏花" --limit 3 --json
uv run python .github/skills/xhs-spider/xhs_search.py "武汉大学樱花" --limit 5 --json
uv run python .github/skills/xhs-spider/xhs_search.py "洛阳牡丹" --limit 5 --json
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `keyword` | 搜索关键词（必填），建议加上"赏花"等主题词 | — |
| `--limit N` | 最大爬取数量（1-20） | 5 |
| `--json` | 输出 JSON 格式（适合管道/程序处理） | 否 |

### JSON 输出格式

```json
{
  "success": true,
  "keyword": "望京海棠花溪",
  "count": 5,
  "notes": [
    {
      "note_id": "xxx",
      "title": "帖子标题",
      "content_preview": "帖子正文预览（前200字）",
      "thumbnail_url": "https://sns-webpic-qc.xhscdn.com/...",
      "xhs_url": "https://www.xiaohongshu.com/explore/xxx",
      "author_name": "作者昵称",
      "author_id": "用户ID",
      "likes": 1234,
      "images": ["图片URL列表"]
    }
  ]
}
```

---

## Cookie 配置

XHS 爬虫需要有效的登录 Cookie。Cookie 存储在项目根目录 `.env` 文件中：

```env
XHS_COOKIE=your_cookie_string_here
```

### 获取 Cookie 步骤

1. 用浏览器打开 [小红书](https://www.xiaohongshu.com) 并登录
2. 按 `F12` 打开开发者工具 → 切换到 **网络(Network)** 面板
3. 刷新页面，点击任意请求
4. 在请求头中找到 `Cookie:` 字段，复制完整值
5. 将 Cookie 写入 `.env` 文件的 `XHS_COOKIE=` 后面

### Cookie 失效处理

当爬虫返回以下错误时，表示 Cookie 已过期：

```
❌ Cookie 失效: ...
请更新 .env 中的 XHS_COOKIE。
```

**解决方法：** 重新从浏览器复制 Cookie 并更新 `.env`。

---

## 退出码说明

| 退出码 | 含义 |
|--------|------|
| `0` | 搜索成功 |
| `1` | Cookie 失效或未配置 |
| `2` | 爬虫模块加载失败（依赖未安装） |
| `3` | 其他运行错误 |

---

## 依赖要求

- Python 3.10+（通过 `uv run` 调用）
- `src/tools/Spider_XHS/` 目录存在（项目已内置）
- Node.js 18+（Spider_XHS 内部使用）
- `python-dotenv`, `loguru`, `retry`, `openpyxl`, `requests`（在 `requirements.txt` 中）

---

## 最佳实践

1. **关键词加主题词**：`"故宫博物院 赏花"` 比 `"故宫"` 更精准
2. **限制数量**：每次 5-10 条，避免频率过高被封
3. **批量搜索**：为多个景点搜索时，每次搜索间隔 2-3 秒
4. **错误处理**：搜索前先检查退出码（`$LASTEXITCODE` 或 `$?`）

---

## 工作流示例

当用户请求"帮我搜索武汉的赏花景点小红书帖子"时：

```bash
# 1. 先验证 Cookie 是否有效（小搜索）
uv run python .github/skills/xhs-spider/xhs_search.py "武汉赏花" --limit 1 --json

# 2. 如成功（exit code 0），批量搜索各景点
uv run python .github/skills/xhs-spider/xhs_search.py "武汉大学樱花" --limit 5 --json
uv run python .github/skills/xhs-spider/xhs_search.py "武汉东湖磨山梅花" --limit 5 --json
uv run python .github/skills/xhs-spider/xhs_search.py "武汉植物园" --limit 5 --json

# 3. 将结果导入数据库
uv run python tools/crawl_flower_spots.py --city 武汉
```
