from fastapi.testclient import TestClient

from helpers import prepare_test_env, register_and_login


prepare_test_env("flow", vector=True)

import api  # noqa: E402


def main():
    with TestClient(api.app) as client:
        headers = register_and_login(client, "foodie_B")

        diary_resp = client.post(
            "/diaries/",
            json={
                "scope": "campus",
                "spot_id": 18,
                "title": "风味餐厅实测",
                "content": "这里的饭菜很有特色，值得一来！",
                "media_files": [],
            },
            headers=headers,
        )
        assert diary_resp.status_code == 200, diary_resp.text
        diary_id = diary_resp.json()["id"]
        assert diary_resp.json()["score"] == 0.0

        comment_resp = client.post(
            "/diaries/comment",
            json={"diary_id": diary_id, "content": "排队人挺多的。", "score": 4.0},
            headers=headers,
        )
        assert comment_resp.status_code == 200, comment_resp.text
        assert comment_resp.json()["new_average_score"] == 4.0

    print("✅ 登录、发日记、评论业务流测试通过")


if __name__ == "__main__":
    main()
