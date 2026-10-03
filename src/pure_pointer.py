"""Content-addressed payload offload with full SHA-256 verification."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Pointer:
    path: str
    canonical_uri: str
    sha256: str
    bytes_in: int
    bytes_out: int

    @property
    def savings_pct(self) -> float:
        if self.bytes_in <= 0:
            return 0.0
        return 100.0 * (1.0 - self.bytes_out / self.bytes_in)


def _safe_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip(".-")
    return cleaned or "blob"


import shutil
from typing import ClassVar

class MockRemoteStore:
    """Simulates OCI / Cloud bucket for seamless offload."""
    _bucket: ClassVar[dict[str, bytes]] = {}

    @classmethod
    def put(cls, digest: str, data: bytes) -> None:
        cls._bucket[digest] = data

    @classmethod
    def get(cls, digest: str) -> bytes | None:
        return cls._bucket.get(digest)


def get_free_disk_gb(path: Path) -> float:
    try:
        usage = shutil.disk_usage(path)
        return usage.free / (1024**3)
    except OSError:
        return 0.0


def enforce_lru_quota(root: Path, max_mb: int = 50) -> None:
    if not root.exists():
        return
    max_bytes = max_mb * 1024 * 1024
    files = []
    total_size = 0
    for path in root.glob("*.txt"):
        if path.is_file():
            stat = path.stat()
            size = stat.st_size
            total_size += size
            files.append((stat.st_atime, size, path))
            
    if total_size <= max_bytes:
        return
        
    # Sort by atime ascending (oldest first)
    files.sort(key=lambda x: x[0])
    
    # Evict until we drop below max_bytes * 0.8 (Tidal eviction to 40 MB)
    target_size = max_bytes * 0.8
    for atime, size, path in files:
        if total_size <= target_size:
            break
        try:
            path.unlink()
            total_size -= size
        except OSError:
            pass


def externalize(body: str, dest: Path, label: str = "blob") -> Pointer:
    root = dest.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    raw = body.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    path = root / f"{_safe_label(label)}_{digest}.txt"
    
    # 1. Seamless Remote Write-Through
    MockRemoteStore.put(digest, raw)
    
    # 2. Local Disk Guard (Only write locally if disk is safe)
    if get_free_disk_gb(root) >= 2.0:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=root,
                prefix=f"{_safe_label(label)}_{digest}_",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_file.write(raw)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = Path(temp_file.name)
            os.replace(temp_path, path)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
                
        # 3. LRU Quota Eviction (50 MB)
        enforce_lru_quota(root, max_mb=50)
                
    canonical_uri = f"sha256://{digest}"
    compact = f"[ptr:{canonical_uri}|file:{path.name}|n={len(raw)}]"
    return Pointer(
        str(path), canonical_uri, digest, len(raw), len(compact.encode("utf-8"))
    )


def resolve(pointer: Pointer, allowed_root: Path | None = None) -> str:
    path = Path(pointer.path).expanduser().resolve()
    if allowed_root is not None:
        root = allowed_root.expanduser().resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("pointer path is outside the allowed root") from exc
            
    # 1. Local Read
    raw = None
    if path.exists():
        raw = path.read_bytes()
    else:
        # 2. Seamless Remote Read-Through (Cache Miss)
        raw = MockRemoteStore.get(pointer.sha256)
        if raw is None:
            raise ValueError(f"pointer {pointer.sha256} not found locally or in remote store")
            
        # Optional: Write back to local cache if space allows (omitted for brevity)
        
    actual = hashlib.sha256(raw).hexdigest()
    if actual != pointer.sha256 or pointer.canonical_uri != f"sha256://{actual}":
        raise ValueError("pointer content hash mismatch")
    return raw.decode("utf-8")


def verify(pointer: Pointer, allowed_root: Path | None = None) -> bool:
    try:
        resolve(pointer, allowed_root)
        return True
    except (OSError, UnicodeError, ValueError):
        return False


def measure(pointer: Pointer) -> dict:
    return {
        "bytes_in": pointer.bytes_in,
        "bytes_out": pointer.bytes_out,
        "savings_pct": round(pointer.savings_pct, 2),
        "measurement_unit": "utf8_bytes",
        "sha256": pointer.sha256,
        "canonical_uri": pointer.canonical_uri,
    }
