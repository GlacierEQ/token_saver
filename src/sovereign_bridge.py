"""APEX Sovereign Token Saver Bridge.

Provides pure-pointer externalization, cryptographic SHA-256 receipt chaining,
and transparent payload offloading for autonomous agent swarms and Mastermind MegaKernel.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SovereignPointerReceipt:
    seq: int
    prev_hash: str
    timestamp: float
    label: str
    sha256: str
    original_bytes: int
    pointer_bytes: int
    savings_pct: float
    canonical_uri: str
    receipt_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SovereignTokenBridge:
    """Bridges Sovereign Agent Swarms with Pure-Pointer Token Externalization."""

    def __init__(
        self,
        storage_dir: Path | str = "/root/projects/token_saver/token_saver_work",
        receipts_path: Path | str = "/root/projects/token_saver/TOKEN_SAVER_CHAIN.jsonl",
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_path = Path(receipts_path)
        self.receipts_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_chain: list[SovereignPointerReceipt] = []
        self._load_chain()

    def _load_chain(self) -> None:
        if self.receipts_path.exists():
            try:
                with open(self.receipts_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            d = json.loads(line)
                            r = SovereignPointerReceipt(
                                seq=d["seq"],
                                prev_hash=d["prev_hash"],
                                timestamp=d["timestamp"],
                                label=d["label"],
                                sha256=d["sha256"],
                                original_bytes=d["original_bytes"],
                                pointer_bytes=d["pointer_bytes"],
                                savings_pct=d["savings_pct"],
                                canonical_uri=d["canonical_uri"],
                                receipt_hash=d["receipt_hash"],
                            )
                            self.receipt_chain.append(r)
            except Exception:
                pass

    def externalize_payload(
        self,
        label: str,
        content: str | bytes,
        extra_metadata: Optional[dict[str, Any]] = None,
    ) -> SovereignPointerReceipt:
        """Content-addressed offloading with SHA-256 verification and receipt emission."""
        raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
        orig_len = len(raw_bytes)
        c_hash = hashlib.sha256(raw_bytes).hexdigest()
        filename = f"{c_hash}.bin"
        target_file = self.storage_dir / filename

        # Atomic write
        temp_file = target_file.with_suffix(".tmp")
        temp_file.write_bytes(raw_bytes)
        temp_file.replace(target_file)

        uri = f"sha256://{c_hash}"
        pointer_repr = json.dumps({
            "__pointer__": uri,
            "label": label,
            "sha256": c_hash,
            "bytes": orig_len,
            "meta": extra_metadata or {},
        })
        ptr_len = len(pointer_repr.encode("utf-8"))
        savings = round(((orig_len - ptr_len) / orig_len) * 100.0, 2) if orig_len > ptr_len else 0.0

        prev_h = self.receipt_chain[-1].receipt_hash if self.receipt_chain else "0" * 64
        seq = len(self.receipt_chain) + 1
        now = time.time()

        blob = f"{seq}:{prev_h}:{now}:{label}:{c_hash}:{orig_len}:{ptr_len}"
        r_hash = hashlib.sha256(blob.encode("utf-8")).hexdigest()

        receipt = SovereignPointerReceipt(
            seq=seq,
            prev_hash=prev_h,
            timestamp=now,
            label=label,
            sha256=c_hash,
            original_bytes=orig_len,
            pointer_bytes=ptr_len,
            savings_pct=savings,
            canonical_uri=uri,
            receipt_hash=r_hash,
        )
        self.receipt_chain.append(receipt)

        with open(self.receipts_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_dict()) + "\n")

        return receipt

    def resolve_pointer(self, uri_or_hash: str) -> Optional[str]:
        """Resolves an externalized pointer back to content, verifying SHA-256 integrity."""
        h = uri_or_hash.replace("sha256://", "").strip()
        target = self.storage_dir / f"{h}.bin"
        if not target.exists():
            return None
        data = target.read_bytes()
        actual_h = hashlib.sha256(data).hexdigest()
        if actual_h != h:
            raise ValueError(f"Integrity violation: expected {h}, got {actual_h}")
        return data.decode("utf-8", errors="replace")

    def auto_externalize_if_needed(
        self,
        data: Any,
        threshold_bytes: int = 500,
        label_prefix: str = "auto",
    ) -> tuple[Any, bool]:
        """Recursively checks payloads and externalizes large text blobs."""
        if isinstance(data, str) and len(data.encode("utf-8")) > threshold_bytes:
            rec = self.externalize_payload(f"{label_prefix}_str", data)
            return {
                "__pointer__": rec.canonical_uri,
                "sha256": rec.sha256,
                "bytes": rec.original_bytes,
                "savings_pct": rec.savings_pct,
            }, True

        if isinstance(data, dict):
            mutated = False
            new_dict = {}
            for k, v in data.items():
                new_v, did_mut = self.auto_externalize_if_needed(
                    v, threshold_bytes=threshold_bytes, label_prefix=f"{label_prefix}_{k}"
                )
                new_dict[k] = new_v
                if did_mut:
                    mutated = True
            return new_dict, mutated

        if isinstance(data, list):
            mutated = False
            new_list = []
            for i, item in enumerate(data):
                new_item, did_mut = self.auto_externalize_if_needed(
                    item, threshold_bytes=threshold_bytes, label_prefix=f"{label_prefix}_{i}"
                )
                new_list.append(new_item)
                if did_mut:
                    mutated = True
            return new_list, mutated

        return data, False
