#!/usr/bin/env python3
"""
🚀 TOKEN_SAVER v3.0 CLI — Elite Command Interface
Author: Casey Barton | GlacierEQ
Status: Tier-1 Bulletproof with Full Observability
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import subprocess

# Import elite core
sys.path.insert(0, '/tmp')
from token_saver_elite_core import (
    TokenSaverElite, Elite, log_elite, EliteMemoryCache, EliteTokenBridge
)

class EliteCLI:
    """Master command interface"""
    
    def __init__(self):
        self.ts = TokenSaverElite()
    
    def cmd_status(self, args=None):
        """❌ Show elite status"""
        self.ts.report()
    
    def cmd_health(self, args=None):
        """🏥 Full health check with diagnostics"""
        print(f"\n{Elite.BOLD}=== HEALTH CHECK ==={Elite.END}\n")
        
        status = self.ts.status()
        print(f"✅ Cache:        {status['cache']['valid']} valid entries")
        print(f"⚠️  Expired:      {status['cache']['expired']} expired (cleanup needed)")
        print(f"📊 Efficiency:   {status['cache']['hits']} hits / {status['cache']['hits'] + status['cache']['misses']} total")
        
        if status['cache']['hits'] + status['cache']['misses'] > 0:
            hit_rate = (status['cache']['hits'] / (status['cache']['hits'] + status['cache']['misses'])) * 100
            print(f"💾 Hit rate:     {hit_rate:.1f}%")
        
        print(f"🎯 Tokens saved: {status['cache']['tokens_saved']}")
        print(f"📁 Disk usage:   {status['cache']['disk_size_kb']} KB\n")
    
    def cmd_cache_set(self, args):
        """💾 Store a key-value pair: cache_set KEY VALUE [TTL]"""
        if len(args) < 2:
            log_elite("Usage: cache_set KEY VALUE [TTL_SECONDS]", "ERROR")
            return
        
        key = args[0]
        value = args[1]
        ttl = int(args[2]) if len(args) > 2 else 3600
        
        self.ts.cache.set(key, value, ttl=ttl, source="cli")
        log_elite(f"✅ Cached '{key}' (TTL: {ttl}s)", "SUCCESS")
    
    def cmd_cache_get(self, args):
        """🔍 Retrieve a cached value: cache_get KEY"""
        if not args:
            log_elite("Usage: cache_get KEY", "ERROR")
            return
        
        key = args[0]
        value = self.ts.cache.get(key)
        
        if value is None:
            log_elite(f"Cache miss: {key}", "WARN")
        else:
            print(f"\n{Elite.GREEN}✅ Found: {key}{Elite.END}")
            print(f"{json.dumps(value, indent=2, default=str)}\n")
    
    def cmd_optimize(self, args):
        """⚡ Optimize a request"""
        if not args:
            log_elite("Usage: optimize QUERY_STRING", "ERROR")
            return
        
        query = " ".join(args)
        request = {"query": query, "tokens": 250}
        
        optimized = self.ts.bridge.optimize_request(request)
        
        print(f"\n{Elite.CYAN}=== OPTIMIZATION RESULT ==={Elite.END}")
        print(f"Original tokens:  {optimized.get('original_tokens', request['tokens'])}")
        print(f"Optimized tokens: {optimized.get('optimized_tokens', request['tokens'] - optimized.get('tokens_saved', 0))}")
        print(f"Tokens saved:     {Elite.GREEN}{optimized.get('tokens_saved', 0)}{Elite.END}")
        print(f"Cached:           {Elite.GREEN if optimized.get('cached') else Elite.YELLOW}{optimized.get('cached', False)}{Elite.END}\n")
    
    def cmd_batch(self, args):
        """🎯 Batch optimize multiple requests"""
        requests = [
            {"type": "query", "model": "gemini", "query": "What is token optimization?", "tokens": 150},
            {"type": "query", "model": "gemini", "query": "Explain distributed memory", "tokens": 160},
            {"type": "query", "model": "gemini", "query": "How does caching work?", "tokens": 140},
        ]
        
        optimized = self.ts.bridge.batch_requests(requests)
        
        print(f"\n{Elite.CYAN}=== BATCH OPTIMIZATION ==={Elite.END}")
        print(f"Input requests:  {len(requests)}")
        print(f"Batched requests: {len(optimized)}\n")
        
        total_before = sum(r.get("token_estimate_before", 0) for r in optimized)
        total_after = sum(r.get("token_estimate_after", 0) for r in optimized)
        
        print(f"Total before:    {total_before} tokens")
        print(f"Total after:     {total_after} tokens")
        print(f"Total saved:     {Elite.GREEN}{total_before - total_after} tokens{Elite.END}")
        print(f"Efficiency:      {Elite.GREEN}{((total_before - total_after) / total_before * 100):.1f}%{Elite.END}\n")
    
    def cmd_clean(self, args):
        """🧹 Remove expired cache entries"""
        before = len(self.ts.cache.memory)
        self.ts.cache.memory = {
            k: v for k, v in self.ts.cache.memory.items() 
            if not v.is_expired()
        }
        after = len(self.ts.cache.memory)
        self.ts.cache._save_cache()
        
        log_elite(f"Cleaned {before - after} expired entries", "SUCCESS")
    
    def cmd_export(self, args):
        """📤 Export cache as JSON"""
        output_path = Path(args[0]) if args else self.ts.home / "cache_export.json"
        
        data = {
            "version": self.ts.VERSION,
            "case": self.ts.CASE_ID,
            "exported_at": datetime.now().isoformat(),
            "cache": {k: v.to_dict() for k, v in self.ts.cache.memory.items()},
            "stats": self.ts.cache.stats
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        log_elite(f"Cache exported to {output_path}", "SUCCESS")
    
    def cmd_help(self, args=None):
        """❓ Show this help menu"""
        print(f"\n{Elite.BOLD}{Elite.CYAN}TOKEN_SAVER v{self.ts.VERSION} — Elite Commands{Elite.END}\n")
        
        commands = {
            "status": "Show elite status report",
            "health": "Full health check with diagnostics",
            "cache_set KEY VALUE [TTL]": "Store a key-value pair",
            "cache_get KEY": "Retrieve a cached value",
            "optimize QUERY": "Optimize a single request",
            "batch": "Batch optimize multiple requests",
            "clean": "Remove expired cache entries",
            "export [PATH]": "Export cache as JSON",
            "help": "Show this menu"
        }
        
        for cmd, desc in commands.items():
            print(f"  {Elite.GREEN}{cmd:<30}{Elite.END} {desc}")
        print()
    
    def run(self, args):
        """Main CLI router"""
        if not args:
            self.cmd_help()
            return
        
        cmd = args[0]
        cmd_args = args[1:]
        
        method_name = f"cmd_{cmd.replace('-', '_')}"
        if hasattr(self, method_name):
            getattr(self, method_name)(cmd_args)
        else:
            log_elite(f"Unknown command: {cmd}", "ERROR")
            self.cmd_help()

def main():
    cli = EliteCLI()
    cli.run(sys.argv[1:])

if __name__ == "__main__":
    main()
