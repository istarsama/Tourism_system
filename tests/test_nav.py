from fastapi.testclient import TestClient

from helpers import prepare_test_env


prepare_test_env("nav")

import api  # noqa: E402


def main():
    with TestClient(api.app) as client:
        single = client.post(
            "/navigate",
            json={"start_id": 1, "end_id": 44, "strategy": "dist", "transport": "walk"},
        )
        assert single.status_code == 200, single.text
        single_data = single.json()
        assert single_data["path_ids"][0] == 1
        assert single_data["path_ids"][-1] == 44
        assert single_data["cost_unit"] == "米"

        multi = client.post(
            "/navigate",
            json={
                "start_id": 1,
                "end_id": 7,
                "via_ids": [57],
                "strategy": "dist",
                "transport": "bike",
            },
        )
        assert multi.status_code == 200, multi.text
        assert 57 in multi.json()["path_ids"]

    print("✅ 校园单点与多点导航测试通过")


if __name__ == "__main__":
    main()
