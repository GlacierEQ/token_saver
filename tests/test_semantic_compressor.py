import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.semantic_compressor import score_lines, compress, compress_to_budget

def test_score_lines():
    text = "First line\n# Header\n- Bullet\n```\nCode\n```\nLast line"
    scores = score_lines(text)
    
    assert len(scores) == 7
    # verify sorted descending
    for i in range(len(scores) - 1):
        assert scores[i][1] >= scores[i+1][1]
        
    # verify structural markers
    line_scores = {line: score for _, score, line in scores}
    assert line_scores['# Header'] > 0
    assert line_scores['```'] > 0

def test_compress():
    text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8\nLine 9\nLine 10"
    compressed = compress(text, ratio=0.3)
    compressed_lines = compressed.split('\n')
    
    assert len(compressed_lines) == 3
    
    # check preserve order
    # By default preserve_order=True
    indices = [int(line.split(' ')[1]) for line in compressed_lines]
    assert indices == sorted(indices)

def test_compress_to_budget():
    text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8\nLine 9\nLine 10"
    
    # We want max tokens = 4, which is about 16 characters for english
    compressed = compress_to_budget(text, max_tokens=4)
    compressed_lines = compressed.split('\n')
    
    assert len(compressed_lines) < 10
    
    from src.token_counter import estimate_tokens
    assert estimate_tokens(compressed) <= 4
