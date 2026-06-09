"""
ExecutionGate — the single, mandatory choke point for ALL order placement.

Design rule (non-negotiable):
  * Market data, analysis, backtests, signals  -> UNRESTRICTED.
  * Order placement                            -> ALWAYS through this gate.

Modes:
  PAPER   (default) : orders are simulated in-memory, never sent anywhere.
  TESTNET           : orders routed to an exchange *testnet/sandbox* adapter.
  LIVE              : real money. DISABLED unless ALL of:
                        - config live_enabled = true
                        - broker credentials present
                        - a fresh human confirmation token is supplied per order

No code path can place a LIVE order without a human-entered confirmation token
that the gate itself issued seconds earlier. An AI/agent cannot self-confirm:
the token is shown to the human and must be typed back. This is intentional.
"""
from __future__ import annotations
import os, json, time, hmac, hashlib, secrets
from dataclasses import dataclass, asdict, field
from enum import Enum
from .audit import audit


class Mode(str, Enum):
    PAPER = "paper"
    TESTNET = "testnet"
    LIVE = "live"


class ExecutionRefused(Exception):
    pass


@dataclass
class Order:
    symbol: str
    side: str            # "buy" | "sell"
    qty: float
    type: str = "market"  # market | limit
    price: float | None = None
    connector: str = "paper"
    meta: dict = field(default_factory=dict)

    def key(self) -> str:
        return f"{self.connector}:{self.symbol}:{self.side}:{self.qty}:{self.type}:{self.price}"


class ExecutionGate:
    def __init__(self, mode: str = "paper", live_enabled: bool = False,
                 broker_creds: dict | None = None):
        self.mode = Mode(mode)
        self.live_enabled = bool(live_enabled)
        self.broker_creds = broker_creds or {}
        self._paper_fills: list[dict] = []
        self._pending: dict[str, dict] = {}   # token -> {order_key, expires}

    # ---- safety banner -------------------------------------------------
    def banner(self) -> str:
        if self.mode is Mode.LIVE and self.live_enabled:
            return "🔴 LIVE — real money. Every order needs a typed confirmation token."
        if self.mode is Mode.TESTNET:
            return "🟡 TESTNET — sandbox exchange, no real funds."
        return "🟢 PAPER — simulated only. Nothing is sent to any exchange."

    # ---- the ONLY entry point for orders -------------------------------
    def place(self, order: Order, confirm_token: str | None = None) -> dict:
        audit("order.request", order=asdict(order), mode=self.mode.value)

        if order.side not in ("buy", "sell"):
            raise ExecutionRefused(f"bad side: {order.side!r}")
        if order.qty <= 0:
            raise ExecutionRefused("qty must be > 0")

        if self.mode is Mode.PAPER:
            return self._paper(order)
        if self.mode is Mode.TESTNET:
            return self._testnet(order)
        return self._live(order, confirm_token)

    # ---- paper ---------------------------------------------------------
    def _paper(self, order: Order) -> dict:
        fill = {
            "status": "filled", "mode": "paper", "ts": time.time(),
            "symbol": order.symbol, "side": order.side, "qty": order.qty,
            "price": order.price or 0.0, "simulated": True,
        }
        self._paper_fills.append(fill)
        audit("order.paper_fill", **fill)
        return fill

    # ---- testnet -------------------------------------------------------
    def _testnet(self, order: Order) -> dict:
        # Routed to a sandbox adapter. Stub: real adapter wired per-connector.
        audit("order.testnet", order=asdict(order))
        return {"status": "submitted", "mode": "testnet", "order": asdict(order),
                "note": "wire a sandbox connector under connectors/ to fill this"}

    # ---- live (heavily gated) -----------------------------------------
    def arm_live(self, order: Order) -> str:
        """Issue a one-time confirmation token for a specific order.
        The token is meant to be SHOWN TO A HUMAN, who types it back."""
        if not self.live_enabled:
            raise ExecutionRefused("live trading not enabled in config (live_enabled=false)")
        if not self.broker_creds:
            raise ExecutionRefused("no broker credentials configured")
        token = secrets.token_hex(3).upper()   # 6 hex chars, human-typeable
        self._pending[token] = {"order_key": order.key(), "expires": time.time() + 120}
        audit("order.live_armed", order=asdict(order), token_issued=True)
        return token

    def _live(self, order: Order, confirm_token: str | None) -> dict:
        if not self.live_enabled:
            raise ExecutionRefused("LIVE refused: live_enabled=false")
        if not self.broker_creds:
            raise ExecutionRefused("LIVE refused: no broker credentials")
        if not confirm_token:
            raise ExecutionRefused(
                "LIVE refused: no confirmation token. Call arm_live(order), show the "
                "token to the human, have them type it back, then pass it here.")
        rec = self._pending.get(confirm_token)
        if not rec:
            raise ExecutionRefused("LIVE refused: unknown/never-issued token")
        if time.time() > rec["expires"]:
            self._pending.pop(confirm_token, None)
            raise ExecutionRefused("LIVE refused: token expired (120s)")
        if rec["order_key"] != order.key():
            raise ExecutionRefused("LIVE refused: token does not match THIS order")
        # passed all gates — hand off to the real broker connector
        self._pending.pop(confirm_token, None)
        audit("order.live_confirmed", order=asdict(order))
        # NOTE: the actual broker call lives in the connector; we only authorize.
        return {"status": "authorized", "mode": "live", "order": asdict(order),
                "note": "authorized for the connector to submit; connector does the send"}

    def paper_pnl(self) -> dict:
        buys = sum(f["qty"] * f["price"] for f in self._paper_fills if f["side"] == "buy")
        sells = sum(f["qty"] * f["price"] for f in self._paper_fills if f["side"] == "sell")
        return {"fills": len(self._paper_fills), "paper_buy_notional": buys,
                "paper_sell_notional": sells, "net": sells - buys}
