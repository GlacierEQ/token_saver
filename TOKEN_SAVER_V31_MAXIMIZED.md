# Token Saver — measured implementation status

This file supersedes earlier v3.1+ marketing language. The repository currently contains a v3.0 local-cache core plus a measured pure-pointer utility; it does not contain a verified Mem0, Notion, multi-model, or distributed GitHub implementation.

## Implemented

- Local JSON cache with TTL and hit/miss counters.
- SQLite schema initialization for future statistics.
- Deterministic context sampling and same-type/model request batching.
- `pure_pointer` externalization with SHA-256 provenance pointer.
- Optional, read-only GitHub fact-store boundary using an injected transport.

## Measured benchmark fixture

Run:

```bash
python3 benchmarks/benchmark_token_saver.py
```

The fixture measures byte/count behavior, not wall-clock speed or universal token savings:

| Workload | Fixture result |
|---|---:|
| Cache miss then hit | 1 miss, 1 hit, 50 internal accounting tokens saved |
| Context sampling | 100 input lines → 12 output lines; 3,089 → 369 bytes |
| Same-type/model batching | 3 requests → 1; 300 → 210 estimated tokens |
| Pointer externalization | 6,000 → 58 bytes; 99.03% byte reduction |

These are reproducible fixture results, not guarantees for arbitrary workloads. No claim is made for overall 95–99% savings, cache-hit rates, latency, or financial savings.

## Optional integrations

Credentials are never embedded. The GitHub boundary remains disabled unless a transport is explicitly injected. Its tests use a mock transport and make no network calls. Additional integrations should follow the same pattern, one at a time, with explicit tests and measured behavior.
