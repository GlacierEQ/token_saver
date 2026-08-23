import math
from collections import Counter
import re
from .token_counter import estimate_tokens


def score_lines(text: str) -> list[tuple[int, float, str]]:
    """Scores lines based on TF-IDF, position, density, and structure."""
    if not text:
        return []

    lines = text.split('\n')
    num_lines = len(lines)
    if num_lines == 0:
        return []

    # Calculate document frequencies
    doc_freq = Counter()
    words_per_line = []
    
    for line in lines:
        words = re.findall(r'\b\w+\b', line.lower())
        words_per_line.append(words)
        unique_words = set(words)
        for word in unique_words:
            doc_freq[word] += 1

    scores = []
    for i, (line, words) in enumerate(zip(lines, words_per_line)):
        if not line.strip():
            scores.append((i, 0.0, line))
            continue
            
        score = 0.0
        
        # TF-IDF
        line_word_counts = Counter(words)
        for word, count in line_word_counts.items():
            tf = count / max(1, len(words))
            idf = math.log(num_lines / (1 + doc_freq[word]))
            score += tf * idf
            
        # Position weight
        if i == 0 or i == num_lines - 1:
            score += 2.0
            
        # Information density
        if len(words) > 0:
            density = len(set(words)) / len(words)
            score += density
            
        # Structural markers
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('- ') or stripped.startswith('* '):
            score += 1.5
        if '```' in stripped:
            score += 2.0
            
        scores.append((i, score, line))
        
    # Sort descending by score
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def compress(text: str, ratio: float = 0.3, preserve_order: bool = True) -> str:
    """Selects top scoring lines based on ratio."""
    if not text or ratio <= 0:
        return ""
    if ratio >= 1.0:
        return text
        
    lines = text.split('\n')
    target_lines_count = max(1, int(len(lines) * ratio))
    
    scored = score_lines(text)
    selected = scored[:target_lines_count]
    
    if preserve_order:
        selected.sort(key=lambda x: x[0])
        
    return '\n'.join(line for _, _, line in selected)


def compress_to_budget(text: str, max_tokens: int, model: str = 'gpt-4') -> str:
    """Compresses text until it fits within max_tokens."""
    if not text:
        return ""
        
    current_tokens = estimate_tokens(text, model)
    if current_tokens <= max_tokens:
        return text
        
    scored = score_lines(text)
    if not scored:
        return ""
        
    selected_indices = []
    current_text = ""
    
    for i, score, line in scored:
        # Try adding this line
        test_indices = sorted(selected_indices + [i])
        lines = text.split('\n')
        test_text = '\n'.join(lines[idx] for idx in test_indices)
        
        if estimate_tokens(test_text, model) <= max_tokens:
            selected_indices.append(i)
            current_text = test_text
        else:
            # Reached budget
            break
            
    # Always preserve order here
    selected_indices.sort()
    lines = text.split('\n')
    return '\n'.join(lines[idx] for idx in selected_indices)
