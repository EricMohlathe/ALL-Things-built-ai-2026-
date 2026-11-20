#!/usr/bin/env python3
"""DEX market research for trader-dex: timestamped snapshots of decentralized-exchange pairs
from DEX Screener's documented public API, checked for pool identity and data quality,
labelled WATCH / REVIEW / SKIP for research, with the analyst and risk-review prompts.
PAPER MODE ONLY: no wallet, no keys, no orders. Standard library only.

    python3 dex.py scan                                   # SOL/USDC and ETH/USDC, 10 pairs each
    python3 dex.py scan "PEPE/WETH" "BONK/SOL" --chain solana --min-liquidity 100000
    python3 dex.py pair solana <pairAddress>              # one pool by chain and address
    python3 dex.py prompts                                # the analyst + risk-review prompts with the real rows
    python3 dex.py history <pairAddress>                  # that pool across every saved snapshot

Each scan writes trader/dex/snapshot-<UTC>.csv (kept: never overwritten) and
trader/dex/latest.json. The method follows the AI Flow Lab paper-trading guide: a documented
endpoint instead of scraping, every row timestamped, the same symbol is NOT proof of the same
token (check the chain and the pair address), and no invented values.

API: https://api.dexscreener.com/latest/dex/search?q=<query> and /latest/dex/pairs/<chain>/<pair>
(reference: https://docs.dexscreener.com/api/reference). Limits and fields can change.
"""

import argparse
import csv
import glob
import json
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trader-core"))
import tradercore as tc  # noqa: E402
import history as hist  # noqa: E402

SEARCH = "https://api.dexscreener.com/latest/dex/search?q=%s"
PAIR = "https://api.dexscreener.com/latest/dex/pairs/%s/%s"
OUT = os.path.join("trader", "dex")
FIELDS = ["timestamp_utc", "search", "chain", "dex", "pair_address", "base_symbol", "base_address", "quote_symbol",
          "price_usd", "liquidity_usd", "volume_24h_usd", "change_h1_pct", "change_h24_pct", "buys_24h", "sells_24h",
          "fdv_usd", "age_hours", "flags", "label", "url"]

ANALYST = """You are an AI market-research assistant in PAPER MODE.
I will paste real DEX Screener CSV rows.
For each pair:
1. Identify chain and pair address.
2. Report price, 24h volume and liquidity exactly as given.
3. Flag missing data, low liquidity and duplicate-looking symbols.
4. List a reason to investigate and a reason to avoid it.
5. Return WATCH / REVIEW / SKIP with a one-line rationale.
Do not invent news, forecasts, fills or profitability.
No live trading recommendations or account connections.
CSV ROWS:
%s"""

REVIEWER = """Review the market idea below as a skeptical PAPER-TRADE reviewer.
Check:
- Does the token/pair address match the intended asset?
- Are liquidity and volume adequate for the proposed size?
- Are data age, spread, slippage and fees unknown?
- Would a different chain or pool change the conclusion?
- What evidence is missing before a simulated entry?
Output: REJECT / NEEDS MORE DATA / PAPER TEST ONLY.
Never turn missing information into confidence.
MARKET SNAPSHOT + ANALYSIS:
%s
[PASTE THE ANALYST'S ANSWER HERE]"""


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def get_json(url):
    raw = hist.http_bytes(url)
    if not raw:
        raise tc.TraderError("DEX Screener sent nothing for %s" % url.split("?")[0])
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        raise tc.TraderError("DEX Screener sent something that is not JSON")


def row_of(pair, term, now_iso, now_ts):
    liq = (pair.get("liquidity") or {}).get("usd")
    vol = (pair.get("volume") or {}).get("h24")
    ch = pair.get("priceChange") or {}
    tx = (pair.get("txns") or {}).get("h24") or {}
    created = pair.get("pairCreatedAt")
    base, quote = pair.get("baseToken") or {}, pair.get("quoteToken") or {}
    return {"timestamp_utc": now_iso, "search": term, "chain": pair.get("chainId", ""), "dex": pair.get("dexId", ""),
            "pair_address": pair.get("pairAddress", ""), "base_symbol": base.get("symbol", ""),
            "base_address": base.get("address", ""), "quote_symbol": quote.get("symbol", ""),
            "price_usd": _num(pair.get("priceUsd")), "liquidity_usd": _num(liq), "volume_24h_usd": _num(vol),
            "change_h1_pct": _num(ch.get("h1")), "change_h24_pct": _num(ch.get("h24")),
            "buys_24h": tx.get("buys"), "sells_24h": tx.get("sells"), "fdv_usd": _num(pair.get("fdv")),
            "age_hours": round((now_ts - created / 1000.0) / 3600.0, 1) if created else None, "url": pair.get("url", "")}


def classify(rows, min_liq, min_vol):
    """Flags and a research label for each row. SKIP: missing or thin data. REVIEW: an identity
    or behaviour question. WATCH: passes every check. None of them is a buy signal."""
    by_symbol = {}
    for r in rows:
        by_symbol.setdefault(r["base_symbol"].upper(), set()).add((r["chain"], r["base_address"]))
    for r in rows:
        f = []
        if r["price_usd"] is None:
            f.append("missing price")
        if r["liquidity_usd"] is None:
            f.append("missing liquidity")
        elif r["liquidity_usd"] < min_liq:
            f.append("low liquidity")
        if r["volume_24h_usd"] is None:
            f.append("missing volume")
        elif r["volume_24h_usd"] < min_vol:
            f.append("low volume")
        if len(by_symbol.get(r["base_symbol"].upper(), ())) > 1:
            f.append("same symbol, different tokens or chains")
        if r["age_hours"] is not None and r["age_hours"] < 72:
            f.append("new pool (%.0fh old)" % r["age_hours"])
        b, s = r["buys_24h"], r["sells_24h"]
        if b and s and (s > 1.5 * b or b > 1.5 * s):
            f.append("one-sided flow (%s buys, %s sells)" % (b, s))
        if r["liquidity_usd"] and r["volume_24h_usd"] and r["volume_24h_usd"] > 5 * r["liquidity_usd"]:
            f.append("volume over 5x liquidity")
        if r["change_h24_pct"] is not None and abs(r["change_h24_pct"]) > 30:
            f.append("moved %+.0f%% in 24h" % r["change_h24_pct"])
        hard = [x for x in f if x.startswith(("missing", "low liquidity"))]
        r["flags"] = "; ".join(f)
        r["label"] = "SKIP" if hard else "REVIEW" if f else "WATCH"
    return rows


def save(rows, out, stamp):
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "snapshot-%s.csv" % stamp)
    k = 1
    while os.path.exists(path):
        k += 1
        path = os.path.join(out, "snapshot-%s-%d.csv" % (stamp, k))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k2: ("" if r.get(k2) is None else r.get(k2)) for k2 in FIELDS})
    tc.write_json(os.path.join(out, "latest.json"), {"file": path, "rows": rows})
    return path


def fmt_usd(x):
    if x is None:
        return "-"
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(x) >= div:
            return "$%.2f%s" % (x / div, suf)
    return "$%.6g" % x


def print_rows(rows):
    print("%-6s %-9s %-9s %-10s %12s %10s %10s %7s  %s" % ("LABEL", "CHAIN", "DEX", "PAIR", "PRICE", "LIQUIDITY",
                                                         "VOL 24H", "24H", "FLAGS / ADDRESS"))
    for r in rows:
        print("%-6s %-9s %-9s %-10s %12s %10s %10s %7s  %s" % (
            r["label"], r["chain"][:9], r["dex"][:9], ("%s/%s" % (r["base_symbol"], r["quote_symbol"]))[:10],
            "-" if r["price_usd"] is None else "%.6g" % r["price_usd"], fmt_usd(r["liquidity_usd"]),
            fmt_usd(r["volume_24h_usd"]), "-" if r["change_h24_pct"] is None else "%+.1f%%" % r["change_h24_pct"],
            r["flags"] or r["pair_address"][:14] + "..."))


def cmd_scan(a, cfg):
    now = tc.utc_now()
    now_iso, now_ts = tc.iso(now), tc.ts_of(now)
    rows, errors = [], []
    for term in a.terms or ["SOL/USDC", "ETH/USDC"]:
        try:
            doc = get_json(SEARCH % urllib.parse.quote(term, safe=""))
        except tc.TraderError as e:
            errors.append("%s: %s" % (term, e))
            continue
        pairs = [p for p in doc.get("pairs") or [] if not a.chain or p.get("chainId") == a.chain]
        rows.extend(row_of(p, term, now_iso, now_ts) for p in pairs[:a.top])
        tc.SLEEP(0.3)
    if not rows:
        raise tc.TraderError("no rows: %s. Check the connection and the API reference; do not invent values."
                             % ("; ".join(errors) or "the searches matched nothing"))
    classify(rows, a.min_liquidity, a.min_volume)
    path = save(rows, a.out, now.strftime("%Y%m%dT%H%M%SZ"))
    if a.json:
        print(json.dumps({"file": path, "rows": rows}, indent=2))
        return 0
    print_rows(rows)
    n = {k: sum(1 for r in rows if r["label"] == k) for k in ("WATCH", "REVIEW", "SKIP")}
    print("\n%d rows at %s saved to %s: %d WATCH, %d REVIEW, %d SKIP%s." % (
        len(rows), now_iso[:16].replace("T", " "), path, n["WATCH"], n["REVIEW"], n["SKIP"],
        "; failed: " + "; ".join(errors) if errors else ""))
    print("Labels are research decisions, not buy signals. Open each url and confirm the chain, the pool and the token "
          "address before anything else. Next: dex.py prompts, then journal.py from-dex.")
    return 0


def cmd_pair(a, cfg):
    now = tc.utc_now()
    doc = get_json(PAIR % (urllib.parse.quote(a.chain, safe=""), urllib.parse.quote(a.address, safe="")))
    pairs = doc.get("pairs") or ([doc["pair"]] if doc.get("pair") else [])
    if not pairs:
        raise tc.TraderError("no pool %s on %s" % (a.address, a.chain))
    rows = classify([row_of(p, "pair", tc.iso(now), tc.ts_of(now)) for p in pairs], a.min_liquidity, a.min_volume)
    if a.json:
        print(json.dumps(rows, indent=2))
    else:
        print_rows(rows)
    return 0


def latest_rows(a):
    doc = tc.read_json(os.path.join(a.out, "latest.json"), "the last scan (run dex.py scan first)")
    return doc["rows"], doc["file"]


def cmd_prompts(a, cfg):
    rows, path = latest_rows(a)
    keep = [r for r in rows if r["label"] in a.labels][:a.rows]
    if not keep:
        raise tc.TraderError("no %s rows in %s" % ("/".join(a.labels), path))
    buf = [",".join(FIELDS)]
    for r in keep:
        buf.append(",".join('"%s"' % ("" if r.get(k) is None else r.get(k)) for k in FIELDS))
    text = "\n".join(buf)
    print("=== 1. MARKET ANALYST (paste into a fresh conversation, or run it as the analyst) ===")
    print(ANALYST % text)
    print("\n=== 2. INDEPENDENT RISK CHECK (a separate conversation: it should look for reasons to reject) ===")
    print(REVIEWER % text)
    print("\nFrom %s. Keep these prompts unchanged for your first sample of decisions: changing the rules after each "
          "outcome hides overfitting." % path)
    return 0


def cmd_history(a, cfg):
    rows = []
    for f in sorted(glob.glob(os.path.join(a.out, "snapshot-*.csv"))):
        with open(f, newline="", encoding="utf-8") as fh:
            rows.extend(r for r in csv.DictReader(fh) if r["pair_address"] == a.address)
    if not rows:
        raise tc.TraderError("pool %s is in none of the snapshots in %s" % (a.address, a.out))
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    r0 = rows[0]
    print("%s/%s on %s (%s), %d snapshots:" % (r0["base_symbol"], r0["quote_symbol"], r0["chain"], r0["dex"], len(rows)))
    first = _num(rows[0]["price_usd"])
    for r in rows:
        p = _num(r["price_usd"])
        print("  %s  price %-12s liquidity %-10s vol 24h %-10s %s" % (
            r["timestamp_utc"][:16].replace("T", " "), r["price_usd"] or "-", fmt_usd(_num(r["liquidity_usd"])),
            fmt_usd(_num(r["volume_24h_usd"])), "%+.1f%% since the first" % (100 * (p / first - 1)) if p and first else ""))
    print("A later price is not evidence that a hypothetical order would have filled at it.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="DEX Screener research snapshots, paper mode only (trader-dex).")
    ap.add_argument("--config", default="trader/config.json")
    ap.add_argument("--out", default=OUT, help="snapshot folder (default trader/dex)")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("scan", "pair"):
        p = sub.add_parser(name)
        if name == "scan":
            p.add_argument("terms", nargs="*", help='searches, e.g. "SOL/USDC" "ETH/USDC" (the default)')
            p.add_argument("--top", type=int, default=10, help="pairs kept per search (default 10)")
            p.add_argument("--chain", help="only this chain id, e.g. solana, ethereum, base, bsc")
        else:
            p.add_argument("chain")
            p.add_argument("address")
        p.add_argument("--min-liquidity", dest="min_liquidity", type=float, default=50000.0)
        p.add_argument("--min-volume", dest="min_volume", type=float, default=50000.0)
    p = sub.add_parser("prompts")
    p.add_argument("--rows", type=int, default=10)
    p.add_argument("--labels", nargs="*", default=["WATCH", "REVIEW"], choices=["WATCH", "REVIEW", "SKIP"])
    p = sub.add_parser("history")
    p.add_argument("address")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        cfg = tc.load_config(a.config)
        return {"scan": cmd_scan, "pair": cmd_pair, "prompts": cmd_prompts, "history": cmd_history}[a.cmd](a, cfg)
    except (tc.TraderError, ValueError, OSError) as e:
        print("dex.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
