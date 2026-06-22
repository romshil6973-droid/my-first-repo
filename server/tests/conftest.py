import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config

@pytest.fixture(autouse=True)
def tmp_dirs(tmp_path):
    config.UPLOADS_DIR = str(tmp_path / "uploads")
    config.DB_PATH = str(tmp_path / "metrics.db")
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)

    import database
    database.init_db()

    yield tmp_path


@pytest.fixture
def client(tmp_dirs):
    from starlette.testclient import TestClient
    import main
    main.app.state.testing = True
    return TestClient(main.app)


@pytest.fixture
def auth_client(client):
    client.post("/login", data={"password": config.DASHBOARD_PASSWORD}, follow_redirects=False)
    return client
