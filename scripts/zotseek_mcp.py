#!/usr/bin/env python3
"""Discover and call tools exposed by the local ZOTseek MCP endpoint.

This client uses only the Python standard library. It initializes the MCP
server and performs ``tools/list`` before every tool call, so tool names and
input schemas are discovered from the running server rather than hard-coded.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_ENDPOINT = "http://localhost:23119/zotseek/mcp"
PROTOCOL_VERSION = "2025-03-26"


class McpError(RuntimeError):
    """Raised for transport and JSON-RPC errors."""


def rpc(endpoint: str, method: str, params: dict[str, Any], request_id: int) -> Any:
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
    except (OSError, urllib.error.URLError) as exc:
        raise McpError(f"cannot reach {endpoint}: {exc}") from exc
    try:
        message = json.loads(body)
    except json.JSONDecodeError as exc:
        raise McpError(f"server returned invalid JSON: {exc}") from exc
    if "error" in message:
        error = message["error"]
        raise McpError(f"MCP error {error.get('code')}: {error.get('message')}")
    if "result" not in message:
        raise McpError("JSON-RPC response has no result")
    return message["result"]


def discover(endpoint: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    server = rpc(
        endpoint,
        "initialize",
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "zotero-use", "version": "1.0"},
        },
        1,
    )
    listing = rpc(endpoint, "tools/list", {}, 2)
    tools = listing.get("tools")
    if not isinstance(tools, list):
        raise McpError("tools/list did not return a tools array")
    return server, tools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("ZOTSEEK_MCP_URL", DEFAULT_ENDPOINT),
        help="MCP URL (default: %(default)s; override with ZOTSEEK_MCP_URL)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    tools_parser = subparsers.add_parser("tools", help="Discover live tools and schemas")
    tools_parser.add_argument(
        "--names-only", action="store_true", help="Print only discovered tool names"
    )

    call_parser = subparsers.add_parser(
        "call", help="Discover tools, then call one by its current name"
    )
    call_parser.add_argument("tool", help="Tool name returned by the live tools command")
    call_parser.add_argument(
        "--arguments", default="{}", help="Tool arguments as a JSON object"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        server, tools = discover(args.endpoint)
        if args.command == "tools":
            if args.names_only:
                print("\n".join(tool.get("name", "") for tool in tools))
            else:
                print(json.dumps({"server": server, "tools": tools}, indent=2))
            return 0

        available = {
            tool.get("name"): tool for tool in tools if isinstance(tool.get("name"), str)
        }
        if args.tool not in available:
            names = ", ".join(sorted(available)) or "none"
            raise McpError(f"tool {args.tool!r} is unavailable; discovered: {names}")
        try:
            arguments = json.loads(args.arguments)
        except json.JSONDecodeError as exc:
            raise McpError(f"--arguments is not valid JSON: {exc}") from exc
        if not isinstance(arguments, dict):
            raise McpError("--arguments must decode to a JSON object")
        result = rpc(
            args.endpoint,
            "tools/call",
            {"name": args.tool, "arguments": arguments},
            3,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except McpError as exc:
        print(f"ZOTseek MCP error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
