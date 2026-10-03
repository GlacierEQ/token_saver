import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.semantic_compressor import score_blocks, compress, compress_to_budget, segment_into_blocks

def test_segment_into_blocks():
    text = "First block\n\n- Bullet\n- Bullet 2\n\n```\nCode 1\nCode 2\n```\n\nLast block"
    blocks = segment_into_blocks(text)
    
    assert len(blocks) == 4
    assert "First block" in blocks[0]
    assert "- Bullet" in blocks[1]
    assert "```\nCode 1\nCode 2\n```" in blocks[2]
    assert "Last block" in blocks[3]

def test_block_segmentation_code_fences():
    text = "Some text\n```python\ndef foo():\n    return 42\n```\nMore text"
    blocks = segment_into_blocks(text)
    assert len(blocks) == 3
    assert blocks[1].strip() == "```python\ndef foo():\n    return 42\n```"
    
def test_score_blocks():
    text = "First block\n\n# Header\n\n- Bullet\n\n```\nCode\n```\n\nLast block"
    scores = score_blocks(text)
    
    assert len(scores) == 5
    # verify sorted descending
    for i in range(len(scores) - 1):
        assert scores[i][1] >= scores[i+1][1]
        
def test_compress():
    text = "Block 1\n\nBlock 2\n\nBlock 3\n\nBlock 4\n\nBlock 5\n\nBlock 6\n\nBlock 7\n\nBlock 8\n\nBlock 9\n\nBlock 10"
    compressed = compress(text, ratio=0.3)
    compressed_blocks = segment_into_blocks(compressed)
    
    assert len(compressed_blocks) == 3

def test_compress_to_budget():
    text = "Block 1\n\nBlock 2\n\nBlock 3\n\nBlock 4\n\nBlock 5\n\nBlock 6\n\nBlock 7\n\nBlock 8\n\nBlock 9\n\nBlock 10"
    
    # max_tokens=10 should fit fewer than 10 blocks
    compressed = compress_to_budget(text, max_tokens=10)
    compressed_blocks = segment_into_blocks(compressed)
    
    assert len(compressed_blocks) < 10
    
    from src.token_counter import estimate_tokens
    assert estimate_tokens(compressed) <= 10

