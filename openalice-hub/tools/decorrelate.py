#!/usr/bin/env python3
"""Correlation filter for the GODMODE roster. Many slots share an underlying or
move together (indices, crypto, EUR-bloc). This computes daily-return correlation
across the roster's markets, greedily clusters at a threshold, and caps slots per
cluster so the portfolio is genuinely diversified risk, not one crowded bet.
Writes the GODMODE_DECORR preset into roster_meta.json + clusters summary."""
import os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openalice_hub.core import data as datamod
from openalice_hub.strategies import godmode_setups  # noqa

META = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "roster_meta.json")))
slots = META["godmode"]["slots"]                      # each: mkt, sym, setup, pf, ...
mkts = sorted({s["mkt"] for s in slots})

# --- daily log-return series per market (date -> ret), from cached data ---
def series(mkt):
    src = "binance" if mkt.endswith("USDT") else None
    try:
        sym, sr = (mkt, "binance") if src else datamod.resolve(mkt)
        bars = datamod.get_ohlcv(sym, source=sr, interval="1d", limit=1500)
    except Exception:
        return {}
    out = {}
    import datetime as dt
    prev = None
    for b in bars:
        t = b["t"]; t = t/1000 if t > 1e11 else t
        day = dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
        if prev and prev > 0 and b["c"] > 0:
            out[day] = math.log(b["c"]/prev)
        prev = b["c"]
    return out
S = {m: series(m) for m in mkts}
S = {m: v for m, v in S.items() if len(v) > 200}      # need enough overlap

def corr(a, b):
    common = set(S[a]) & set(S[b])
    if len(common) < 100: return 0.0
    xa = [S[a][d] for d in common]; xb = [S[b][d] for d in common]
    n = len(xa); ma = sum(xa)/n; mb = sum(xb)/n
    cov = sum((xa[i]-ma)*(xb[i]-mb) for i in range(n))
    va = sum((x-ma)**2 for x in xa); vb = sum((x-mb)**2 for x in xb)
    return cov/math.sqrt(va*vb) if va > 0 and vb > 0 else 0.0

# --- greedy cluster markets by correlation (rep = highest-PF market in cluster) ---
THRESH = 0.7
pf_by_mkt = {}
for s in slots: pf_by_mkt[s["mkt"]] = pf_by_mkt.get(s["mkt"], 0) + s["pf"]
ordered = [m for m in sorted(pf_by_mkt, key=lambda m: pf_by_mkt[m], reverse=True) if m in S]
clusters = []   # list of {rep, members[]}
for m in ordered:
    placed = False
    for c in clusters:
        if abs(corr(m, c["rep"])) >= THRESH:
            c["members"].append(m); placed = True; break
    if not placed:
        clusters.append({"rep": m, "members": [m]})
mkt_cluster = {m: i for i, c in enumerate(clusters) for m in c["members"]}

# --- build decorrelated roster: cap slots per cluster (keep best PF), risk-balance ---
CAP = 6                                   # max slots per correlation cluster
bycl = {}
for s in sorted(slots, key=lambda s: s["pf"], reverse=True):
    ci = mkt_cluster.get(s["mkt"])
    if ci is None: continue
    bycl.setdefault(ci, []).append(s)
dec = []
for ci, lst in bycl.items():
    dec += lst[:CAP]
# stats
def g(s, k):
    ex = next((x for x in slots if x["mkt"] == s["mkt"] and x["setup"] == s["setup"]), {})
    return s
# reconstruct roster string from full meta slots (they carry exits via the godmode roster order)
# map (sym,setup)->slotstring from existing godmode roster
gm_slots = META["godmode"]["roster"].split(";")
key2str = {}
for ss in gm_slots:
    p = ss.split(":"); key2str[(p[0], p[1])] = ss
dec_str = ";".join(key2str[(s["sym"], s["setup"])] for s in dec if (s["sym"], s["setup"]) in key2str)
n = len(dec); tpd = sum(x["tpy"] for x in dec)/252.0; avg = sum(x["pf"] for x in dec)/n
META["godmode_decorr"] = {"n": n, "tpd": round(tpd, 2), "avg_pf": round(avg, 2),
                          "clusters": len(clusters), "cap_per_cluster": CAP,
                          "roster": dec_str,
                          "slots": [dict(s, cluster=mkt_cluster[s["mkt"]]) for s in sorted(dec, key=lambda s: s["pf"], reverse=True)]}
json.dump(META, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "roster_meta.json"), "w"), indent=1, default=str)
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry", "roster_godmode_decorr.txt"), "w").write(dec_str)
print(f"markets with data: {len(S)}/{len(mkts)}")
print(f"correlation clusters (>= {THRESH}): {len(clusters)} independent risk factors")
print(f"GODMODE_DECORR: {n} slots (cap {CAP}/cluster) | ~{tpd:.2f} trades/day | avg PF {avg:.2f}")
print("\nclusters (rep + size):")
for i, c in enumerate(sorted(clusters, key=lambda c: -len(c["members"]))[:14]):
    print(f"  [{len(c['members']):2}] {c['rep']:8} :: {', '.join(c['members'][:8])}{' …' if len(c['members'])>8 else ''}")
