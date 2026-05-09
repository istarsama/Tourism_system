from fastapi.testclient import TestClient

from helpers import prepare_test_env, register_and_login


prepare_test_env("comment", vector=True)

import api  # noqa: E402


def main():
    with TestClient(api.app) as client:
        headers = register_and_login(client, "student_A")

        diary_resp = client.post(
            "/diaries/",
            json={
                "scope": "campus",
                "spot_id": 44,
                "title": "测试评分专用贴",
                "content": "大家快来给我打分！这是一个测试。",
                "media_files": [],
            },
            headers=headers,
        )
        assert diary_resp.status_code == 200, diary_resp.text
        diary_id = diary_resp.json()["id"]

        first = client.post(
            "/diaries/comment",
            json={"diary_id": diary_id, "content": "写得太好了！", "score": 5.0},
            headers=headers,
        )
        assert first.status_code == 200, first.text
        assert first.json()["new_average_score"] == 5.0

        second = client.post(
            "/diaries/comment",
            json={"diary_id": diary_id, "content": "再看一遍一般。", "score": 1.0},
            headers=headers,
        )
        assert second.status_code == 200, second.text
        assert second.json()["new_average_score"] == 3.0

        detail = client.get(f"/diaries/detail/{diary_id}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["score"] == 3.0
        assert detail.json()["view_count"] == 1

    print("✅ 评论与平均评分测试通过")


if __name__ == "__main__":
    main()
