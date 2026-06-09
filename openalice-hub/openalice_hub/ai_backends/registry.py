"""
AIBackendRegistry — pluggable AI brains for the hub.

Built-in slots:
  * claude   : native (this Claude Code session / Anthropic API)
  * hermes   : Nous Hermes agent via the local 9router gateway (OpenAI-compatible)
  * <custom> : any OpenAI-compatible endpoint you add (your own models)

You can attach your own AIs alongside the configured ones at any time:
  python hub.py add-ai --name mybrain --base-url http://host:port/v1 --model foo --key sk-...
"""
from __future__ import annotations
import os, json, urllib.request

_REG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "registry", "ai_backends.json")


def _load() -> list[dict]:
    try:
        return json.load(open(_REG))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    os.makedirs(os.path.dirname(_REG), exist_ok=True)
    json.dump(items, open(_REG, "w"), indent=2)


def list_backends() -> list[dict]:
    return _load()


def add_backend(name: str, base_url: str, model: str, api_key: str = "",
                kind: str = "openai-compatible") -> dict:
    items = _load()
    items = [b for b in items if b.get("name") != name]
    entry = {"name": name, "kind": kind, "base_url": base_url,
             "model": model, "api_key_env": f"{name.upper()}_API_KEY",
             "api_key": api_key, "enabled": True}
    items.append(entry)
    _save(items)
    return entry


def health(entry: dict, timeout: float = 3.0) -> str:
    """Best-effort reachability check for an OpenAI-compatible backend."""
    base = entry.get("base_url", "").rstrip("/")
    if not base:
        return "no-url"
    try:
        req = urllib.request.Request(base + "/models")
        key = entry.get("api_key") or os.environ.get(entry.get("api_key_env", ""), "")
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return "reachable" if r.status == 200 else f"http {r.status}"
    except Exception as e:
        return f"unreachable ({type(e).__name__})"
