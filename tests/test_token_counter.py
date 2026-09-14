import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.token_counter import (
    estimate_tokens, 
    TokenBudget, 
    measure_token_savings, 
    detect_content_type
)

def test_detect_content_type():
    english_text = "This is a simple english sentence."
    json_text = '{"key": "value", "key2": {"nested": "value"}}'
    code_text = "def hello_world():\n    return 'hello'\nclass Foo:\n    pass\n"
    
    assert detect_content_type(english_text) == "english"
    assert detect_content_type(json_text) == "json"
    assert detect_content_type(code_text) == "code"

def test_estimate_tokens():
    text = "Hello world! This is a test string."
    count = estimate_tokens(text)
    # length is 35. English ratio 4. 35/4 = 8.75 -> 9. 
    # check within 2x
    assert 4 <= count <= 18
    
    code = "def test():\n  pass"
    count_code = estimate_tokens(code)
    assert count_code > 0

def test_token_budget():
    budget = TokenBudget(max_tokens=100)
    assert budget.max_tokens == 100
    assert budget.used_tokens == 0
    assert budget.remaining == 100
    
    budget.used_tokens = 30
    assert budget.remaining == 70

def test_measure_token_savings():
    before = "A very long string that goes on and on and on."
    after = "A very long string."
    
    measurement = measure_token_savings(before, after)
    
    assert measurement.tokens_before > measurement.tokens_after
    assert measurement.tokens_saved > 0
    assert 0 < measurement.savings_pct <= 100
    assert measurement.model == 'gpt-4'
