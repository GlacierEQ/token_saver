import threading
from src.metrics import MetricsRegistry

def test_counter():
    reg = MetricsRegistry()
    c = reg.counter("my_counter", {"app": "test"})
    c.inc()
    c.inc(2)
    out = reg.expose()
    assert 'my_counter{app="test"} 3.0' in out

def test_gauge():
    reg = MetricsRegistry()
    g = reg.gauge("my_gauge")
    g.set(10)
    g.inc(5)
    g.dec(2)
    out = reg.expose()
    assert 'my_gauge 13' in out

def test_histogram():
    reg = MetricsRegistry()
    h = reg.histogram("my_hist")
    h.observe(0.05)
    h.observe(0.05)
    h.observe(0.1)
    
    out = reg.expose()
    assert 'my_hist_bucket{le="0.05"} 2' in out
    assert 'my_hist_bucket{le="0.1"} 3' in out
    assert 'my_hist_sum 0.2' in out
    assert 'my_hist_count 3' in out

def test_thread_safety():
    reg = MetricsRegistry()
    c = reg.counter("ts_counter")
    
    def worker():
        for _ in range(100):
            c.inc()
            
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert c.value == 1000.0
