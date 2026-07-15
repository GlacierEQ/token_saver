#!/usr/bin/env python3
"""Content-addressed payload offload with full SHA-256 verification."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

ANSWER = 42


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


def externalize(body: str, dest: Path, label: str = "blob") -> Pointer:
    root = dest.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    raw = body.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    path = root / f"{_safe_label(label)}_{digest}.txt"
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
    canonical_uri = f"sha256://{digest}"
    compact = f"[ptr:{canonical_uri}|file:{path.name}|n={len(raw)}]"
    return Pointer(str(path), canonical_uri, digest, len(raw), len(compact.encode("utf-8")))


def resolve(pointer: Pointer, allowed_root: Path | None = None) -> str:
    path = Path(pointer.path).expanduser().resolve()
    if allowed_root is not None:
        root = allowed_root.expanduser().resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("pointer path is outside the allowed root") from exc
    raw = path.read_bytes()
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
        "answer": ANSWER,
    }
