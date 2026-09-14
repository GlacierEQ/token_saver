# token_saver Thread Charter

## Mission

`token_saver` reduces the transport footprint of structured request context while keeping the difference between **lossy compaction** and **reversible externalization** explicit and inspectable.

## Runnable Proof Surface

Run the complete local suite with:

```bash
PYTHONPATH=. pytest -q
```

Run the deterministic standalone proof with:

```bash
PYTHONPATH=. python3 benchmarks/benchmark_token_saver.py --output token_saver_standalone_proof.json
```

The benchmark exercises cache behavior, line-based context compaction, request batching, and SHA-256-backed pointer externalization. It makes no network request.

## Published Capability Surfaces

| Surface | Promise |
|---|---|
| `EliteTokenBridge.batch_requests()` | Groups equivalent request envelopes without mutating caller-owned input; its output states that savings are **not measured**. |
| `EliteTokenBridge.compress_context()` | Performs line-based selection. It is intentionally **lossy** and must not be presented as reversible compression. |
| `pure_pointer.externalize()` / `resolve()` | Stores UTF-8 content under a SHA-256 identity and verifies bytes before resolution; callers can enforce an allowed root. |
| `PromotionAuthority` / `verify_bound_grant()` | Binds a grant to a source revision and proof-receipt digest. Verification now requires an explicitly injected operator secret and fails closed when one is absent. |

## Truth Boundary

This thread demonstrates deterministic byte measurements and reversible source-pointer integrity for local fixtures. It does **not** demonstrate provider-token savings, model-token equivalence, remote storage durability, or authority to mutate an external system.

## Next Capability

Publish an optional Work Amplification request manifest that declares source pointers, byte budgets, lossiness, and expected downstream transformation constraints. This will let `make-it-heavy` consume a token_saver artifact without importing its internals or treating a byte measurement as a claim about model-token economics.
