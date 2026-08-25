import hashlib
from pathlib import Path

from ..config import settings


def ensure_dirs() -> None:
    for p in (settings.data_dir, settings.upload_dir, settings.heatmap_dir, settings.report_dir):
        p.mkdir(parents=True, exist_ok=True)


def hashes_of(data: bytes) -> tuple[str, str]:
    return hashlib.sha256(data).hexdigest(), hashlib.sha1(data).hexdigest()


def save_upload(data: bytes, suffix: str) -> str:
    ensure_dirs()
    digest = hashlib.sha256(data).hexdigest()
    name = f"{digest}{suffix}"
    path = settings.upload_dir / name
    if not path.exists():
        path.write_bytes(data)
    return name


def upload_path(name: str) -> Path:
    return settings.upload_dir / name


def media_kind(filename: str, mime: str) -> str:
    ext = Path(filename).suffix.lower()
    if mime.startswith("image/") or ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}:
        return "image"
    if mime.startswith("video/") or ext in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
        return "video"
    if mime.startswith("audio/") or ext in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}:
        return "audio"
    return "unknown"
