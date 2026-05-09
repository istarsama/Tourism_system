from fastapi.testclient import TestClient

from helpers import prepare_test_env


prepare_test_env("login")

import api  # noqa: E402


def main():
    with TestClient(api.app) as client:
        user = {"username": "student_A", "password": "123456"}
        register = client.post("/auth/register", json=user)
        assert register.status_code == 200, register.text

        login = client.post("/auth/login", json=user)
        assert login.status_code == 200, login.text
        assert login.json()["access_token"]

        bad_login = client.post(
            "/auth/login",
            json={"username": user["username"], "password": "wrong-password"},
        )
        assert bad_login.status_code == 401

    print("✅ 登录成功与错误密码拒绝测试通过")


if __name__ == "__main__":
    main()
