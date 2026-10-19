# Mission depth before compression

**Governing source:** [GlacierEQ/aspen-grove-core/TOKEN_AWARE_EXECUTION.md](https://github.com/GlacierEQ/aspen-grove-core/blob/main/TOKEN_AWARE_EXECUTION.md), verified SHA `9a20362fe8b8d1215ea50773073f5a3b556e5191`.

Token Saver is a subordinate efficiency mechanism. It **must not** lower the Operator's objective, useful execution depth, evidence surface, source visibility, or remaining actionable frontier to earn a better compression metric.

## Runtime contracts

- **Unified engine:** `optimize_message_payload(payload)` returns an unchanged complete payload by default. For explicit reversible bulk offloading, specify `offload_threshold_bytes`. Current mission, corrections, context, evidence, instructions and cursor remain inline. There is no implicit 500-byte pointer threshold.
- **Explicit context extraction:** Specify both `compression_ratio < 1` and `allow_lossy_context=True`. Source SHA-256 pointer is persisted before the extracted result is returned; `original_context_pointer` allows independent recovery. A ratio alone is not consent.
- **Elite request optimizer:** `optimize_request(request)` preserves full context unless that individual request explicitly supplies a `compression_ratio`. Old compressed results cannot be replayed because the cache-key version changed. `compress_context(text)` likewise preserves the original by default.
- **HTTP gateway:** Omitting `ratio` from `/optimize` preserves the original. An explicit ratio still permits extractive optimization with an original-source pointer.
- **MCP tools:** Operations use the local owner's cache and pointer implementation rather than returning stub results. Byte and local tokenizer measurements are never represented as provider inference telemetry.

## Acceptance criteria

1. Full mission context, objectives, corrections, evidence, action cursors and requirements survive default pipeline calls unchanged, including long text.
2. Explicit document offload is SHA-256-addressed, recoverable, and does not remove active mission state.
3. Requested extractive compression has an original-source pointer and a truthfully reported preservation state.
4. A default call does not claim savings unless it actually saved bytes; old lossy cache records do not survive admission.
5. Live results and counters cannot be hardcoded or simulated.
6. This repository does not own mission continuation or prove that work was completed. Provider-native evidence, action, readback and the remaining frontier belong to the existing APEX/Spiral runtime.

**Regression command:** `python -m pytest -q tests/` with the focused `tests/test_work_amplification_defaults.py` suite. A successful repository CI run is not proof of ChatGPT-host deployment.

## Example

```python
from src.unified_token_engine import UnifiedTokenEngine
engine = UnifiedTokenEngine(work_dir="./cache", receipts_path="./cache/receipts.jsonl")
full = engine.optimize_message_payload({"mission_id": "M1", "context": "Complete task and evidence."})
assert full["payload"]["context"] == "Complete task and evidence."

# Supporting document pointer requires explicit selection.
bulky = engine.optimize_message_payload(
    {"context": "Complete task.", "document": "Attachment text " * 100},
    offload_threshold_bytes=300,
)

# Separately consent to reversible extractive context:
compacted = engine.optimize_message_payload(
    {"context": "Long research text. " * 100},
    compression_ratio=0.2, allow_lossy_context=True,
)
```

## Source-persistence boundary

`src.pure_pointer.externalize` now fails when it cannot durably write and hash-check the original. It never issues a pointer backed only by the temporary in-process `MockRemoteStore`. `resolve` requires an actual persisted source file. Automatic 50 MB LRU eviction no longer applies to source/evidence pointers; discarding preserved originals is not a valid way to report greater savings. Full mission state remains inline unless the caller explicitly selects a reversible source offload.
