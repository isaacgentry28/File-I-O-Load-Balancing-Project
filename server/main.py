from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from hashlib import sha256
from datetime import datetime
from typing import Optional, List
import asyncio, json, os

app = FastAPI(title="Dist-IO File Server")

CONFIG_PATH = os.environ.get("SERVER_CONFIG", "server_config.json")
DEFAULT_CFG = {"repo_root": "repo_data/server-1", "api_key": "dev-key-123"}

try:
    if Path(CONFIG_PATH).exists():
        # 'utf-8-sig' strips a BOM if present
        cfg_text = Path(CONFIG_PATH).read_text(encoding="utf-8-sig")
        cfg = json.loads(cfg_text)
    else:
        cfg = DEFAULT_CFG
except Exception as e:
    print(f"[WARN] Failed to load {CONFIG_PATH}: {e}. Using defaults.")
    cfg = DEFAULT_CFG


REPO = Path(cfg["repo_root"]).resolve()
REPO.mkdir(parents=True, exist_ok=True)

_locks: dict[str, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()

async def get_lock(key: str) -> asyncio.Lock:
    async with _locks_guard:
        if key not in _locks:
            _locks[key] = asyncio.Lock()
        return _locks[key]

class VersionInfo(BaseModel):
    version: int
    size: int
    checksum: str
    timestamp: str

def file_dir(path: str) -> Path:
    return (REPO / "files" / path)

def meta_path(path: str) -> Path:
    return file_dir(path) / "index.json"

def load_meta(path: str) -> dict:
    mp = meta_path(path)
    return json.loads(mp.read_text()) if mp.exists() else {"latest": 0, "versions": []}

def save_meta(path: str, meta: dict):
    d = file_dir(path); d.mkdir(parents=True, exist_ok=True)
    meta_path(path).write_text(json.dumps(meta, indent=2))

@app.get("/health")
async def health():
    return {"status": "ok"}

def require_key(key: Optional[str]):
    if key != cfg["api_key"]:
        raise HTTPException(status_code=401, detail="invalid API key")

@app.post("/files/{path:path}")
async def write_file(path: str, file: UploadFile = File(...), x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    lock = await get_lock(path)
    async with lock:
        meta = load_meta(path)
        new_v = meta["latest"] + 1
        target = file_dir(path) / f"v{new_v}"
        data = await file.read()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    checksum = "sha256:" + sha256(data).hexdigest()
    info = VersionInfo(version=new_v, size=len(data), checksum=checksum, timestamp=datetime.utcnow().isoformat()+"Z")
    meta["latest"] = new_v
    # use model_dump() (Pydantic v2) instead of the deprecated dict()
    meta["versions"].append(info.model_dump())
    save_meta(path, meta)
    return info

@app.get("/files/{path:path}/versions", response_model=List[VersionInfo])
async def list_versions(path: str, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    meta = load_meta(path)
    return meta["versions"]


@app.get("/files/{path:path}")
async def read_file(path: str, version: Optional[int] = None, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    meta = load_meta(path)
    if meta["latest"] == 0:
        raise HTTPException(404, "file not found")
    v = version or meta["latest"]
    p = file_dir(path) / f"v{v}"
    if not p.exists():
        raise HTTPException(404, "version not found")
    return FileResponse(p)

@app.delete("/files/{path:path}")
async def delete_latest(path: str, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    lock = await get_lock(path)
    async with lock:
        meta = load_meta(path)
        if meta["latest"] == 0:
            raise HTTPException(404, "file not found")
        deleted = meta["latest"]
        meta["latest"] = 0
        save_meta(path, meta)
        return {"deletedVersion": deleted}
