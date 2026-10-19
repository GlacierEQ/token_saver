# Token Saver v4.1 — Sovereign Dual-Stage Optimization & Pure-Pointer Engine

**Dependency-free, measurement-honest, distributed token optimization, pure-pointer offloading, and APEX receipt chaining for LLM agent infrastructure.**

Zero mandatory runtime dependencies. The full Python suite runs in CI; local token metrics are not provider inference telemetry.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  APEX Unified Token Engine (src/unified_token_engine.py)│
│  Stage 1: Macro Pure Pointer Offload (>500B)            │
│  Stage 2: Micro Context Compression (+ Mermicorn fallback)│
├─────────────────────────────────────────────────────────┤
│  APEX Sovereign Bridge (src/sovereign_bridge.py)        │
│  SHA-256 Content-Addressed Offload + Receipt Chaining   │
├─────────────────────────────────────────────────────────┤
│  MCP Tool Server (JSON-RPC 2.0 over stdio)              │
│  compress_context · externalize · optimize · status      │
├─────────────────────────────────────────────────────────┤
│  HTTP Gateway (:8400)                                    │
│  /health · /cache · /optimize · /metrics                 │
├───────────────┬─────────────────┬───────────────────────┤
│ Token Counter │ Semantic        │ Pure Pointer           │
│ (BPE heurist  │ Compressor      │ (SHA-256 content-      │
│  + tiktoken)  │ (TF-IDF lines)  │  addressed offload)    │
├───────────────┴─────────────────┴───────────────────────┤
│  EliteMemoryCache (JSON) + SQLite Optimization Log       │
├─────────────────────────────────────────────────────────┤
│  Distributed Mesh: HashRing + UDP Discovery + Replicas   │
├─────────────────────────────────────────────────────────┤
│  Observability: Prometheus Metrics · Integrity Watchdog   │
│  Mastermind Sidecar: Process/Memory/Disk Health           │
└─────────────────────────────────────────────────────────┘
```

## What It Does (Measured)

| Component | File | What It Does |
|---|---|---|
| **Unified Token Engine** | `src/unified_token_engine.py` | Orchestrates dual-stage optimization: Macro PurePointer offloading (>500B) and Micro context compression. Seamlessly integrates with Mermicorn context compression when detected. |
| **Sovereign Bridge** | `src/sovereign_bridge.py` | Content-addressed SHA-256 storage (`sha256://<hash>`), automated payload inspection, pointer resolution with cryptographic integrity checks, and immutable receipt chaining (`TOKEN_SAVER_CHAIN.jsonl`). |
| **Token Counter** | `src/token_counter.py` | Estimates LLM token counts via calibrated character ratios. Falls back to exact `tiktoken` counts when available. |
| **Semantic Compressor** | `src/semantic_compressor.py` | Block-aware segmentation (protects code fences, lists, paragraphs). TF-IDF weighted block scoring. |
| **Pure Pointer** | `src/pure_pointer.py` | Explicit durable SHA-256 source storage, 2 GiB free-disk guard, independent local readback, and no automatic eviction of preserved sources. |
| **Elite Cache & Compressor** | `token_saver_elite_core.py` | 4-rung Lossless-first compression ladder (Exact → Normalize → Pointer → Declared Extractive). Emits omission receipts for dropped blocks. |
| **Preserve Guard** | `src/preserve_guard.py` | Detects URLs, SHAs, timestamps, negations, and docket numbers. Fails closed (`BudgetUnmetProtectedError`) if budget requires dropping protected text. |
| **SQLite Audit Log** | `token_saver_elite_core.py` | Records every optimization event with bytes/tokens before/after and compression method. |
| **Promotion Authority** | `src/promotion_authority.py` | HMAC-SHA256 signed promotion grants with expiration and proof receipt verification. |
| **HTTP Gateway** | `server/gateway.py` | ThreadingHTTPServer exposing cache, optimization, health, and Prometheus metrics endpoints. Boot requires explicit `--discovery` flag to join mesh. |
| **Peer Discovery** | `server/discovery.py` | Opt-in, targeted Tailscale (`100.x.x.x`) peer discovery. Zero LAN UDP broadcast pollution. |
| **Consistent Hash Ring** | `server/mesh.py` | Distributes cache keys across peers with configurable virtual nodes and N-replica replication. |
| **MCP Tool Server** | `mcp/server.py` | JSON-RPC 2.0 MCP server with 4 tools for agent integration. |
| **Integrity Watchdog** | `src/watchdog.py` | SHA-256 file monitoring with polling loop and change callbacks. |
| **Prometheus Metrics** | `src/metrics.py` | Thread-safe counters, gauges, and histograms in Prometheus text exposition format. |
| **Mastermind Sidecar** | `mastermind_sidecar.py` | Real process monitor: PID, memory, uptime, cache health, disk space, database status. |

## Benchmark (Deterministic Fixture)

| Workload | Result |
|---|---|
| Cache miss → hit | 1 miss, 1 hit, 50 internal accounting tokens saved |
| Context sampling | 100 input lines → 10 output lines; 3,089 → 307 bytes |
| Same-type/model batching | 3 requests → 1; 300 → 210 estimated tokens |
| Pointer externalization | 6,000 → 165 bytes; 97.25% byte reduction |

These are reproducible fixture results, not guarantees for arbitrary workloads.

## Quick Start

```bash
# Optional editable install (PEP 621 / pyproject.toml)
pip install -e . --no-deps

# Run the cache + optimization engine
python3 token_saver_elite_core.py

# Sovereign CLI Commands
python3 token_saver_elite_cli.py health
python3 token_saver_elite_cli.py benchmark
python3 token_saver_elite_cli.py sovereign_externalize <label> <content>
python3 token_saver_elite_cli.py unified_optimize '{"context": "text..."}'

# Start the HTTP gateway
python3 -m server.gateway --port 8400

# Start the MCP tool server (for agent integration)
python3 -m mcp.server

# Run the integrity watchdog
python3 -m src.watchdog

# Run the complete Python test suite
python3 -m pytest tests/ -v
```

## Dependency Strategy

```
Core engine: Zero external dependencies (stdlib only)
Optional:    tiktoken (exact GPT token counts), mermicorn-token-saver
```

## Test Coverage

The full Python test suite and security checks run in CI; test counts are read from each actual workflow run, not hard-coded.

## License

See [LICENSE](LICENSE).


## ChatGPT conversation export auditor

Analyze **export-visible message text**, per selected conversation branch, role and turn. It does **not** measure ChatGPT's actual inference input/output, cached, hidden reasoning tokens, or the percentage of available compute.

```bash
python3 -m pip install -e '.[audit]'
token-saver-chatgpt-audit ~/Downloads/chatgpt-export.zip --output ~/Desktop/chatgpt-token-audit --require-tokenizer
python3 -m pytest -q tests/test_chatgpt_export_audit.py
```

This local-only command writes aggregate JSON and per-message CSV reports. With tiktoken installed, token counts are precise **for the o200k_base tokenizer**, not necessarily the deployed ChatGPT model. Without it, rough character-based estimates are explicitly labeled. Protect your private export and generated reports; none of the user's conversation content is included in this change. See [ChatGPT token audit documentation](docs/CHATGPT_EXPORT_TOKEN_AUDIT.md).


## Mission-first token amplification

**Outcome depth comes before token reduction.** The default unified, Elite, and HTTP paths now preserve the complete task and evidence context. No automatic 500-byte pointer replacement, 50% context reduction, or 10% retention. Explicit bulk-document offload remains reversible; extractive context compression requires clear opt-in and an original-source receipt. The MCP interface returns actual local results and measurements rather than fixed fixture values. This change does not reveal ChatGPT's hidden token usage or prove that the ChatGPT host has adopted these defaults.

Read [Work Amplification Before Compression](docs/WORK_AMPLIFICATION_BEFORE_COMPRESSION.md), which references the **existing Aspen token-aware execution doctrine** rather than creating a competing policy.
