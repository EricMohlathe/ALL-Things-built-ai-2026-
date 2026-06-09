"""Append-only audit log for every gate decision and order event."""
from __future__ import annotations
import os, json, time

_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "audit.log")


def audit(event: str, **fields) -> None:
    rec = {"ts": time.time(), "iso": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event}
    rec.update(fields)
    try:
        os.makedirs(os.path.dirname(_LOG), exist_ok=True)
        with open(_LOG, "a") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
    except Exception:
        pass  # auditing must never break execution flow
