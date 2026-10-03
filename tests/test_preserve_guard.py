import pytest
from src.preserve_guard import PreserveGuard, BudgetUnmetProtectedError

def test_preserve_guard_detects_constraints():
    guard = PreserveGuard()
    
    cases = [
        "DO NOT delete this file",
        "This MUST be preserved",
        "It is forbidden to do this",
        "never say never",
        "Please PRESERVE this line",
        "commit: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        "URL: https://github.com/google/token_saver",
        "Time: 2026-10-03T11:15:47Z",
        "Case: 1:24-cv-00123-ABC"
    ]
    
    for case in cases:
        assert guard.is_protected(case), f"Failed to protect: {case}"

def test_preserve_guard_allows_safe_lines():
    guard = PreserveGuard()
    assert not guard.is_protected("This is a normal sentence.")
    assert not guard.is_protected("var x = 42;")
    assert not guard.is_protected("Just some logging output")

def test_preserve_guard_enforces_budget_fail_closed():
    guard = PreserveGuard()
    text = "Line 1\nDO NOT DROP THIS\nLine 3"
    
    with pytest.raises(BudgetUnmetProtectedError) as excinfo:
        # If budget can't fit the protected lines, it fails closed
        guard.enforce_budget(text, max_lines=0)
        
    assert "BUDGET_UNMET_PROTECTED" in str(excinfo.value)
    
def test_preserve_guard_fidelity_metric():
    guard = PreserveGuard()
    text = "Line 1\nDO NOT DROP THIS\nLine 3"
    
    # If budget can fit the protected lines, it succeeds and reports recall
    result = guard.enforce_budget(text, max_lines=2)
    assert "DO NOT DROP THIS" in result["text"]
    assert result["protected_recall"] == 1.0

def test_optimize_request_adversarial(tmp_path):
    from token_saver_elite_core import EliteMemoryCache, EliteTokenBridge
    cache = EliteMemoryCache(str(tmp_path))
    bridge = EliteTokenBridge(cache)
    
    # 10 lines total. Ratio = 0.1 means budget is 1 line (but maxed to 3).
    # Still, 5 protected lines means budget (3) is unmet.
    text = "Line 1\n\nDO NOT 2\n\nLine 3\n\nDO NOT 4\n\nLine 5\n\nDO NOT 6\n\nDO NOT 7\n\nDO NOT 8\n\nLine 9\n\nLine 10"
    
    req = {
        "context": text,
        "compression_ratio": 0.1
    }
    
    opt = bridge.optimize_request(req)
    
    # Check that it fell back to pointer offload
    assert opt["status"] == "BUDGET_UNMET_PROTECTED"
    assert opt["context"].startswith("[ptr:sha256://")
    assert opt["measurement"]["protected_recall"] == 1.0
