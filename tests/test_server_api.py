from fastapi.testclient import TestClient
from server import main as server_module
from pathlib import Path

# Use the app from the server module and create a TestClient
app = server_module.app
client = TestClient(app)
API_KEY = "dev-key-123"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_unauthorized_upload():
    files = {"file": ("f.bin", b"x")}
    r = client.post("/files/unauth/test.bin", files=files)
    assert r.status_code == 401


def test_upload_list_download_delete(tmp_path):
    # Isolate repo storage for this test
    repo = Path(tmp_path) / "repo_data" / "server-1"
    repo.mkdir(parents=True, exist_ok=True)
    server_module.REPO = repo

    headers = {"x-api-key": API_KEY}
    files = {"file": ("f.bin", b"hello-world")}

    # upload
    r = client.post("/files/auto/testfile.bin", headers=headers, files=files)
    assert r.status_code == 200
    info = r.json()
    assert info.get("version") == 1
    assert info.get("size") == len(b"hello-world")
    assert info.get("checksum", "").startswith("sha256:")

    # list versions
    r = client.get("/files/auto/testfile.bin/versions", headers=headers)
    assert r.status_code == 200
    versions = r.json()
    assert isinstance(versions, list) and len(versions) >= 1

    # download latest
    r = client.get("/files/auto/testfile.bin", headers=headers)
    assert r.status_code == 200
    assert r.content == b"hello-world"

    # delete latest
    r = client.delete("/files/auto/testfile.bin", headers=headers)
    assert r.status_code == 200
    assert r.json().get("deletedVersion") == 1

    # now reading should return 404
    r = client.get("/files/auto/testfile.bin", headers=headers)
    assert r.status_code == 404
