# token_saver

A dependency-free Python toolkit for reducing repeated context transfer.

## Verified scope

- `src/pure_pointer.py` externalizes a UTF-8 payload under an allowed local
  root, returns a full SHA-256 content URI, and verifies the hash on resolve.
- `token_saver_elite_core.py` provides an atomic local cache, SHA-256 request
  identity, non-mutating context sampling and request grouping.
- Measurements are canonical UTF-8 byte counts. They are not token estimates.
- Repeated optimized requests are read from the persisted cache.

## Run

```bash
python3 -m unittest discover -s tests -v
python3 benchmarks/benchmark_token_saver.py
python3 token_saver_elite_cli.py health
```

The runtime has no third-party dependencies. Pytest is only needed for the test
suite.

## Claims policy

Savings are workload-dependent. Report only measured benchmark outputs. Do not
claim a universal percentage, cache-hit rate, latency reduction, financial
savings, or fixed tokens saved per cache hit.

The optimizer never treats byte reduction as an exact token count. External
services require explicit configuration and mocked tests before activation.

---

## Fleet ops (transparent)

This repo may include **`.integrity/`** (SHA-256 baselines / watchdog) and/or a health sidecar.
These are **documented multi-repo fleet operations**, not covert implants.

See [SECURITY_AND_FLEET_OPS.md](SECURITY_AND_FLEET_OPS.md) and
`~/GlacierEQ_Swarm/state/PORTFOLIO_SHADOW_AND_GAUNTLET.md`.

## Helix strand

See [HELIX_STRAND.md](HELIX_STRAND.md) — piston/spiral role in the portfolio double helix.
