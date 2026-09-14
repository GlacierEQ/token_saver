import json
import time
from pathlib import Path
from src.watchdog import IntegrityWatchdog

def test_watchdog_baseline(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.log"
    f1.write_text("hello")
    f2.write_text("world")

    wd = IntegrityWatchdog(tmp_path, ["*.txt", "*.log"])
    baseline = wd.compute_baseline()
    assert "a.txt" in baseline
    assert "b.log" in baseline

def test_watchdog_verify(tmp_path):
    f1 = tmp_path / "a.txt"
    f1.write_text("hello")

    wd = IntegrityWatchdog(tmp_path, ["*.txt"])
    baseline = wd.compute_baseline()

    res = wd.verify(baseline)
    assert res.passed
    assert res.unchanged == ["a.txt"]

    f1.write_text("hello world")
    res = wd.verify(baseline)
    assert not res.passed
    assert res.modified == ["a.txt"]

    f2 = tmp_path / "c.txt"
    f2.write_text("new")
    res = wd.verify(baseline)
    assert not res.passed
    assert "c.txt" in res.added

    f1.unlink()
    res = wd.verify(baseline)
    assert not res.passed
    assert "a.txt" in res.removed

def test_watchdog_watch_loop(tmp_path):
    f1 = tmp_path / "a.txt"
    f1.write_text("hello")

    wd = IntegrityWatchdog(tmp_path, ["*.txt"])
    
    events = []
    def cb(res):
        events.append(res)
    
    wd.watch(interval=0.1, callback=cb)
    time.sleep(0.2)
    f1.write_text("hello modified")
    time.sleep(0.2)
    wd.stop()
    
    assert len(events) > 0
    assert "a.txt" in events[0].modified
