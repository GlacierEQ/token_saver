#!/usr/bin/env python3
"""Token Saver v3.0 command-line interface."""
import sys
import json
from pathlib import Path
from datetime import datetime

# Import the sibling core from this repository, not from /tmp.
_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from token_saver_elite_core import (  # noqa: E402
    TokenSaverElite, Elite, log_elite
)

class EliteCLI:
    def __init__(self):
        self.ts = TokenSaverElite()

    def cmd_status(self, args=None):
        self.ts.report()

    def cmd_health(self, args=None):
        status = self.ts.status()
        cache = status['cache']
        total = cache['hits'] + cache['misses']
        print(f"\n{Elite.BOLD}=== HEALTH CHECK ==={Elite.END}\n")
        print(f"Cache entries: {cache['valid']} valid, {cache['expired']} expired")
        print(f"Hits/misses:   {cache['hits']}/{cache['misses']}")
        print(f"Hit rate:      {(cache['hits'] / total * 100) if total else 0:.1f}%")
        print(f"Tokens saved:  {cache['tokens_saved']}")
        print(f"Disk usage:    {cache['disk_size_kb']} KB\n")

    def cmd_cache_set(self, args):
        if len(args) < 2:
            log_elite('Usage: cache_set KEY VALUE [TTL_SECONDS]', 'ERROR'); return
        ttl = int(args[2]) if len(args) > 2 else 3600
        self.ts.cache.set(args[0], args[1], ttl=ttl, source='cli')
        log_elite(f"Cached '{args[0]}' (TTL: {ttl}s)", 'SUCCESS')

    def cmd_cache_get(self, args):
        if not args:
            log_elite('Usage: cache_get KEY', 'ERROR'); return
        value = self.ts.cache.get(args[0])
        if value is None:
            log_elite(f'Cache miss: {args[0]}', 'WARN')
        else:
            print(json.dumps(value, indent=2, default=str))

    def cmd_optimize(self, args):
        if not args:
            log_elite('Usage: optimize QUERY_STRING', 'ERROR'); return
        request = {'query': ' '.join(args), 'tokens': 250}
        result = self.ts.bridge.optimize_request(request)
        print(json.dumps(result, indent=2, default=str))

    def cmd_batch(self, args):
        requests = [
            {'type': 'query', 'model': 'local', 'query': 'What is token optimization?', 'tokens': 150},
            {'type': 'query', 'model': 'local', 'query': 'Explain distributed memory', 'tokens': 160},
            {'type': 'query', 'model': 'local', 'query': 'How does caching work?', 'tokens': 140},
        ]
        print(json.dumps(self.ts.bridge.batch_requests(requests), indent=2))

    def cmd_clean(self, args):
        before = len(self.ts.cache.memory)
        self.ts.cache.memory = {k: v for k, v in self.ts.cache.memory.items() if not v.is_expired()}
        self.ts.cache._save_cache()
        log_elite(f'Cleaned {before - len(self.ts.cache.memory)} expired entries', 'SUCCESS')

    def cmd_export(self, args):
        output = Path(args[0]) if args else self.ts.home / 'cache_export.json'
        data = {'version': self.ts.VERSION, 'case': self.ts.CASE_ID,
                'exported_at': datetime.now().isoformat(),
                'cache': {k: v.to_dict() for k, v in self.ts.cache.memory.items()},
                'stats': self.ts.cache.stats}
        output.write_text(json.dumps(data, indent=2, default=str))
        log_elite(f'Cache exported to {output}', 'SUCCESS')

    def cmd_help(self, args=None):
        print(f'\n{Elite.BOLD}{Elite.CYAN}TOKEN_SAVER v{self.ts.VERSION}{Elite.END}\n')
        for command, description in {
            'status': 'Show status', 'health': 'Run health checks',
            'cache_set KEY VALUE [TTL]': 'Store a value', 'cache_get KEY': 'Retrieve a value',
            'optimize QUERY': 'Optimize one request', 'batch': 'Batch sample requests',
            'clean': 'Remove expired entries', 'export [PATH]': 'Export cache', 'help': 'Show help'
        }.items():
            print(f'  {command:<28} {description}')

    def run(self, args):
        if not args: return self.cmd_help()
        method = getattr(self, f"cmd_{args[0].replace('-', '_')}", None)
        if method: return method(args[1:])
        log_elite(f'Unknown command: {args[0]}', 'ERROR'); self.cmd_help()

def main():
    EliteCLI().run(sys.argv[1:])

if __name__ == '__main__':
    main()
