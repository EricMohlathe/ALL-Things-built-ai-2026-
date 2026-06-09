"""
ConnectorRegistry — pluggable trading-platform MCP connectors.

A "connector" is any MCP server that exposes a trading platform (TradingView,
a broker, an exchange, a data feed). The hub reads/analyzes through them and —
only via the ExecutionGate — can place orders through ones that support it.

Add ANY platform later:
  python hub.py add-connector --name my-broker --mcp "npx -y some-broker-mcp" --exec true
which appends to registry/connectors.json AND prints the `claude mcp add` line
so Claude itself can drive it.
"""
from __future__ import annotations
import os, json

_REG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "registry", "connectors.json")


def _load() -> list[dict]:
    try:
        return json.load(open(_REG))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    os.makedirs(os.path.dirname(_REG), exist_ok=True)
    json.dump(items, open(_REG, "w"), indent=2)


def list_connectors() -> list[dict]:
    return _load()


def add_connector(name: str, mcp_cmd: str, exec_capable: bool = False,
                  transport: str = "stdio", url: str = "") -> dict:
    items = _load()
    items = [c for c in items if c.get("name") != name]
    entry = {"name": name, "mcp_cmd": mcp_cmd, "transport": transport,
             "url": url, "exec_capable": bool(exec_capable), "enabled": True}
    items.append(entry)
    _save(items)
    return entry


def claude_mcp_add_line(entry: dict) -> str:
    if entry.get("transport") == "http" and entry.get("url"):
        return f'claude mcp add --transport http --scope user {entry["name"]} {entry["url"]}'
    return f'claude mcp add --scope user {entry["name"]} -- {entry.get("mcp_cmd","")}'
