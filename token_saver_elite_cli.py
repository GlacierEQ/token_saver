"""Token Saver command-line interface."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from token_saver_elite_core import Elite, TokenSaverElite, log_elite


class EliteCLI:
    def __init__(self):
        self.ts = TokenSaverElite()

    def cmd_status(self, args=None):
        self.ts.report()

    def cmd_health(self, args=None):
        cache = self.ts.status()["cache"]
        total = cache["hits"] + cache["misses"]
        print(f"\n{Elite.BOLD}=== HEALTH CHECK ==={Elite.END}\n")
        print(f"Cache entries: {cache['valid']} valid, {cache['expired']} expired")
        print(f"Hits/misses:   {cache['hits']}/{cache['misses']}")
        print(f"Hit rate:      {(cache['hits'] / total * 100) if total else 0:.1f}%")
        print(f"Measured bytes saved: {cache['measured_bytes_saved']}")
        print(f"Measurement unit:     {cache['measurement_unit']}")
        print(f"Disk usage:           {cache['disk_size_kb']} KB\n")

    def cmd_cache_set(self, args):
        if len(args) < 2:
            log_elite("Usage: cache_set KEY VALUE [TTL_SECONDS]", "ERROR")
            return
        try:
            ttl = int(args[2]) if len(args) > 2 else 3600
        except ValueError:
            log_elite("TTL_SECONDS must be a valid integer", "ERROR")
            return
        if self.ts.cache.set(args[0], args[1], ttl=ttl, source="cli"):
            log_elite(f"Cached '{args[0]}' (TTL: {ttl}s)", "SUCCESS")
        else:
            log_elite(f"Could not persist cache entry '{args[0]}'", "ERROR")

    def cmd_cache_get(self, args):
        if not args:
            log_elite("Usage: cache_get KEY", "ERROR")
            return
        value = self.ts.cache.get(args[0])
        if value is None:
            log_elite(f"Cache miss: {args[0]}", "WARN")
        else:
            print(json.dumps(value, indent=2, default=str))

    def cmd_optimize(self, args):
        if not args:
            log_elite("Usage: optimize QUERY_STRING", "ERROR")
            return
        result = self.ts.bridge.optimize_request({"query": " ".join(args)})
        print(json.dumps(result, indent=2, default=str))

    def cmd_clean(self, args=None):
        before = len(self.ts.cache.memory)
        self.ts.cache.memory = {
            key: value
            for key, value in self.ts.cache.memory.items()
            if not value.is_expired()
        }
        self.ts.cache._save_cache()
        log_elite(
            f"Cleaned {before - len(self.ts.cache.memory)} expired entries",
            "SUCCESS",
        )

    def cmd_export(self, args):
        output = Path(args[0]) if args else self.ts.home / "cache_export.json"
        data = {
            "version": self.ts.VERSION,
            "exported_at": datetime.now(UTC).isoformat(),
            "cache": {
                key: value.to_dict() for key, value in self.ts.cache.memory.items()
            },
            "stats": self.ts.cache.stats,
        }
        output.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )
        log_elite(f"Cache exported to {output}", "SUCCESS")

    def cmd_sovereign_externalize(self, args):
        if not args:
            log_elite("Usage: sovereign_externalize LABEL CONTENT", "ERROR")
            return
        label = args[0]
        content = " ".join(args[1:]) if len(args) > 1 else sys.stdin.read()
        from src.sovereign_bridge import SovereignTokenBridge
        bridge = SovereignTokenBridge(storage_dir=self.ts.home / "token_saver_work")
        receipt = bridge.externalize_payload(label, content)
        print(json.dumps(receipt.to_dict(), indent=2))

    def cmd_unified_optimize(self, args):
        if not args:
            log_elite("Usage: unified_optimize JSON_PAYLOAD_OR_FILE", "ERROR")
            return
        raw = " ".join(args)
        if Path(raw).exists():
            payload = json.loads(Path(raw).read_text(encoding="utf-8"))
        else:
            payload = json.loads(raw)
        from src.unified_token_engine import UnifiedTokenEngine
        engine = UnifiedTokenEngine(work_dir=self.ts.home / "token_saver_work")
        res = engine.optimize_message_payload(payload)
        print(json.dumps(res, indent=2))

    def cmd_benchmark(self, args=None):
        try:
            from benchmarks.benchmark_token_saver import run_all_benchmarks as run_bench
        except ImportError:
            from benchmarks.benchmark_token_saver import run as run_bench
        results = run_bench()
        print(json.dumps(results, indent=2))

    def cmd_help(self, args=None):
        print(f"\n{Elite.BOLD}{Elite.CYAN}TOKEN_SAVER v{self.ts.VERSION}{Elite.END}\n")
        print(
            "  status | health | cache_set | cache_get | optimize |\n"
            "  sovereign_externalize | unified_optimize | benchmark |\n"
            "  clean | export | help"
        )

    def run(self, args):
        if not args:
            return self.cmd_help()
        method = getattr(self, f"cmd_{args[0].replace('-', '_')}", None)
        if method:
            return method(args[1:])
        log_elite(f"Unknown command: {args[0]}", "ERROR")
        return self.cmd_help()


def main():
    EliteCLI().run(sys.argv[1:])


if __name__ == "__main__":
    main()
