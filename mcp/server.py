import sys
import json
import traceback
from typing import Any

class TokenSaverMCPServer:
    def __init__(self, stdin=sys.stdin, stdout=sys.stdout):
        self.stdin = stdin
        self.stdout = stdout

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
                            "description": "Compress text context",
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
                            "description": "Create pure pointer",
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
                            "description": "Optimize request",
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
                            "description": "Cache health metrics",
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
            if "text" not in args or "ratio" not in args or "model" not in args:
                raise ValueError("Missing required arguments")
            return {"compressed": "mock_compressed", "tokens_saved": 10}
        elif name == "externalize":
            if "text" not in args or "label" not in args or "dest" not in args:
                raise ValueError("Missing required arguments")
            return {"pointer_uri": f"mock_uri_{args['label']}", "savings": 20}
        elif name == "optimize_request":
            if "request" not in args or "ttl" not in args:
                raise ValueError("Missing required arguments")
            return {"optimized": True, "ttl": args["ttl"]}
        elif name == "cache_status":
            return {"hits": 100, "misses": 5}
        else:
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
