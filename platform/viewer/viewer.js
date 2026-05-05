// GODMODE_OFEA — Phase-1 replay viewer.
//
// Reads two inputs:
//   1. a CSV of bars (ts,open,high,low,close,volume) — drives the candle chart;
//   2. a JSONL stream of EngineEvents (output of `godmode-replay`) — overlays
//      gate decisions, notifications, candidates, and orders.
//
// No build step, no npm. Open viewer/index.html in any modern browser.

const $ = (id) => document.getElementById(id);

const state = {
  bars: [],
  events: [],
  countsByKind: {},
  selectedBarIdx: null,
  hoverX: null,
};

// ---------- file loaders ----------

$('file-bars').addEventListener('change', async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const text = await f.text();
  state.bars = parseBarCsv(text);
  $('status').textContent = `${state.bars.length} bars loaded`;
  render();
});

$('file-events').addEventListener('change', async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const text = await f.text();
  state.events = parseJsonl(text);
  recomputeCounts();
  $('status').textContent = `${state.events.length} events loaded`;
  render();
});

$('demo-btn').addEventListener('click', () => {
  state.bars = demoBars();
  state.events = demoEvents(state.bars);
  recomputeCounts();
  $('status').textContent = `demo · ${state.bars.length} bars · ${state.events.length} events`;
  render();
});

function parseBarCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const header = lines.shift().split(',').map((s) => s.trim().toLowerCase());
  const idx = (k) => header.indexOf(k);
  const out = [];
  for (const line of lines) {
    const cols = line.split(',');
    if (cols.length < 5) continue;
    out.push({
      ts: cols[idx('ts')] || cols[0],
      open: +cols[idx('open')],
      high: +cols[idx('high')],
      low: +cols[idx('low')],
      close: +cols[idx('close')],
      volume: +(cols[idx('volume')] || 0),
    });
  }
  return out;
}

function parseJsonl(text) {
  const out = [];
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try { out.push(JSON.parse(trimmed)); } catch { /* skip */ }
  }
  return out;
}

function recomputeCounts() {
  const counts = {};
  for (const ev of state.events) {
    const kind = ev.Gate ? `Gate ${ev.Gate.gate}` :
                 ev.Notify ? ev.Notify.tag :
                 ev.Candidate ? 'Candidate' :
                 ev.Order ? 'Order' :
                 ev.Dashboard ? 'Dashboard' : 'Unknown';
    counts[kind] = (counts[kind] || 0) + 1;
  }
  state.countsByKind = counts;
}

// ---------- rendering ----------

function render() {
  drawChart();
  drawSidebar();
}

function drawChart() {
  const canvas = $('chart');
  const wrap = $('chart-wrap');
  const dpr = window.devicePixelRatio || 1;
  canvas.width = wrap.clientWidth * dpr;
  canvas.height = wrap.clientHeight * dpr;
  canvas.style.width = wrap.clientWidth + 'px';
  canvas.style.height = wrap.clientHeight + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const W = wrap.clientWidth;
  const H = wrap.clientHeight;

  // background
  ctx.fillStyle = '#0b0e14';
  ctx.fillRect(0, 0, W, H);

  if (!state.bars.length) {
    ctx.fillStyle = '#6b7280';
    ctx.font = '13px ui-monospace, monospace';
    ctx.fillText('Drop a bars CSV (or click Demo) to start.', 20, H / 2);
    return;
  }

  // pad
  const padL = 60, padR = 12, padT = 16, padB = 28;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  // y-scale from price extremes
  let lo = Infinity, hi = -Infinity;
  for (const b of state.bars) { lo = Math.min(lo, b.low); hi = Math.max(hi, b.high); }
  const pad = (hi - lo) * 0.08;
  lo -= pad; hi += pad;

  const x = (i) => padL + (i + 0.5) * (plotW / state.bars.length);
  const y = (price) => padT + (1 - (price - lo) / (hi - lo)) * plotH;

  // grid
  ctx.strokeStyle = '#1f2530';
  ctx.lineWidth = 1;
  ctx.font = '11px ui-monospace, monospace';
  ctx.fillStyle = '#6b7280';
  for (let g = 0; g <= 5; g++) {
    const py = padT + (g / 5) * plotH;
    ctx.beginPath(); ctx.moveTo(padL, py); ctx.lineTo(W - padR, py); ctx.stroke();
    const price = hi - (hi - lo) * (g / 5);
    ctx.fillText(price.toFixed(5), 6, py + 3);
  }

  // candles
  const w = Math.max(2, plotW / state.bars.length - 2);
  state.bars.forEach((b, i) => {
    const cx = x(i);
    const yo = y(b.open), yc = y(b.close);
    const yh = y(b.high), yl = y(b.low);
    const isUp = b.close >= b.open;
    ctx.strokeStyle = isUp ? '#2bbc8a' : '#e35d6a';
    ctx.fillStyle = isUp ? '#2bbc8a' : '#e35d6a';
    ctx.beginPath();
    ctx.moveTo(cx, yh); ctx.lineTo(cx, yl); ctx.stroke();
    const top = Math.min(yo, yc);
    const ht = Math.max(1, Math.abs(yc - yo));
    ctx.fillRect(cx - w / 2, top, w, ht);
  });

  // x-axis ticks
  ctx.fillStyle = '#6b7280';
  const step = Math.max(1, Math.floor(state.bars.length / 8));
  for (let i = 0; i < state.bars.length; i += step) {
    const cx = x(i);
    const label = (state.bars[i].ts || '').slice(5, 16);
    ctx.fillText(label, cx - 30, H - 8);
  }

  // overlay gate / notification markers
  // Heuristic: spread non-Dashboard events evenly across bars by index in the
  // event sequence — when the JSONL was produced by godmode-replay, events
  // are emitted bar-by-bar and we approximate by bucketing.
  const eventsPerBar = Math.max(1, Math.floor(state.events.length / state.bars.length));
  state.events.forEach((ev, k) => {
    const barIdx = Math.min(state.bars.length - 1, Math.floor(k / eventsPerBar));
    const cx = x(barIdx);
    if (ev.Notify) {
      const t = ev.Notify.tag;
      let color = null;
      if (t === 'N-I') color = '#2bbc8a';
      else if (t === 'N-J') color = '#f0a84a';
      else if (String(t).startsWith('N-L')) color = '#e35d6a';
      if (color) {
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(cx, padT + 8, 3, 0, Math.PI * 2); ctx.fill();
      }
    } else if (ev.Order) {
      ctx.fillStyle = '#f0a84a';
      ctx.beginPath();
      ctx.moveTo(cx - 4, padT + 18); ctx.lineTo(cx + 4, padT + 18); ctx.lineTo(cx, padT + 24);
      ctx.closePath(); ctx.fill();
    }
  });

  // POC/VAH/VAL from latest dashboard event, if any
  const lastDash = [...state.events].reverse().find((e) => e.Dashboard);
  if (lastDash && lastDash.Dashboard) {
    const d = lastDash.Dashboard;
    const lines = [
      ['POC', d.poc, '#a06bff'],
      ['VAH', d.vah, '#6aa9ff'],
      ['VAL', d.val, '#6aa9ff'],
    ];
    for (const [name, p, col] of lines) {
      if (p < lo || p > hi) continue;
      const py = y(p);
      ctx.strokeStyle = col;
      ctx.setLineDash(name === 'POC' ? [] : [4, 4]);
      ctx.beginPath(); ctx.moveTo(padL, py); ctx.lineTo(W - padR, py); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = col;
      ctx.fillText(`${name} ${p.toFixed(5)}`, W - padR - 90, py - 3);
    }
  }
}

function drawSidebar() {
  // Latest dashboard
  const dashRows = $('dashboard');
  const lastDash = [...state.events].reverse().find((e) => e.Dashboard);
  if (lastDash) {
    const d = lastDash.Dashboard;
    const fmt = [
      ['Symbol', d.symbol],
      ['Mode', d.mode],
      ['Session', d.session],
      ['State', d.state],
      ['Bias', d.bias],
      ['Loc', d.loc],
      ['CVD dir', d.cvd_dir],
      ['Score', `${d.score} P${d.priority}`],
      ['SL', d.sl?.toFixed?.(5) ?? '-'],
      ['R:R', d.rr?.toFixed?.(2) ?? '-'],
      ['POC', d.poc?.toFixed?.(5) ?? '-'],
      ['VAH', d.vah?.toFixed?.(5) ?? '-'],
      ['VAL', d.val?.toFixed?.(5) ?? '-'],
      ['DD %', d.daily_dd_pct?.toFixed?.(2) ?? '-'],
      ['Trades', d.trades_today ?? 0],
    ];
    dashRows.innerHTML = fmt
      .map(([k, v]) => `<div class="row"><span class="k">${k}</span><span>${v}</span></div>`)
      .join('');
  } else {
    dashRows.innerHTML = `<div class="row"><span class="k">— no dashboard event yet —</span></div>`;
  }

  // Gate trace from last bar (find last block of Gate events)
  const gates = state.events.filter((e) => e.Gate);
  const lastN = gates.slice(-9);
  $('gate-list').innerHTML = lastN
    .map((g) => {
      const gg = g.Gate;
      const cls = gg.result.passed ? 'pass' : 'fail';
      const sym = gg.result.passed ? '✓' : '✗';
      return `<div class="gate-row ${cls}">
        <span class="g">${gg.gate}</span>
        <span class="n">${gg.name}</span>
        <span class="r">${sym} ${escape(gg.result.reason)}</span>
      </div>`;
    })
    .join('');

  // Recent notifications
  const notifs = state.events.filter((e) => e.Notify).slice(-12);
  $('notif-list').innerHTML = notifs
    .map((n) => `<div class="notif-row"><span class="tag">${n.Notify.tag}</span> ${escape(n.Notify.msg)}</div>`)
    .join('') || '<div class="notif-row">— none —</div>';

  // Counts
  const counts = state.countsByKind;
  const keys = Object.keys(counts).sort();
  $('counts').innerHTML = keys
    .map((k) => `<div class="row"><span class="k">${k}</span><span>${counts[k]}</span></div>`)
    .join('') || '<div class="row"><span class="k">— none —</span></div>';
}

function escape(s) {
  return String(s).replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));
}

// ---------- demo data ----------

function demoBars() {
  const bars = [];
  const start = new Date('2026-05-05T08:00:00Z').getTime();
  let price = 1.0830;
  for (let i = 0; i < 80; i++) {
    const t = new Date(start + i * 15 * 60_000);
    const drift = (Math.sin(i / 6) + (i > 40 ? -1 : 0.5)) * 0.00015;
    const o = price;
    const c = o + drift + (Math.random() - 0.5) * 0.00015;
    const h = Math.max(o, c) + Math.random() * 0.0002;
    const l = Math.min(o, c) - Math.random() * 0.0002;
    bars.push({
      ts: t.toISOString().slice(0, 16).replace('T', ' '),
      open: o, high: h, low: l, close: c, volume: 1000 + Math.random() * 500,
    });
    price = c;
  }
  return bars;
}

function demoEvents(bars) {
  const ev = [];
  const last = bars[bars.length - 1];
  bars.forEach((b, i) => {
    ev.push({ Gate: { gate: 0, name: 'Kill', result: { passed: true, reason: 'ok', value: 0 }}});
    ev.push({ Gate: { gate: 1, name: 'F2·Session', result: { passed: i < 60, reason: i < 60 ? 'ok' : 'after-hours', value: 0 }}});
    if (i === 30) {
      ev.push({ Notify: { kind: 'AplusReady', tag: 'N-I', msg: 'A+ READY LONG setup=1 score=5 R:R=2.8', ts: bars[30].ts }});
      ev.push({ Notify: { kind: 'TradeFired', tag: 'N-J', msg: 'LONG 0.10 units @ 1.08340 SL 1.08220 TP 1.08670 [MANUAL]', ts: bars[30].ts }});
    }
    if (i === 70) {
      ev.push({ Notify: { kind: 'KillSwitch', tag: 'N-L_SPREAD_BLOWOUT', msg: 'KILL SWITCH: SPREAD_BLOWOUT', ts: bars[70].ts }});
    }
  });
  ev.push({ Dashboard: {
    symbol: 'EURUSD', mode: 'Manual',
    state: 'Balanced', session: 'LdnMain', bias: 'Bull', loc: 'Val', cvd_dir: 'Long',
    footprint_ready: true, sl: 1.08220, rr: 2.8, score: 5, priority: 1,
    cvd: 14820, bar_delta: -842, vol_z: 2.4,
    poc: 1.08670, vah: 1.08920, val: 1.08300,
    daily_dd_pct: -1.2, trades_today: 3,
    last_refresh: last.ts,
  }});
  return ev;
}

window.addEventListener('resize', render);
render();
