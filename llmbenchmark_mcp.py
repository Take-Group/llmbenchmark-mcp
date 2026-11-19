#!/usr/bin/env python3
"""LLMBenchmark.ai MCP server: stdio proxy and small CLI over the hosted server (stdlib only)."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERSION = "1.0.0"
URL = os.environ.get("LLMBENCHMARK_MCP_URL") or "https://api.llmbenchmark.ai/mcp"
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
USER_AGENT = "llmbenchmark-mcp/" + VERSION

CONFIG = {"mcpServers": {"llmbenchmark": {"url": "https://api.llmbenchmark.ai/mcp"}}}


class Client:
    """Talks to the hosted Streamable HTTP server; handles JSON and SSE replies and the session id."""

    def __init__(self):
        self.session = None
        self.next_id = 0
        self.started = False
        self.tools = None

    def _post(self, payload):
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        req = urllib.request.Request(URL, json.dumps(payload).encode(), headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                self.session = resp.headers.get("Mcp-Session-Id") or self.session
                return resp.read().decode(), resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            raise RuntimeError("HTTP %s: %s" % (e.code, e.read().decode(errors="replace")[:300]))
        except urllib.error.URLError as e:
            raise RuntimeError("Cannot reach %s: %s" % (URL, e.reason))

    @staticmethod
    def _parse(body, ctype, rid):
        if "text/event-stream" in ctype:
            for line in body.splitlines():
                if line.startswith("data:"):
                    try:
                        msg = json.loads(line[5:].strip())
                    except ValueError:
                        continue
                    if isinstance(msg, dict) and msg.get("id") == rid:
                        return msg
            raise RuntimeError("No JSON-RPC answer in stream")
        return json.loads(body)

    def rpc(self, method, params=None):
        self.next_id += 1
        rid = self.next_id
        body, ctype = self._post({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        msg = self._parse(body, ctype, rid)
        if "error" in msg:
            raise RuntimeError(msg["error"].get("message", str(msg["error"])))
        return msg.get("result", {})

    def start(self):
        if self.started:
            return
        self.rpc("initialize", {
            "protocolVersion": PROTOCOLS[0],
            "capabilities": {},
            "clientInfo": {"name": "llmbenchmark-mcp", "version": VERSION},
        })
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.started = True

    def list_tools(self):
        if self.tools is None:
            self.start()
            self.tools = self.rpc("tools/list").get("tools", [])
        return self.tools

    def call(self, name, args):
        self.start()
        return self.rpc("tools/call", {"name": name, "arguments": args or {}})


def result_text(res):
    return "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")


class Server:
    def __init__(self):
        self.client = Client()

    def handle(self, msg):
        method, rid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
        if rid is None:
            return None  # notification, no reply
        if method == "initialize":
            want = params.get("protocolVersion")
            result = {
                "protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "llmbenchmark", "title": "LLMBenchmark.ai", "version": VERSION},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            try:
                result = {"tools": self.client.list_tools()}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32603, "message": str(e)}}
        elif method == "tools/call":
            try:
                result = self.client.call(params.get("name", ""), params.get("arguments"))
            except Exception as e:
                self.client = Client()
                result = {"content": [{"type": "text", "text": "LLMBenchmark.ai is unreachable: %s" % e}], "isError": True}
        else:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "Method not found: %s" % method}}
        return {"jsonrpc": "2.0", "id": rid, "result": result}


def serve():
    """MCP stdio transport: one JSON-RPC message per line on stdin/stdout, logs on stderr."""
    server = Server()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = None
        try:
            msg = json.loads(line)
            reply = server.handle(msg) if isinstance(msg, dict) else None
        except ValueError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        except Exception as e:
            print("Error: %s" % e, file=sys.stderr)
            reply = {"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict) else None,
                     "error": {"code": -32603, "message": str(e)}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


def main():
    p = argparse.ArgumentParser(prog="llmbenchmark-mcp", description="LLMBenchmark.ai MCP server and CLI. No args: stdio server.")
    p.add_argument("--version", action="version", version="llmbenchmark-mcp " + VERSION)
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("recommend", help="print the recommend_model answer for a task")
    r.add_argument("task")
    r.add_argument("--max-price", type=float, help="max output price per million tokens")
    r.add_argument("--open-weights", action="store_true", help="open-weight models only")
    sub.add_parser("tools", help="print the tool names")
    sub.add_parser("config", help="print the remote JSON config for Claude/Cursor")
    args = p.parse_args()
    if args.cmd is None:
        return serve()
    if args.cmd == "config":
        print(json.dumps(CONFIG, indent=2))
        return
    try:
        c = Client()
        if args.cmd == "tools":
            print("\n".join(t["name"] for t in c.list_tools()))
        else:
            a = {"task": args.task}
            if args.max_price is not None:
                a["max_output_price_per_m"] = args.max_price
            if args.open_weights:
                a["open_weights_only"] = True
            res = c.call("recommend_model", a)
            print(result_text(res))
            if res.get("isError"):
                sys.exit(1)
    except Exception as e:
        print("Error: %s" % e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
