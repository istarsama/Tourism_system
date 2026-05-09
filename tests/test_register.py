from fastapi.testclient import TestClient

from helpers import prepare_test_env


prepare_test_env("register")

import api  # noqa: E402


def main():
    with TestClient(api.app) as client:
        payload = {"username": "xiaoming", "password": "my_secret_password_123"}

        response = client.post("/auth/register", json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["username"] == payload["username"]

        duplicate = client.post("/auth/register", json=payload)
        assert duplicate.status_code == 400
        assert "用户名已存在" in duplicate.text

        login = client.post("/auth/login", json=payload)
        assert login.status_code == 200, login.text
        data = login.json()
        assert data["token_type"] == "bearer"
        assert data["access_token"]

    print("✅ 注册、重复注册与登录联动测试通过")


if __name__ == "__main__":
    main()
