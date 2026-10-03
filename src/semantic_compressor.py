import math
import re
from collections import Counter
try:
    from .token_counter import estimate_tokens
except (ImportError, ValueError):
    from token_counter import estimate_tokens

def segment_into_blocks(text: str) -> list[str]:
    """Segments text into atomic blocks (fenced code, paragraphs)."""
    blocks = []
    lines = text.splitlines(keepends=True)
    current_block = []
    in_fence = False
    
    for line in lines:
        if line.strip().startswith("```"):
            if in_fence:
                current_block.append(line)
                in_fence = False
                blocks.append("".join(current_block))
                current_block = []
            else:
                if any(x.strip() for x in current_block):
                    blocks.append("".join(current_block))
                    current_block = []
                current_block.append(line)
                in_fence = True
        elif in_fence:
            current_block.append(line)
        elif not line.strip():
            current_block.append(line)
        else:
            if current_block and not current_block[-1].strip():
                if any(x.strip() for x in current_block):
                    blocks.append("".join(current_block))
                    current_block = []
            current_block.append(line)
            
    if current_block:
        blocks.append("".join(current_block))
        
    return [b for b in blocks if b.strip()]

def score_blocks(text: str) -> list[tuple[int, float, str]]:
    """Scores blocks based on TF-IDF, position, density, and structure."""
    if not text:
        return []

    blocks = segment_into_blocks(text)
    num_blocks = len(blocks)
    if num_blocks == 0:
        return []

    doc_freq = Counter()
    words_per_block = []
    
    for block in blocks:
        words = re.findall(r'\b\w+\b', block.lower())
        words_per_block.append(words)
        unique_words = set(words)
        for word in unique_words:
            doc_freq[word] += 1

    scores = []
    for i, (block, words) in enumerate(zip(blocks, words_per_block)):
        if not block.strip():
            scores.append((i, 0.0, block))
            continue
            
        score = 0.0
        
        # TF-IDF
        block_word_counts = Counter(words)
        for word, count in block_word_counts.items():
            tf = count / max(1, len(words))
            idf = math.log(num_blocks / (1 + doc_freq[word]))
            score += tf * idf
            
        # Position weight
        if i == 0 or i == num_blocks - 1:
            score += 2.0
            
        # Information density
        if len(words) > 0:
            density = len(set(words)) / len(words)
            score += density
            
        # Structural markers
        stripped = block.strip()
        if stripped.startswith('#') or stripped.startswith('- ') or stripped.startswith('* '):
            score += 1.5
        if '```' in stripped:
            score += 2.0
            
        scores.append((i, score, block))
        
    # Sort descending by score
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores

def compress(text: str, ratio: float = 0.3, preserve_order: bool = True) -> str:
    """Selects top scoring blocks based on ratio."""
    if not text or ratio <= 0:
        return ""
    if ratio >= 1.0:
        return text
        
    blocks = segment_into_blocks(text)
    target_block_count = max(1, int(len(blocks) * ratio))
    
    scored = score_blocks(text)
    selected = scored[:target_block_count]
    
    if preserve_order:
        selected.sort(key=lambda x: x[0])
        
    return "".join(block for _, _, block in selected)

def compress_to_budget(text: str, max_tokens: int, model: str = 'gpt-4') -> str:
    """Compresses text until it fits within max_tokens."""
    if not text:
        return ""
        
    current_tokens = estimate_tokens(text, model)
    if current_tokens <= max_tokens:
        return text
        
    scored = score_blocks(text)
    if not scored:
        return ""
        
    selected_indices = []
    current_text = ""
    blocks = segment_into_blocks(text)
    
    for i, score, block in scored:
        # Try adding this block
        test_indices = sorted(selected_indices + [i])
        test_text = "".join(blocks[idx] for idx in test_indices)
        
        if estimate_tokens(test_text, model) <= max_tokens:
            selected_indices.append(i)
            current_text = test_text
        else:
            # Reached budget
            break
            
    # Always preserve order here
    selected_indices.sort()
    return "".join(blocks[idx] for idx in selected_indices)


class SemanticCompressor:
    """Object-oriented wrapper around semantic compression utilities."""

    @staticmethod
    def score_blocks(text: str) -> list[tuple[int, float, str]]:
        return score_blocks(text)

    @staticmethod
    def compress(text: str, ratio: float = 0.3, preserve_order: bool = True) -> str:
        return compress(text, ratio=ratio, preserve_order=preserve_order)

    @staticmethod
    def compress_to_budget(text: str, max_tokens: int, model: str = "gpt-4") -> str:
        return compress_to_budget(text, max_tokens=max_tokens, model=model)
