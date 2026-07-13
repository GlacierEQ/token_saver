import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'benchmarks'))
from benchmark_token_saver import run

def test_deterministic_benchmarks():
    result = run()
    assert result['cache_hit_miss'] == {'miss_is_none': True, 'hit_value': {'answer': 42}, 'hits': 1, 'misses': 1, 'tokens_saved': 50}
    assert result['compression'] == {'input_lines': 100, 'output_lines': 12, 'input_bytes': 2889, 'output_bytes': 337}
    assert result['batching'] == {'input_requests': 3, 'output_requests': 1, 'before': 300, 'after': 210}
    assert result['pointer_externalization']['bytes_in'] == 6000
    assert result['pointer_externalization']['bytes_out'] == 58
    assert result['pointer_externalization']['savings_pct'] == 99.03
