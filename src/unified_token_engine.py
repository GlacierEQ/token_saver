"""APEX Unified Token Engine: Dual-Stage Macro + Micro Token Optimization.

Stage 1 (Macro): Pure Pointer Externalization — offloads bulky payloads (>500B)
to content-addressed SHA-256 storage, emitting immutable receipts.
Stage 2 (Micro): Context Compression — scores lines with TF-IDF and structural bonuses,
or delegates to Mermicorn ContextCompressor when present.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from .sovereign_bridge import SovereignTokenBridge, SovereignPointerReceipt
    from .semantic_compressor import SemanticCompressor
    from .token_counter import estimate_tokens
except (ImportError, ValueError):
    from sovereign_bridge import SovereignTokenBridge, SovereignPointerReceipt
    from semantic_compressor import SemanticCompressor
    from token_counter import estimate_tokens

# Optional Mermicorn integration
try:
    import sys
    _mermi_path = Path("/root/projects/mermicorn/token-saver/src")
    if str(_mermi_path) not in sys.path:
        sys.path.insert(0, str(_mermi_path))
    from mermicorn_token_saver import ContextCompressor as MermicornCompressor
except Exception:
    MermicornCompressor = None  # type: ignore


class UnifiedTokenEngine:
    """Combines GlacierEQ pure-pointer externalization with micro context compression."""

    def __init__(
        self,
        work_dir: Path | str = "/root/projects/token_saver/token_saver_work",
        receipts_path: Path | str = "/root/projects/token_saver/TOKEN_SAVER_CHAIN.jsonl",
    ) -> None:
        self.bridge = SovereignTokenBridge(storage_dir=work_dir, receipts_path=receipts_path)
        self.semantic_compressor = SemanticCompressor()
        self.mermicorn_available = MermicornCompressor is not None

    def optimize_message_payload(
        self,
        payload: dict[str, Any],
        offload_threshold_bytes: int = 500,
        compression_ratio: float = 0.5,
    ) -> dict[str, Any]:
        """Runs the complete two-stage optimization pipeline."""
        orig_raw = json.dumps(payload, sort_keys=True)
        orig_bytes = len(orig_raw.encode("utf-8"))
        orig_tokens = estimate_tokens(orig_raw)

        # Stage 1: Macro Pure-Pointer Externalization
        externalized_payload, did_externalize = self.bridge.auto_externalize_if_needed(
            payload, threshold_bytes=offload_threshold_bytes
        )

        # Stage 2: Micro Context Compression on any remaining long text
        final_payload = externalized_payload
        if isinstance(final_payload, dict) and "context" in final_payload and isinstance(final_payload["context"], str):
            ctx_text = final_payload["context"]
            if len(ctx_text) > 300:
                if self.mermicorn_available:
                    try:
                        compressor = MermicornCompressor()
                        comp_res = compressor.compress(ctx_text, strategy="semantic_dedup")
                        final_payload["context"] = comp_res.compacted_text
                    except Exception:
                        final_payload["context"] = self.semantic_compressor.compress_to_budget(
                            ctx_text, max_tokens=max(1, int(orig_tokens * compression_ratio))
                        )
                else:
                    final_payload["context"] = self.semantic_compressor.compress_to_budget(
                        ctx_text, max_tokens=max(1, int(orig_tokens * compression_ratio))
                    )

        final_raw = json.dumps(final_payload, sort_keys=True)
        final_bytes = len(final_raw.encode("utf-8"))
        final_tokens = estimate_tokens(final_raw)

        saved_bytes = max(0, orig_bytes - final_bytes)
        saved_tokens = max(0, orig_tokens - final_tokens)
        savings_pct = round((saved_bytes / orig_bytes) * 100.0, 2) if orig_bytes > 0 else 0.0

        return {
            "status": "OPTIMIZED",
            "payload": final_payload,
            "metrics": {
                "bytes_before": orig_bytes,
                "bytes_after": final_bytes,
                "bytes_saved": saved_bytes,
                "tokens_before": orig_tokens,
                "tokens_after": final_tokens,
                "tokens_saved": saved_tokens,
                "savings_pct": savings_pct,
                "stage1_externalized": did_externalize,
                "mermicorn_active": self.mermicorn_available,
            },
        }
