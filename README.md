# Token Saver v4.0 — Distributed Context Optimization Engine

**Dependency-free, measurement-honest, distributed token optimization for LLM agent infrastructure.**

Zero external dependencies. 52 tests. Every claim is measured.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
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
| **Token Counter** | `src/token_counter.py` | Estimates LLM token counts via calibrated character ratios. Falls back to exact `tiktoken` counts when available. |
| **Semantic Compressor** | `src/semantic_compressor.py` | TF-IDF weighted line scoring with structural marker bonuses. Selects most important lines within a token budget. |
| **Pure Pointer** | `src/pure_pointer.py` | Content-addressed file offloading. SHA-256 integrity verification. Path traversal rejection. |
| **Elite Cache** | `token_saver_elite_core.py` | In-memory JSON cache with atomic disk persistence, TTL expiration, and rollback on write failure. |
| **SQLite Audit Log** | `token_saver_elite_core.py` | Records every optimization event with bytes/tokens before/after and compression method. |
| **Promotion Authority** | `src/promotion_authority.py` | HMAC-SHA256 signed promotion grants with expiration and proof receipt verification. |
| **HTTP Gateway** | `server/gateway.py` | ThreadingHTTPServer exposing cache, optimization, health, and Prometheus metrics endpoints. |
| **Peer Discovery** | `server/discovery.py` | UDP broadcast/listen for LAN peer discovery with stale timeout. |
| **Consistent Hash Ring** | `server/mesh.py` | Distributes cache keys across peers with configurable virtual nodes and N-replica replication. |
| **MCP Tool Server** | `mcp/server.py` | JSON-RPC 2.0 MCP server with 4 tools for agent integration. |
| **Integrity Watchdog** | `src/watchdog.py` | SHA-256 file monitoring with polling loop and change callbacks. |
| **Prometheus Metrics** | `src/metrics.py` | Thread-safe counters, gauges, and histograms in Prometheus text exposition format. |
| **Mastermind Sidecar** | `mastermind_sidecar.py` | Real process monitor: PID, memory, uptime, cache health, disk space, database status. |

## Benchmark (Deterministic Fixture)

| Workload | Result |
|---|---|
| Cache miss → hit | 1 miss, 1 hit, 50 internal accounting tokens saved |
| Context sampling | 100 input lines → 12 output lines; 3,089 → 369 bytes |
| Same-type/model batching | 3 requests → 1; 300 → 210 estimated tokens |
| Pointer externalization | 6,000 → 58 bytes; 99.03% byte reduction |

These are reproducible fixture results, not guarantees for arbitrary workloads.

## Quick Start

```bash
# Run the cache + optimization engine
python3 token_saver_elite_core.py

# Start the HTTP gateway
python3 -m server.gateway --port 8400

# Start the MCP tool server (for agent integration)
python3 -m mcp.server

# Run the integrity watchdog
python3 -m src.watchdog

# Run all 52 tests
python3 -m pytest tests/ -v
```

## Dependency Strategy

```
Core engine: Zero external dependencies (stdlib only)
Optional:    tiktoken (exact GPT token counts)
```

## Test Coverage

52 tests across 13 test files. All assertions are real — no stubs, no `return True`, no in-test simulators.

## License

See [LICENSE](LICENSE).
