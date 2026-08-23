import json
import io
from mcp.server import TokenSaverMCPServer

def test_initialize():
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    server = TokenSaverMCPServer()
    res = server.handle_request(req)
    assert res["jsonrpc"] == "2.0"
    assert res["id"] == 1
    assert "serverInfo" in res["result"]
    assert "capabilities" in res["result"]

def test_tools_list():
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    server = TokenSaverMCPServer()
    res = server.handle_request(req)
    assert "tools" in res["result"]
    tools = {t["name"] for t in res["result"]["tools"]}
    assert tools == {"compress_context", "externalize", "optimize_request", "cache_status"}

def test_tools_call():
    req = {
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {
            "name": "compress_context",
            "arguments": {"text": "abc", "ratio": 0.5, "model": "gpt"}
        }
    }
    server = TokenSaverMCPServer()
    res = server.handle_request(req)
    assert "content" in res["result"]
    content = json.loads(res["result"]["content"][0]["text"])
    assert "compressed" in content

def test_tools_call_error():
    req = {
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {
            "name": "compress_context",
            "arguments": {}
        }
    }
    server = TokenSaverMCPServer()
    res = server.handle_request(req)
    assert "error" in res
    assert res["error"]["code"] == -32602

def test_bad_method():
    req = {"jsonrpc": "2.0", "id": 5, "method": "bad_method"}
    server = TokenSaverMCPServer()
    res = server.handle_request(req)
    assert "error" in res
    assert res["error"]["code"] == -32601

def test_run_loop():
    stdin = io.StringIO('{"jsonrpc": "2.0", "id": 1, "method": "initialize"}\ninvalid json\n')
    stdout = io.StringIO()
    server = TokenSaverMCPServer(stdin=stdin, stdout=stdout)
    server.run()
    out = stdout.getvalue().strip().split('\n')
    assert len(out) == 2
    res1 = json.loads(out[0])
    res2 = json.loads(out[1])
    assert "result" in res1
    assert "error" in res2
    assert res2["error"]["code"] == -32700
