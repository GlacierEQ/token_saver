# token_saver

A dependency-free Python toolkit for reducing repeated context transfer.

## Verified scope

- `src/pure_pointer.py`: externalizes a payload and returns a compact, hash-bearing pointer.
- `token_saver_elite_core.py`: local JSON cache, SQLite initialization, context sampling, and request batching.
- `benchmarks/benchmark_token_saver.py`: deterministic byte/count benchmarks.
- `integrations/github_facts.py`: optional first integration boundary; disabled unless an injected transport is supplied.

## Run

```bash
python3 benchmarks/benchmark_token_saver.py
python3 -m pytest -q   # if pytest is installed
python3 token_saver_elite_cli.py health
```

The runtime has no third-party dependencies, so installation does not run `pip install`.

## Claims policy

Savings are workload-dependent. This repository reports measured benchmark outputs only; it does not claim a universal percentage, cache-hit rate, latency, or financial savings. External services require explicit configuration and are tested with mocks.
