"""APEX Unified Token Engine: Dual-Stage Macro + Micro Token Optimization.

Stage 1 (Macro): Pure Pointer Externalization — offloads bulky payloads (>500B)
to content-addressed SHA-256 storage, emitting immutable receipts.
Stage 2 (Micro): Context Compression — scores lines with TF-IDF and structural bonuses,
or delegates to Mermicorn ContextCompressor when present.
"""
from __future__ import annotations

import copy
import json
import math
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

# Mission/governance/source fields must stay available to the next agent.
_MISSION_FIELDS = frozenset({
    "context", "mission", "mission_id", "objective", "objectives", "goal", "goals",
    "instructions", "system", "messages", "corrections", "requirements", "evidence",
    "sources", "facts", "decisions", "action_plan", "actions", "tasks", "cursor",
    "continuation_cursor", "readback", "case", "case_id", "constraints",
})

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
        offload_threshold_bytes: int | None = None,
        compression_ratio: float = 1.0,
        *,
        allow_lossy_context: bool = False,
    ) -> dict[str, Any]:
        """Preserve complete work by default; allow explicit reversible offload/extraction."""
        if offload_threshold_bytes is not None and (
            isinstance(offload_threshold_bytes, bool)
            or not isinstance(offload_threshold_bytes, int)
            or offload_threshold_bytes <= 0
        ):
            raise ValueError("offload_threshold_bytes must be a positive integer or None")
        if (
            isinstance(compression_ratio, bool)
            or not isinstance(compression_ratio, (int, float))
            or not math.isfinite(compression_ratio)
            or not 0 < compression_ratio <= 1
        ):
            raise ValueError("compression_ratio must be finite and in (0,1]")
        if not isinstance(allow_lossy_context, bool):
            raise ValueError("allow_lossy_context must be boolean")
        orig_raw = json.dumps(payload, sort_keys=True)
        orig_bytes = len(orig_raw.encode("utf-8"))
        orig_tokens = estimate_tokens(orig_raw)

        # Preserve full source and mission context unless an offload was requested.
        if offload_threshold_bytes is None:
            final_payload = copy.deepcopy(payload)
            did_externalize = False
        else:
            final_payload, did_externalize = self.bridge.auto_externalize_if_needed(
                payload,
                threshold_bytes=offload_threshold_bytes,
                preserve_keys=_MISSION_FIELDS,
            )

        requested_extract = compression_ratio < 1
        blocked_extract = requested_extract and not allow_lossy_context
        applied_extract = False
        recovery_pointer = None
        context = final_payload.get("context")
        if requested_extract and allow_lossy_context and isinstance(context, str) and len(context) > 300:
            compacted = None
            if self.mermicorn_available:
                try:
                    compressor = MermicornCompressor()
                    result = compressor.compress(context, strategy="semantic_dedup")
                    if isinstance(result.compacted_text, str):
                        compacted = result.compacted_text
                except Exception:
                    compacted = None
            if compacted is None:
                compacted = self.semantic_compressor.compress_to_budget(
                    context,
                    max_tokens=max(1, int(estimate_tokens(context) * compression_ratio)),
                )
            if compacted != context:
                # Source write must succeed BEFORE an extracted answer leaves the pipeline.
                receipt = self.bridge.externalize_payload("explicit_context_original", context)
                recovery_pointer = receipt.canonical_uri
                final_payload["context"] = compacted
                applied_extract = True

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
                "mission_depth_policy": "preserve_by_default",
                "mission_context_preserved": final_payload.get("context") == payload.get("context"),
                "lossy_compression_blocked": blocked_extract,
                "lossy_compression_applied": applied_extract,
                "original_context_pointer": recovery_pointer,
                "token_count_basis": "local_counter_not_actual_provider_usage",
            },
        }
