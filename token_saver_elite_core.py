"""Dependency-free, measurement-honest request cache and context optimizer."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class Elite:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def colored(text: str, color: str) -> str:
    return f"{color}{text}{Elite.END}"


def log_elite(msg: str, level: str = "INFO") -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    color = {"ERROR": Elite.RED, "SUCCESS": Elite.GREEN, "WARN": Elite.YELLOW}.get(
        level, Elite.BLUE
    )
    print(colored(f"[{ts}] {level}: {msg}", color))


def canonical_json(value: Any) -> str:
    """Stable JSON used for cache identity and byte measurements."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def sha256_key(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass
class CacheEntry:
    key: str
    value: Any
    ttl: int
    created_at: float
    source: str
    hits: int = 0

    def is_expired(self) -> bool:
        return time.time() > self.created_at + self.ttl

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EliteMemoryCache:
    """Small local JSON cache with atomic persistence and honest metrics."""

    def __init__(self, home_dir: str | None = None):
        self.home_dir = Path(home_dir or os.path.expanduser("~/.token_saver"))
        self.home_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.home_dir / "cache.json"
        self.log_file = self.home_dir / "token_saver.log"
        self.memory: dict[str, CacheEntry] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "optimized_bytes_before": 0,
            "optimized_bytes_after": 0,
        }
        self._setup_logging()
        self._load_cache()

    def _setup_logging(self) -> None:
        self.logger = logging.getLogger(f"token_saver:{self.log_file}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file)
            handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            )
            self.logger.addHandler(handler)

    def _load_cache(self) -> None:
        try:
            if not self.cache_file.exists():
                return
            with self.cache_file.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
            for key, raw_entry in data.get("cache", {}).items():
                try:
                    entry = CacheEntry(**raw_entry)
                    if not entry.is_expired():
                        self.memory[key] = entry
                except (TypeError, ValueError) as exc:
                    self.logger.warning("Skipping invalid cache entry %s: %s", key, exc)
            loaded_stats = data.get("stats", {})
            for key in self.stats:
                value = loaded_stats.get(key, 0)
                self.stats[key] = value if isinstance(value, int) and value >= 0 else 0
        except (OSError, ValueError, TypeError) as exc:
            self.logger.error("Cache load failed: %s", exc)

    def _save_cache(self) -> bool:
        temp_file = self.cache_file.with_suffix(".tmp")
        try:
            data = {
                "schema_version": "2.0.0",
                "cache": {key: entry.to_dict() for key, entry in self.memory.items()},
                "stats": self.stats,
                "saved_at": datetime.now(UTC).isoformat(),
            }
            with temp_file.open("w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2, ensure_ascii=False, default=str)
                stream.flush()
                os.fsync(stream.fileno())
            temp_file.replace(self.cache_file)
            return True
        except (OSError, TypeError, ValueError) as exc:
            self.logger.error("Cache save failed: %s", exc)
            temp_file.unlink(missing_ok=True)
            return False

    def set(
        self, key: str, value: Any, ttl: int = 3600, source: str = "memory"
    ) -> bool:
        if not key or len(key) > 256:
            raise ValueError("key must be 1-256 characters")
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        previous = self.memory.get(key)
        self.memory[key] = CacheEntry(
            key=key,
            value=value,
            ttl=ttl,
            created_at=time.time(),
            source=source,
        )
        if self._save_cache():
            return True
        if previous is None:
            del self.memory[key]
        else:
            self.memory[key] = previous
        return False

    def get(self, key: str) -> Any | None:
        entry = self.memory.get(key)
        if entry is None:
            self.stats["misses"] += 1
            return None
        if entry.is_expired():
            del self.memory[key]
            self.stats["misses"] += 1
            self._save_cache()
            return None
        entry.hits += 1
        self.stats["hits"] += 1
        return copy.deepcopy(entry.value)

    def record_measurement(self, before: int, after: int) -> bool:
        if before < 0 or after < 0:
            raise ValueError("byte measurements cannot be negative")
        previous_before = self.stats["optimized_bytes_before"]
        previous_after = self.stats["optimized_bytes_after"]
        self.stats["optimized_bytes_before"] += before
        self.stats["optimized_bytes_after"] += after
        if self._save_cache():
            return True
        self.stats["optimized_bytes_before"] = previous_before
        self.stats["optimized_bytes_after"] = previous_after
        return False

    def health(self) -> dict[str, Any]:
        expired = sum(1 for entry in self.memory.values() if entry.is_expired())
        before = self.stats["optimized_bytes_before"]
        after = self.stats["optimized_bytes_after"]
        return {
            "cache_size": len(self.memory),
            "expired": expired,
            "valid": len(self.memory) - expired,
            **self.stats,
            "measured_bytes_saved": max(0, before - after),
            "measurement_unit": "canonical_utf8_bytes",
            "cache_dir": str(self.home_dir),
            "disk_size_kb": sum(
                path.stat().st_size
                for path in self.home_dir.glob("**/*")
                if path.is_file()
            )
            // 1024,
        }


class EliteTokenBridge:
    """Deterministic request optimizer; it never mutates caller input."""

    def __init__(self, cache: EliteMemoryCache):
        self.cache = cache

    def batch_requests(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[tuple, list[dict[str, Any]]] = {}
        for request in requests:
            grouped.setdefault((request.get("type"), request.get("model")), []).append(
                copy.deepcopy(request)
            )
        result: list[dict[str, Any]] = []
        for (request_type, model), members in grouped.items():
            if len(members) == 1:
                result.append(members[0])
                continue
            result.append(
                {
                    "type": request_type,
                    "model": model,
                    "requests": members,
                    "request_count": len(members),
                    "savings_status": "not_measured",
                }
            )
        return result

    def compress_context(self, context: str, compression_ratio: float = 0.1) -> str:
        if not 0 < compression_ratio <= 1:
            raise ValueError("compression_ratio must be greater than 0 and at most 1")
        lines = context.splitlines()
        if len(lines) <= 3 or compression_ratio == 1:
            return context
        keep_total = max(3, min(len(lines), round(len(lines) * compression_ratio)))
        head_count = min(2, keep_total)
        tail_count = keep_total - head_count
        selected = lines[:head_count] + (lines[-tail_count:] if tail_count else [])
        return "\n".join(selected)

    def optimize_request(
        self, request: dict[str, Any], ttl: int = 3600
    ) -> dict[str, Any]:
        original = copy.deepcopy(request)
        cache_key = f"request:sha256:{sha256_key(original)}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            cached["cache"] = {
                "hit": True,
                "key": cache_key,
                "algorithm": "sha256",
            }
            return cached

        optimized = copy.deepcopy(original)
        before = len(canonical_json(original).encode("utf-8"))
        context = optimized.get("context")
        if isinstance(context, str):
            optimized["context"] = self.compress_context(context)
        after = len(canonical_json(optimized).encode("utf-8"))
        optimized["measurement"] = {
            "unit": "canonical_utf8_bytes",
            "before": before,
            "after": after,
            "saved": max(0, before - after),
        }
        optimized["cache"] = {
            "hit": False,
            "key": cache_key,
            "algorithm": "sha256",
        }
        optimized["cache"]["stored"] = self.cache.set(
            cache_key,
            optimized,
            ttl=ttl,
            source="optimized_request",
        )
        optimized["measurement"]["persisted"] = self.cache.record_measurement(
            before, after
        )
        return optimized


class TokenSaverElite:
    VERSION = "4.0.0"

    def __init__(self, home_dir: str | None = None):
        self.home = Path(home_dir or os.path.expanduser("~/.token_saver"))
        self.home.mkdir(parents=True, exist_ok=True)
        self.cache = EliteMemoryCache(str(self.home))
        self.bridge = EliteTokenBridge(self.cache)
        self.db_path = self.home / "token_saver.db"
        self._init_db()

    def _init_db(self) -> None:
        connection = sqlite3.connect(self.db_path)
        try:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS query_cache (
                        query_hash TEXT PRIMARY KEY,
                        query TEXT NOT NULL,
                        result TEXT NOT NULL,
                        measured_bytes_saved INTEGER NOT NULL DEFAULT 0,
                        tokens_before INTEGER NOT NULL DEFAULT 0,
                        tokens_after INTEGER NOT NULL DEFAULT 0,
                        compression_method TEXT NOT NULL DEFAULT 'unknown',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS optimization_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_hash TEXT NOT NULL,
                        bytes_before INTEGER NOT NULL,
                        bytes_after INTEGER NOT NULL,
                        tokens_before INTEGER NOT NULL DEFAULT 0,
                        tokens_after INTEGER NOT NULL DEFAULT 0,
                        compression_method TEXT NOT NULL DEFAULT 'line_truncation',
                        cache_hit INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
        finally:
            connection.close()

    def record_optimization(
        self,
        request_hash: str,
        bytes_before: int,
        bytes_after: int,
        tokens_before: int = 0,
        tokens_after: int = 0,
        compression_method: str = "line_truncation",
        cache_hit: bool = False,
    ) -> bool:
        """Record an optimization event to the SQLite audit log."""
        try:
            connection = sqlite3.connect(self.db_path)
            try:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO optimization_log
                            (request_hash, bytes_before, bytes_after,
                             tokens_before, tokens_after,
                             compression_method, cache_hit)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            request_hash,
                            bytes_before,
                            bytes_after,
                            tokens_before,
                            tokens_after,
                            compression_method,
                            1 if cache_hit else 0,
                        ),
                    )
                return True
            finally:
                connection.close()
        except (OSError, sqlite3.Error) as exc:
            log_elite(f"optimization_log write failed: {exc}", "ERROR")
            return False

    def query_optimization_stats(self) -> dict[str, Any]:
        """Query aggregate optimization statistics from the audit log."""
        try:
            connection = sqlite3.connect(self.db_path)
            try:
                cursor = connection.execute(
                    """
                    SELECT
                        COUNT(*) as total_optimizations,
                        SUM(bytes_before) as total_bytes_before,
                        SUM(bytes_after) as total_bytes_after,
                        SUM(tokens_before) as total_tokens_before,
                        SUM(tokens_after) as total_tokens_after,
                        SUM(cache_hit) as cache_hits,
                        COUNT(*) - SUM(cache_hit) as cache_misses
                    FROM optimization_log
                    """
                )
                row = cursor.fetchone()
                if row is None or row[0] == 0:
                    return {"total_optimizations": 0}
                return {
                    "total_optimizations": row[0],
                    "total_bytes_before": row[1] or 0,
                    "total_bytes_after": row[2] or 0,
                    "total_bytes_saved": max(0, (row[1] or 0) - (row[2] or 0)),
                    "total_tokens_before": row[3] or 0,
                    "total_tokens_after": row[4] or 0,
                    "total_tokens_saved": max(0, (row[3] or 0) - (row[4] or 0)),
                    "cache_hits": row[5] or 0,
                    "cache_misses": row[6] or 0,
                }
            finally:
                connection.close()
        except (OSError, sqlite3.Error) as exc:
            log_elite(f"optimization_log query failed: {exc}", "ERROR")
            return {"total_optimizations": 0, "error": str(exc)}

    def status(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "home": str(self.home),
            "cache": self.cache.health(),
            "optimization_log": self.query_optimization_stats(),
            "bridge_ready": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def report(self) -> None:
        status = self.status()
        cache = status["cache"]
        opt_log = status["optimization_log"]
        print(colored(f"TOKEN_SAVER v{status['version']}", Elite.CYAN))
        print(f"Cache entries: {cache['valid']} valid, {cache['expired']} expired")
        print(f"Hits/misses: {cache['hits']}/{cache['misses']}")
        print(f"Measured bytes saved: {cache['measured_bytes_saved']}")
        total_opt = opt_log.get("total_optimizations", 0)
        if total_opt > 0:
            print(f"Total optimizations logged: {total_opt}")
            print(f"Total bytes saved (log): {opt_log.get('total_bytes_saved', 0)}")
            print(f"Total tokens saved (log): {opt_log.get('total_tokens_saved', 0)}")


if __name__ == "__main__":
    TokenSaverElite().report()
