import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List

@dataclass
class VerifyResult:
    passed: bool
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)

class IntegrityWatchdog:
    def __init__(self, root: Path | str, patterns: List[str]):
        self.root = Path(root)
        self.patterns = patterns
        self._stop_event = threading.Event()
        self._watch_thread = None

    def _get_files(self) -> List[Path]:
        files = []
        for pattern in self.patterns:
            files.extend(self.root.rglob(pattern))
        return list(set(f for f in files if f.is_file()))

    def _hash_file(self, path: Path) -> str:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def compute_baseline(self) -> Dict[str, str]:
        baseline = {}
        for f in self._get_files():
            rel_path = str(f.relative_to(self.root))
            baseline[rel_path] = self._hash_file(f)
        return baseline

    def save_baseline(self, path: Path | str):
        baseline = self.compute_baseline()
        with open(path, "w") as f:
            json.dump(baseline, f, indent=2)

    def load_baseline(self, path: Path | str) -> Dict[str, str]:
        with open(path, "r") as f:
            return json.load(f)

    def verify(self, baseline: Dict[str, str]) -> VerifyResult:
        current = self.compute_baseline()
        added = []
        removed = []
        modified = []
        unchanged = []

        for path, file_hash in current.items():
            if path not in baseline:
                added.append(path)
            elif baseline[path] != file_hash:
                modified.append(path)
            else:
                unchanged.append(path)

        for path in baseline:
            if path not in current:
                removed.append(path)

        passed = not bool(added or removed or modified)
        return VerifyResult(passed, added, removed, modified, unchanged)

    def watch(self, interval: float = 5.0, callback: Callable = None):
        baseline = self.compute_baseline()
        self._stop_event.clear()

        def loop():
            while not self._stop_event.is_set():
                res = self.verify(baseline)
                if not res.passed and callback:
                    callback(res)
                # Note: Do not auto-update baseline to avoid self-fulfilling bug!
                time.sleep(interval)

        self._watch_thread = threading.Thread(target=loop, daemon=True)
        self._watch_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._watch_thread:
            self._watch_thread.join()
