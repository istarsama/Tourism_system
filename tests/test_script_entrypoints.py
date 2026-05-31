import os
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCRIPT_TESTS = [
    "tests/test_register.py",
    "tests/test_login.py",
    "tests/test_flow.py",
    "tests/test_comment.py",
    "tests/test_nav.py",
    "tests/test_search.py",
    "tests/test_rag.py",
    "tests/test_ai.py",
    "tests/test_diary_scope.py",
    "tests/test_init_db_schema_compat.py",
    "tests/test_map_api.py",
    "tests/test_national_spot_schema_upgrade.py",
    "tests/test_national_spot_xhs_import.py",
    "tests/test_national_spots_link.py",
    "tests/test_osm_api.py",
    "tests/test_osm_frontend_contract.py",
    "tests/test_osm_graph_cache_metadata.py",
    "tests/test_osm_preload.py",
    "tests/test_poi_sync.py",
    "tests/test_search_scope.py",
    "tests/test_vector_db.py",
    "tests/tools/test_spider_run.py",
]


@pytest.mark.parametrize("script_path", SCRIPT_TESTS)
def test_script_entrypoint(script_path: str):
    env = os.environ.copy()
    env.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "SECRET_KEY": "test-secret-key",
            "OPENAI_COMPAT_API_KEY": "test-key",
            "DEEPSEEK_API_KEY": "test-key",
            "TAVILY_API_KEY": "",
            "EMBEDDING_BACKEND": "local_hash",
            "XHS_LIVE_TEST": "0",
        }
    )
    env.pop("XHS_COOKIE", None)

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / script_path)],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=300,
    )

    assert result.returncode == 0, (
        f"{script_path} failed with exit code {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
