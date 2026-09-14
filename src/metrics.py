import threading
from typing import Dict, List, Optional

class Metric:
    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.labels = labels or {}
        self.lock = threading.Lock()

    def _render_labels(self, extra: Optional[Dict[str, str]] = None) -> str:
        all_labels = self.labels.copy()
        if extra:
            all_labels.update(extra)
        if not all_labels:
            return ""
        label_strs = [f'{k}="{v}"' for k, v in all_labels.items()]
        return "{" + ",".join(label_strs) + "}"

class Counter(Metric):
    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None):
        super().__init__(name, labels)
        self.value = 0.0

    def inc(self, amount: float = 1.0):
        with self.lock:
            if amount < 0:
                raise ValueError("Counters can only increment")
            self.value += amount

    def render(self) -> str:
        with self.lock:
            val = self.value
        return f"{self.name}{self._render_labels()} {val}"

class Gauge(Metric):
    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None):
        super().__init__(name, labels)
        self.value = 0.0

    def set(self, value: float):
        with self.lock:
            self.value = value

    def inc(self, amount: float = 1.0):
        with self.lock:
            self.value += amount

    def dec(self, amount: float = 1.0):
        with self.lock:
            self.value -= amount

    def render(self) -> str:
        with self.lock:
            val = self.value
        return f"{self.name}{self._render_labels()} {val}"

class Histogram(Metric):
    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None):
        super().__init__(name, labels)
        self.sum = 0.0
        self.count = 0
        self.buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')]
        self.bucket_counts = {b: 0 for b in self.buckets}

    def observe(self, value: float):
        with self.lock:
            self.sum += value
            self.count += 1
            for b in self.buckets:
                if value <= b:
                    self.bucket_counts[b] += 1

    def render(self) -> str:
        lines = []
        with self.lock:
            for b in self.buckets:
                b_str = "+Inf" if b == float('inf') else str(b)
                lines.append(f"{self.name}_bucket{self._render_labels({'le': b_str})} {self.bucket_counts[b]}")
            lines.append(f"{self.name}_sum{self._render_labels()} {self.sum}")
            lines.append(f"{self.name}_count{self._render_labels()} {self.count}")
        return "\n".join(lines)

class MetricsRegistry:
    def __init__(self):
        self.metrics: List[Metric] = []
        self.lock = threading.Lock()

    def counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> Counter:
        with self.lock:
            c = Counter(name, labels)
            self.metrics.append(c)
            return c

    def gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Gauge:
        with self.lock:
            g = Gauge(name, labels)
            self.metrics.append(g)
            return g

    def histogram(self, name: str, labels: Optional[Dict[str, str]] = None) -> Histogram:
        with self.lock:
            h = Histogram(name, labels)
            self.metrics.append(h)
            return h

    def expose(self) -> str:
        with self.lock:
            metrics_copy = list(self.metrics)
        lines = []
        for m in metrics_copy:
            lines.append(m.render())
        return "\n".join(lines)

# Pre-register metrics
registry = MetricsRegistry()
registry.counter("token_saver_cache_hits_total")
registry.counter("token_saver_cache_misses_total")
registry.counter("token_saver_bytes_saved_total")
registry.counter("token_saver_tokens_saved_total")
registry.histogram("token_saver_optimization_duration_seconds")
registry.gauge("token_saver_active_peers")
