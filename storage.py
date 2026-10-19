#config.py   -> supplies upload_dir, database_url, log_level, limits
#lifespan    -> reads settings, configures logging, builds Repository and storage,
#               puts them on app.state, disposes them on shutdown
#storage.py  -> receives its root from config, logs failures through logging
import uuid
from pathlib import Path
from typing import Protocol

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


class ChartStorage(Protocol):
    def save(self, *, owner: str, filename: str, content: bytes) -> str: ...
    def delete(self, key: str) -> None: ...
    def path_for(self, key: str) -> Path: ...


class LocalChartStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def save(self, *, owner: str, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise ValueError(f"UNSUPPORTED FILE TYPE: {suffix}")
        key = f"{owner}/{uuid.uuid4().hex}{suffix}"
        dest = self.path_for(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return key

    def delete(self, key: str) -> None:
        self.path_for(key).unlink(missing_ok=True)

    def path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):      # blocks "../../etc/passwd"
            raise ValueError("INVALID STORAGE KEY")
        return path
