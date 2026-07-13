#!/usr/bin/env python3
"""Deterministic, dependency-free Token Saver benchmark suite.

These are byte/count benchmarks, not wall-clock performance claims.
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from pure_pointer import externalize, measure
from token_saver_elite_core import EliteMemoryCache, EliteTokenBridge

def run():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / 'cache'
        cache = EliteMemoryCache(str(home))
        bridge = EliteTokenBridge(cache)

        miss = cache.get('missing')
        cache.set('known', {'answer': 42}, ttl=3600, source='benchmark')
        hit = cache.get('known')
        cache_result = {'miss_is_none': miss is None, 'hit_value': hit,
                        'hits': cache.stats['hits'], 'misses': cache.stats['misses'],
                        'tokens_saved': cache.stats['tokens_saved']}

        context = '\n'.join(f'line-{i}: deterministic context' for i in range(100))
        compressed = bridge.compress_context(context, compression_ratio=0.1)
        compression_result = {'input_lines': len(context.splitlines()),
                              'output_lines': len(compressed.splitlines()),
                              'input_bytes': len(context.encode()),
                              'output_bytes': len(compressed.encode())}

        requests = [{'type': 'query', 'model': 'local', 'query': f'q{i}', 'tokens': 100} for i in range(3)]
        batched = bridge.batch_requests(requests)
        batching_result = {'input_requests': len(requests), 'output_requests': len(batched),
                           'before': batched[0]['token_estimate_before'],
                           'after': batched[0]['token_estimate_after']}

        pointer = externalize('hello world ' * 500, Path(tmp) / 'pointers')
        pointer_result = measure(pointer)
        return {'cache_hit_miss': cache_result, 'compression': compression_result,
                'batching': batching_result, 'pointer_externalization': pointer_result}

if __name__ == '__main__':
    print(json.dumps(run(), indent=2, sort_keys=True))
