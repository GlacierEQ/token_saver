import math
from dataclasses import dataclass
import re

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


@dataclass
class TokenBudget:
    """Represents a budget for tokens."""
    max_tokens: int
    used_tokens: int = 0

    @property
    def remaining(self) -> int:
        return self.max_tokens - self.used_tokens


@dataclass
class TokenMeasurement:
    """Measurement of token savings."""
    tokens_before: int
    tokens_after: int
    tokens_saved: int
    savings_pct: float
    model: str
    measurement_method: str = 'heuristic_v1'


def detect_content_type(text: str) -> str:
    """Detects content type to adjust heuristics."""
    if not text:
        return "english"

    # Count characteristics
    json_chars = text.count('{') + text.count('}') + text.count('"') + text.count(':')
    code_chars = len(re.findall(r'\b(def|class|function|import|return)\b', text)) * 5 + text.count('(') + text.count(';')
    
    length = max(1, len(text))
    
    if json_chars / length > 0.05:
        return "json"
    if code_chars / length > 0.02:
        return "code"
    
    return "english"


def estimate_tokens(text: str, model: str = 'gpt-4') -> int:
    """Estimates token count using character-based heuristics or tiktoken."""
    if HAS_TIKTOKEN:
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except KeyError:
            pass # fallback to heuristic if model not found

    content_type = detect_content_type(text)
    
    if content_type == "json":
        chars_per_token = 3.0
    elif content_type == "code":
        chars_per_token = 3.5
    else:
        chars_per_token = 4.0

    return max(1, int(math.ceil(len(text) / chars_per_token))) if text else 0


def measure_token_savings(before: str, after: str, model: str = 'gpt-4') -> TokenMeasurement:
    """Measures token savings between two strings."""
    tokens_before = estimate_tokens(before, model)
    tokens_after = estimate_tokens(after, model)
    
    tokens_saved = tokens_before - tokens_after
    savings_pct = (tokens_saved / tokens_before * 100.0) if tokens_before > 0 else 0.0
    
    method = 'tiktoken' if HAS_TIKTOKEN else 'heuristic_v1'
    
    return TokenMeasurement(
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        tokens_saved=tokens_saved,
        savings_pct=savings_pct,
        model=model,
        measurement_method=method
    )
