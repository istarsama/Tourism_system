import os
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"


def prepare_test_env(name: str, *, vector: bool = False) -> tuple[Path, Path | None]:
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))

    db_path = PROJECT_ROOT / "tests" / f"tmp_{name}.db"
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ.setdefault("SECRET_KEY", "test-secret-key")
    os.environ.setdefault("OPENAI_COMPAT_API_KEY", "test-key")
    os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")
    os.environ.setdefault("TAVILY_API_KEY", "")
    os.environ["EMBEDDING_BACKEND"] = "local_hash"

    vector_dir = None
    if vector:
        vector_dir = PROJECT_ROOT / "tests" / f"tmp_{name}_chroma"
        if vector_dir.exists():
            shutil.rmtree(vector_dir, ignore_errors=True)
        os.environ["VECTOR_DB_PATH"] = vector_dir.as_posix()

    return db_path, vector_dir


def login(client, username: str, password: str) -> dict:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register_and_login(client, username: str, password: str = "123456") -> dict:
    response = client.post("/auth/register", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return login(client, username, password)
