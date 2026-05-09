import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPIDER_DIR = PROJECT_ROOT / "src" / "tools" / "Spider_XHS"


def load_spider_main():
    if str(SPIDER_DIR) not in sys.path:
        sys.path.insert(0, str(SPIDER_DIR))
    spec = importlib.util.spec_from_file_location("spider_xhs_main_test", SPIDER_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_spider_some_note_saves_media_and_excel(monkeypatch, tmp_path):
    module = load_spider_main()
    spider = module.Data_Spider()

    note_info = {
        "note_id": "note-1",
        "user_id": "user-1",
        "nickname": "测试作者",
        "title": "测试标题",
        "note_type": "图集",
        "image_list": ["https://example.com/image.jpg"],
    }
    download_calls = []
    excel_calls = []

    def fake_spider_note(note_url, cookies_str, proxies=None):
        return True, "ok", {**note_info, "note_url": note_url}

    def fake_download_note(note, path, save_choice):
        download_calls.append((note["note_id"], Path(path).name, save_choice))
        return str(Path(path) / note["note_id"])

    def fake_save_to_xlsx(datas, file_path, type="note"):
        excel_calls.append((len(datas), Path(file_path).name, type))

    monkeypatch.setattr(spider, "spider_note", fake_spider_note)
    monkeypatch.setattr(module, "download_note", fake_download_note)
    monkeypatch.setattr(module, "save_to_xlsx", fake_save_to_xlsx)

    result = spider.spider_some_note(
        ["https://www.xiaohongshu.com/explore/note-1?xsec_token=abc"],
        cookies_str="web_session=test",
        base_path={"media": str(tmp_path / "media"), "excel": str(tmp_path / "excel")},
        save_choice="all",
        excel_name="xhs_test",
    )

    assert result[0]["note_id"] == "note-1"
    assert download_calls == [("note-1", "media", "all")]
    assert excel_calls == [(1, "xhs_test.xlsx", "note")]


def test_spider_some_note_excel_only_does_not_download(monkeypatch, tmp_path):
    module = load_spider_main()
    spider = module.Data_Spider()

    def fake_spider_note(note_url, cookies_str, proxies=None):
        return True, "ok", {
            "note_id": "note-2",
            "user_id": "user-2",
            "nickname": "测试作者",
            "title": "测试标题",
            "note_type": "图集",
            "image_list": [],
        }

    download_calls = []
    excel_calls = []
    monkeypatch.setattr(spider, "spider_note", fake_spider_note)
    monkeypatch.setattr(module, "download_note", lambda *args, **kwargs: download_calls.append(args))
    monkeypatch.setattr(module, "save_to_xlsx", lambda datas, file_path, type="note": excel_calls.append(file_path))

    spider.spider_some_note(
        ["https://www.xiaohongshu.com/explore/note-2?xsec_token=abc"],
        cookies_str="web_session=test",
        base_path={"media": str(tmp_path / "media"), "excel": str(tmp_path / "excel")},
        save_choice="excel",
        excel_name="xhs_excel_only",
    )

    assert download_calls == []
    assert Path(excel_calls[0]).name == "xhs_excel_only.xlsx"


def test_spider_some_note_none_only_returns_data(monkeypatch):
    module = load_spider_main()
    spider = module.Data_Spider()

    def fake_spider_note(note_url, cookies_str, proxies=None):
        return True, "ok", {
            "note_id": "note-3",
            "user_id": "user-3",
            "nickname": "测试作者",
            "title": "只入库不落本地",
            "note_type": "图集",
            "image_list": [],
        }

    monkeypatch.setattr(spider, "spider_note", fake_spider_note)
    monkeypatch.setattr(module, "download_note", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not download")))
    monkeypatch.setattr(module, "save_to_xlsx", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not export excel")))

    result = spider.spider_some_note(
        ["https://www.xiaohongshu.com/explore/note-3?xsec_token=abc"],
        cookies_str="web_session=test",
        base_path={},
        save_choice="none",
    )

    assert result[0]["note_id"] == "note-3"


def test_spider_some_search_note_uses_search_card_fallback(monkeypatch):
    module = load_spider_main()
    spider = module.Data_Spider()

    search_card = {
        "id": "note-4",
        "xsec_token": "token-4",
        "note_card": {
            "type": "normal",
            "display_title": "北邮星塔打卡",
            "desc": "星塔附近很适合拍照",
            "user": {
                "user_id": "user-4",
                "nickname": "测试作者",
                "avatar": "https://example.com/avatar.jpg",
            },
            "interact_info": {
                "liked_count": "1.2万",
                "collected_count": "88",
                "comment_count": "9",
                "share_count": "3",
            },
            "cover": {
                "url_default": "https://example.com/cover.jpg",
            },
        },
    }

    def fake_search_some_note(*args, **kwargs):
        return True, "成功", [search_card]

    def fake_spider_note(note_url, cookies_str, proxies=None):
        return False, KeyError("data.items"), None

    monkeypatch.setattr(spider.xhs_apis, "search_some_note", fake_search_some_note)
    monkeypatch.setattr(spider, "spider_note", fake_spider_note)

    result, success, msg = spider.spider_some_search_note(
        query="北邮",
        require_num=1,
        cookies_str="web_session=test",
        base_path={},
        save_choice="none",
    )

    assert success is True
    assert msg == "成功"
    assert result[0]["note_id"] == "note-4"
    assert result[0]["title"] == "北邮星塔打卡"
    assert result[0]["desc"] == "星塔附近很适合拍照"
    assert result[0]["nickname"] == "测试作者"
    assert result[0]["image_list"] == ["https://example.com/cover.jpg"]
