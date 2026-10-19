import sys
import hashlib
import json
import traceback
from typing import Any
from pathlib import Path

from token_saver_elite_core import EliteMemoryCache, EliteTokenBridge
from src.pure_pointer import externalize
from src.token_counter import estimate_tokens

class TokenSaverMCPServer:
    def __init__(self, stdin=sys.stdin, stdout=sys.stdout, *, cache=None):
        self.stdin = stdin
        self.stdout = stdout
        self._cache = cache

    def _owner_cache(self):
        if self._cache is None:
            self._cache = EliteMemoryCache()
        return self._cache

    def handle_request(self, req: dict) -> dict:
        method = req.get("method")
        params = req.get("params", {})
        req_id = req.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "serverInfo": {"name": "TokenSaverMCP", "version": "1.0"},
                    "capabilities": {"tools": {}}
                }
            }
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "compress_context",
                            "description": "Explicitly requested extractive compression only; original source remains recoverable",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "ratio": {"type": "number"},
                                    "model": {"type": "string"}
                                },
                                "required": ["text", "ratio", "model"]
                            }
                        },
                        {
                            "name": "externalize",
                            "description": "Explicit reversible source storage using verified SHA-256 pointer",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "label": {"type": "string"},
                                    "dest": {"type": "string"}
                                },
                                "required": ["text", "label", "dest"]
                            }
                        },
                        {
                            "name": "optimize_request",
                            "description": "Preserve full context by default; reduce only when compression_ratio is supplied explicitly",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "request": {"type": "object"},
                                    "ttl": {"type": "integer"}
                                },
                                "required": ["request", "ttl"]
                            }
                        },
                        {
                            "name": "cache_status",
                            "description": "Read actual local cache health and measurements",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                res = self.call_tool(tool_name, tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res)}]
                    }
                }
            except ValueError as e:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": str(e)}}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

    def call_tool(self, name: str, args: dict) -> Any:
        if name == "compress_context":
            if not all(k in args for k in ("text", "ratio", "model")):
                raise ValueError("Missing required arguments")
            original, ratio, model = args["text"], args["ratio"], args["model"]
            if not isinstance(original, str) or not isinstance(model, str) or not model:
                raise ValueError("text and model must be strings")
            compact = EliteTokenBridge(self._owner_cache()).compress_context(
                original, compression_ratio=ratio
            )
            return {
                "compressed": compact,
                "tokens_saved": max(0, estimate_tokens(original, model) - estimate_tokens(compact, model)),
                "measurement_basis": "local_counter_not_actual_provider_usage",
                "context_policy": "preserved" if compact == original else "explicit_extraction",
            }
        if name == "externalize":
            if not all(k in args for k in ("text", "label", "dest")):
                raise ValueError("Missing required arguments")
            if any(not isinstance(args[k], str) for k in ("text", "label", "dest")) or not args["dest"].strip():
                raise ValueError("text, label and dest must be valid strings")
            pointer = externalize(args["text"], dest=Path(args["dest"]), label=args["label"])
            if not Path(pointer.path).is_file():
                raise RuntimeError("PERSISTENT_POINTER_UNAVAILABLE")
            if hashlib.sha256(Path(pointer.path).read_bytes()).hexdigest() != pointer.sha256:
                raise RuntimeError("PERSISTENT_POINTER_HASH_MISMATCH")
            return {
                "pointer_uri": pointer.canonical_uri,
                "sha256": pointer.sha256,
                "path": pointer.path,
                "bytes_in": pointer.bytes_in,
                "bytes_out": pointer.bytes_out,
                "saved_bytes": max(0, pointer.bytes_in - pointer.bytes_out),
                "savings_status": "bytes_only",
            }
        if name == "optimize_request":
            if "request" not in args or "ttl" not in args:
                raise ValueError("Missing required arguments")
            if not isinstance(args["request"], dict) or not isinstance(args["ttl"], int):
                raise ValueError("request must be a dict and ttl must be integer")
            return EliteTokenBridge(self._owner_cache()).optimize_request(
                args["request"], ttl=args["ttl"]
            )
        if name == "cache_status":
            return self._owner_cache().health()
        raise ValueError(f"Tool {name} not found")

    def run(self):
        for line in self.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                res = self.handle_request(req)
                self.stdout.write(json.dumps(res) + "\n")
                self.stdout.flush()
            except json.JSONDecodeError:
                err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
                self.stdout.write(json.dumps(err) + "\n")
                self.stdout.flush()

if __name__ == "__main__":
    server = TokenSaverMCPServer()
    server.run()
