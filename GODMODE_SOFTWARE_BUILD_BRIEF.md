# GODMODE Trading OS — Master Build Brief

**Audience:** Claude (design + build agent).
**Author intent:** Eric Bokgabane Mohlathe / AEGO. Single desktop+web trading operating system that ingests the 26-EA GODMODE library, runs the user's $10→$5,000 flip plan, and looks/feels like the union of SierraCharts + Bookmap + TradingView + NinjaTrader + cTrader + MetaTrader + DeepCharts.
**Honesty contract:** Brief §21 + "Proof iFVGs have no edge." Never display fabricated win rates. All performance numbers come from real backtests or live broker fills.

---

## 0. North Star (one paragraph)

A single workstation app — **GODMODE Trading OS** — that connects to MT4/MT5/cTrader/TradingView/Binance/Bybit/IBKR via official APIs, runs the 26 GODMODE archetypes on demo and live accounts, visualises order flow and structure at Bookmap density, journals every entry *and skip*, exposes a Claude-powered analyst pane, and lets the user toggle archetypes/risk-modes/symbols from one dark cockpit. Mobile companion is read-only at v1.

---

## 1. Aesthetic DNA — what we steal from whom

| Platform | What we copy | What we discard |
|---|---|---|
| **SierraCharts** | Information density, multi-pane workspace persistence, study-stack panels, numbers DOM | Dated chrome, MFC-era widgets |
| **Bookmap** | Heatmap depth, footprint, GPU-smooth canvas redraw, time-aligned overlays | Steep learning curve, sparse onboarding |
| **TradingView** | Drawing UX, watchlist sidebar, Pine-style script editor, alert builder, social feed pattern (we omit social) | Webby toolbars, popup ads |
| **NinjaTrader** | Strategy Analyzer + Optimizer UX, ATM templates, market replay scrubber | Java-feel modal dialogs |
| **cTrader** | cBot manager, dark glass theme, control bar over chart, depth ladder | Locked broker tie-in |
| **MetaTrader 5** | Strategy Tester results page (graph + report + journal tabs), MarketWatch column, Navigator tree | MQL-only ecosystem |
| **DeepCharts** | Footprint cluster colouring, imbalance highlighting, low-latency rendering | Single-purpose scope |
| **Figma dashboards** (Linear, Vercel, Stripe, Notion Calendar, Raycast) | Spacing rhythm, micro-interactions, command palette ⌘K, motion curves | Pastel SaaS look |

**House rule:** if a feature exists in two of those platforms, copy the better one verbatim before innovating.

---

## 2. Visual system

### Themes
- **GODMODE Dark** (default). Background `#07090C`, panel `#0E1218`, hairline `#1E2530`, text primary `#E6ECF3`, secondary `#8A96A8`, accent green `#22C55E`, accent red `#EF4444`, accent amber `#F59E0B`, accent cyan `#22D3EE`.
- **GODMODE Tape** (Bookmap-style — black, neon depth gradient).
- **Paper White** (for screenshots / journaling export only).

### Typography
- **UI:** Inter Tight 13/14/16, tabular-numerals on price.
- **Mono / prices / code:** JetBrains Mono 12/13.
- **Charts:** never use serifs.

### Motion
- 120ms ease-out for panel open/close.
- 80ms for hover state.
- No bouncy springs on data. Bouncy only on celebratory milestones (profit-target hit) — Lottie sparkle, dismissable.
- Footprint/heatmap repaint is canvas, target 60 fps even with 500k cells onscreen.

### Components (atomic library, named)
1. **Glass Panel** — `bg-#0E1218/80`, `backdrop-blur-12`, 1px hairline border.
2. **Stat Tile** — label top-left, value 28px tabular, delta chip bottom-right.
3. **Pill Tab** — Linear-style segmented control.
4. **Command Bar (⌘K)** — Raycast clone, fuzzy over symbols/archetypes/settings/AI prompts.
5. **Depth Ladder** — fixed-width tabular DOM with size heatmap behind cells.
6. **Footprint Cell** — bid×ask split with imbalance tint.
7. **Toggle Card** — archetype enable + risk-mode segmented + magic-badge.
8. **Equity Sparkline** — 1px stroke, area gradient, tooltip on hover.
9. **Order Ticket** — Buy/Sell big buttons, qty stepper, SL/TP fields with R preview.
10. **Trade Card** — symbol, direction chevron, R achieved, P/L, EA tag, expand → journal entry.
11. **News Strip** — calendar-style ticker, impact chip (low/med/high), time-to-event countdown.
12. **AI Chat Bubble** — left-aligned analyst replies, citations as numbered chips.

---

## 3. Information architecture — pages

Top-level navigation rail (left, 56px, icon-only, tooltip on hover):

1. **Cockpit** — landing dashboard.
2. **Charts** — multi-pane chart workspace.
3. **DOM / Tape** — depth ladder + time & sales + footprint.
4. **EAs** — the 26-archetype manager.
5. **Backtest** — Strategy Analyzer.
6. **Optimizer** — parameter sweep + walk-forward.
7. **Replay** — historical scrub-bar simulator.
8. **Journal** — trade + skip log, calendar heatmap, R-multiple histogram.
9. **Planner** — goals, targets, milestones, flip ladder.
10. **News & Calendar** — economic events + headline feed.
11. **AI Analyst** — Claude pane with full context.
12. **Accounts** — broker connections, balance, equity, leverage.
13. **Settings** — themes, hotkeys, API keys (encrypted), data sources.

### Cockpit layout (default)
```
+-------------------+-------------------+-------------------+
| Equity Curve      | Today P/L         | Flip Progress     |
| (sparkline + R)   | + open positions  | $10 → $5,000 bar  |
+-------------------+-------------------+-------------------+
| Active Archetypes (cards 4x2, toggle + risk-mode)         |
+----------------------------------------------------------+
| Live Signals Stream | News & Calendar | AI Insight        |
| (last 50 events)    | (next 8 events) | (1-paragraph)     |
+----------------------------------------------------------+
| Open Positions Table (sortable, inline close, R column)   |
+----------------------------------------------------------+
```

### Charts page
- 4-pane grid by default (drag-to-resize, save layouts).
- Each pane: symbol picker, TF picker, study stack (collapsible right-side accordion).
- Drawing tools left rail: trendline, hline, rectangle, fib, measure, FVG, OB, anchor VWAP.
- Top bar: ⌘K command, theme toggle, sync crosshair across panes, replay arm.
- Inline GODMODE dashboard indicator (already built — `TradingView/GODMODE_Dashboard.pine` and cAlgo/MT5 ports) as a togglable overlay.

### DOM / Tape page (Bookmap-style)
- Centre: heatmap of resting liquidity over time (x = time, y = price, colour = size).
- Right: depth ladder (price column, bid size, ask size, cumulative delta column).
- Bottom: time & sales tape with aggressor-tinted prints.
- Optional footprint pane (cluster bars with bid×ask split, imbalance highlight ≥3:1).
- Hotkeys: `B`/`S` market buy/sell at cursor price, `Esc` cancel last, `F` flatten.

### EAs page
- Grid of 26 cards (already exists in `GODMODE_App/index.html` — port and upgrade).
- Each card: name, archetype description tooltip, magic, toggle ON/OFF, risk-mode segmented (Cons/Aggr/Flip), per-symbol enable chips, last fire timestamp, lifetime PF.
- Right pane: portfolio correlation matrix — heatmap of pair returns across enabled EAs (Pearson).
- Bulk-edit drawer: enable/disable groups (ICT, SMC, Wyckoff, AMT, PA, MeanRev, Breakout).

### Backtest page (MT5 Strategy Tester clone, upgraded)
- Top: symbol, period (date range picker), TF, model (every tick / m1 OHLC / open price), spread, initial deposit, leverage.
- Left rail: EA picker (single or basket).
- Run button → live progress bar with live equity curve drawn as it runs.
- Results tabs: **Graph** (equity + drawdown), **Report** (PF/expectancy/Sharpe/Sortino/Calmar/MaxDD/recovery/avg-R), **Trades** (sortable table), **Journal** (skips + entries), **Heatmap** (P/L by hour×day-of-week).
- Export: CSV + PDF report + screenshot.

### Optimizer
- NinjaTrader-style. Parameter list with min/max/step. Genetic + grid + Bayesian options.
- Walk-forward toggle: in-sample %, step %.
- Result grid sorted by user-chosen objective (PF default).
- 3D surface plot (Plotly/three.js) of two-param sweep.

### Replay
- Scrub bar (TradingView/NinjaTrader style) with play/pause, 1×/4×/16×/64× speeds.
- All chart + DOM components re-render against simulated clock.
- User can place sim trades — journal tags them `[REPLAY]`.

### Journal
- Top: calendar heatmap (GitHub-contribution style — green = profit day, red = loss).
- Left: filters (date, EA, symbol, direction, R bucket, outcome, tag).
- Centre: trade card list (virtualised).
- Each trade card expands to: entry chart screenshot (auto-captured), notes field (markdown), screenshot upload, mood selector (0–5), rule-violation checklist.
- Right rail: R-multiple histogram, expectancy curve, win/loss streak chart.
- Skip log tab — all SKIP_RR/SKIP_SIZE/SKIP_FILTER rows from `GODMODE_GMxx_*.csv` (denominator).

### Planner
- **Flip ladder:** $10 → $20 → $50 → $100 → $250 → $500 → $1k → $2.5k → $5k. Show current rung, % to next, expected days at observed expectancy (read-only inference, not a promise).
- **Goals:** SMART goal cards (drag-rank).
- **Targets:** daily R target, weekly $ target, monthly drawdown limit.
- **Calendar:** week/month view, drag economic events in, attach prep notes.
- **Trade plan template** per session (LdnMain/NY AM/NY PM) — pre-fillable form.

### News & Calendar
- ForexFactory-style table: time, currency, impact, event, actual/forecast/previous.
- Live feed (Reuters/Bloomberg headline tickers via licensed API — see §6).
- Auto-flatten or auto-pause rule per impact level (e.g. pause EAs 5 min before High-impact USD).
- Sentiment chip per symbol (rolling 24h, sourced from news + social NLP).

### AI Analyst (Claude pane)
- Right-side drawer, ⌥A toggle.
- Context auto-attached: current symbol, last 200 bars, open positions, today's journal, enabled EAs, recent news.
- Slash commands: `/explain` (current chart), `/critique` (last trade), `/plan` (next session), `/scan` (find archetype setups across watchlist), `/replay-coach` (run replay + critique decisions), `/recap` (end-of-day debrief), `/risk-check` (sanity-check current exposure).
- Citations: when AI references a setup, it links the journal row + chart anchor.
- Streaming responses, 80 col code blocks, markdown render.
- Model selection: Opus 4.7 default, Sonnet 4.6 for fast scans, Haiku 4.5 for ticker enrichment.

### Accounts
- Connection cards per broker: status dot, last heartbeat, equity, balance, free margin, open P/L.
- One-click swap of "active trading account" (binds where new orders go).
- Encrypted credential vault (OS keychain). MFA passthrough where supported.
- Demo↔Live toggle is a prominent guarded action (confirm modal).

### Settings
- Themes, hotkeys (full remap), data sources, API keys, AI keys, telemetry opt-out, journal export path, backup/restore, factory reset.

---

## 4. The 26 EAs — first-class citizens

Ship the existing `MT5_MasterLibrary/` and `cTrader_MasterLibrary/` (already built) as bundled assets. The OS:

1. **Detects platform installs** (MT4/MT5/cTrader paths on disk) and offers one-click copy of EA + indicator files into the right MQL5/Experts and cAlgo/Sources folders.
2. **Reads journals** (`GODMODE_GMxx_*_log.csv`) live — file watchers, no polling.
3. **Sends start/stop commands** via platform APIs where available (cTrader Open API for cBots; MT5 has no remote attach — surface a "open MT5 and attach" CTA with deep-link).
4. **Aggregates fire-rate, skip-rate, direction split, avg score per EA** — same logic as `GODMODE_App/index.html` parser, lifted into the OS.
5. **Backtest panel can launch the MT5 Strategy Tester** via shellexec with prefilled .set file, or use the internal backtester (see §7).

26 archetype list reference: see [cTrader_MasterLibrary/README.md](cTrader_MasterLibrary/README.md) and [MT5_MasterLibrary/README.md](MT5_MasterLibrary/README.md). GM01 ORB through GM26 Confluence Stack.

---

## 5. Indicators — built-in catalog

Beyond the GODMODE dashboard, ship native indicators (do not depend on TradingView):

**Structure:** Swing fractals, BOS/CHoCH, FVG/iFVG, Order Block, Breaker, S&D zones (RBR/DBR/DBD/RBD), Liquidity pools (eq highs/lows), PDH/PDL/PWH/PWL, NDOG/NWOG, Initial Balance, Opening Range.

**Order flow:** CVD (anchored, session, rolling), Delta footprint, Cumulative delta divergence, Open Interest (where data available), Funding rate (crypto), Aggressor ratio, Imbalance highlighter, Absorption flag.

**Volume profile:** Session VP, Visible Range VP, Composite VP, Naked POC tracker, Value Area H/L, HVN/LVN.

**Statistical / AMT:** Anchored VWAP (multi-anchor), σ bands (1/2/3), Z-score, ATR, BB, Keltner, Donchian, Standard-deviation projection lines (helper already in `GODMODE_Core`).

**Momentum/Trend:** EMA stack (8/21/50/200), MACD, RSI, Connors RSI(2), Stochastic, ADX, Ichimoku.

**ICT-specific:** Silver Bullet windows, Killzone shading (LdnOpen/NYAm/NYPm), Power-of-3 phase tagger, OTE Fib zone, SMT divergence cross-pair.

**Harmonic:** XABCD scanner (Gartley/Bat/Butterfly/Crab) — visual + alert.

**Calendar/News overlays:** Vertical lines at high-impact events, blackout-window shading.

Every indicator is GPU-rendered (canvas/WebGL via `lightweight-charts` extended or `tradingview-widget` headless if licensable; otherwise custom on `regl`/`pixi.js`).

---

## 6. Data & connectivity

### Market data
- **Primary feeds:** Polygon.io (US equities + FX + crypto), Databento (futures L2/L3 if user upgrades), CoinAPI (crypto multi-exchange), TradingView UDF for fallback.
- **Broker feeds:** MT4/MT5 (ZeroMQ bridge EA `GODMODE_Bridge.mq5` — to be written), cTrader Open API (OAuth 2 + Protobuf), IBKR (TWS API), Binance/Bybit/OKX (REST + WS), OANDA v20.
- **Tick caching:** local DuckDB or ClickHouse, columnar by symbol/date.
- **News:** Benzinga / Marketaux / NewsAPI / Forex Factory ICS feed. Reuters/Bloomberg only if user has license.
- **Economic calendar:** Trading Economics API or ForexFactory scrape (respect ToS).
- **Social/sentiment:** StockTwits API + X (Twitter) v2 API for cashtags + Reddit API (r/wallstreetbets, r/forex). NLP via Claude or finetuned sentiment model.

### Storage
- SQLite (user DB, settings, journals).
- DuckDB (analytical: backtests, ticks, journals at scale).
- File system: `~/GODMODE/journals/`, `~/GODMODE/backtests/`, `~/GODMODE/workspaces/`.

### Auth & secrets
- OS keychain (macOS Keychain, Windows Credential Manager, libsecret on Linux).
- All third-party keys encrypted at rest. Memory-only decryption.
- No telemetry by default.

---

## 7. Internal backtester + optimizer

Not everyone has MT5 installed. Ship a native engine:

- **Event-driven** (per-tick or per-bar), written in Rust (compiled to native + WASM for in-app web preview). Expose via Tauri command.
- **Slippage / commission models** configurable per symbol.
- **Adapter pattern** — each GODMODE archetype is a strategy class implementing `on_bar` / `on_tick` / `on_order_fill`. The MT5/cTrader source files are kept as canonical; the Rust port is generated from a shared spec YAML per archetype.
- **Result schema** identical to MT5 report (PF, expectancy, Sharpe, Sortino, Calmar, MaxDD, recovery, avg trade R, expectancy by hour/day).
- **Optimizer:** grid, genetic (DEAP-style), Bayesian (Optuna-style — port to Rust or shell out to Python sidecar).
- **Walk-forward:** rolling in-sample/out-of-sample with auto-report.
- **Monte Carlo:** shuffle trade order N times, report DD distribution.
- **Acceptance gates** wired in (PF≥1.5, expectancy>0, DD≤20%, recovery≥2.0) — flag pass/fail per `TESTING.md`.

---

## 8. AI layer (Claude integration)

### Architecture
- **Local agent:** runs in Tauri sidecar, holds an Anthropic SDK client (Opus 4.7 / Sonnet 4.6 / Haiku 4.5).
- **Context builder:** assembles {chart snapshot PNG, last-200-bar OHLCV, open positions, recent journal, enabled EAs, news headlines for symbol's currency/asset class, indicator values at right edge}.
- **Tools (Claude tool-use):** `place_order`, `flatten_all`, `read_journal(filter)`, `run_backtest(ea, symbol, range)`, `draw_on_chart(anchor, shape)`, `search_news(query)`, `query_calendar(date_range)`, `get_market_depth(symbol)`, `screenshot_chart()`.
- **Guardrails:** `place_order` and `flatten_all` are **never auto-confirmed**. Claude proposes, user confirms in a modal showing the order ticket + risk preview.
- **Streaming:** SSE → UI bubbles render incrementally.
- **Memory:** per-user vector store (Qdrant local or sqlite-vec) of journal entries and prior AI sessions → RAG over their own history.

### Slash command catalog
- `/explain` — read chart + indicators → 4-sentence regime call.
- `/scan <watchlist>` — Haiku batch over symbols → ranked archetype-setup table.
- `/critique <trade-id>` — read the trade, the rules of that EA, and the chart at entry → "was this in spec, was it a good trade independent of outcome".
- `/plan` — read calendar, news, current account state → next-session plan with go/no-go per killzone.
- `/recap` — end-of-day: P/L, R distribution, rule violations, top mistakes.
- `/risk-check` — total exposure, correlated open positions, news within next 60 min, drawdown vs daily cap.
- `/journal "text"` — append free-text note to today's journal with chart auto-attach.
- `/coach replay` — load replay, ask coaching questions in-line.

### Cost control
- Token budget per session (configurable). Display running cost in status bar.
- Aggressive prompt-cache reuse; system prompt = static for the day.
- Vision calls (chart screenshots) only on explicit user invoke or scheduled `/recap`.

---

## 9. Automation engine

### Triggers (when…)
- Time (cron / killzone).
- Price (cross level, % move).
- Indicator (RSI crosses, BOS, FVG fill).
- News (impact ≥ medium for currency X).
- EA fire (signal from journal file watcher).
- AI insight (Claude flags condition).
- Account (drawdown threshold, free margin %).

### Actions (then…)
- Place order (with template).
- Flatten symbol / all.
- Disable EA / enable EA.
- Switch risk mode.
- Send notification (push / email / Telegram / Discord / phone via Twilio).
- Run backtest.
- Capture screenshot to journal.
- Prompt Claude with template.

### UI
- Zapier-style node editor (React Flow). Drag trigger → condition → action. Save as **"Playbooks"**.
- Built-in playbooks shipped:
  - "Flatten 5 min before red news for that currency."
  - "If daily DD > 4%, halt all EAs until tomorrow."
  - "If GM26 ConfluenceStack fires with score ≥ 5, enable Aggressive mode for that EA on that symbol for 30 min."
  - "Daily 22:00 SAST: run `/recap` and email me."

---

## 10. Alerts & notifications

- In-app toast (Linear-style, top-right, stackable).
- OS notification.
- Push to mobile companion (Expo push).
- Email (SES / Resend).
- Telegram / Discord webhooks.
- Phone call for **critical** only (Twilio) — e.g. margin call.

User builds alert from any indicator/EA/playbook with a "Create alert" button (TradingView-style).

---

## 11. Tech stack (recommended)

| Layer | Choice | Why |
|---|---|---|
| Desktop shell | **Tauri 2** (Rust core + webview frontend) | Tiny binary, native perf, multi-window, Bookmap-grade canvas perf with WebGL |
| Frontend framework | **React 19 + TypeScript** | Ecosystem; Tauri-first plugins |
| Styling | **Tailwind CSS 4 + shadcn/ui** (themed) | Vercel-grade speed of build, easy theme tokens |
| State | **Zustand** + **TanStack Query** | Simple, fast, well-typed |
| Charts | **lightweight-charts** + custom WebGL layer (regl/pixi) for depth/footprint | License-friendly; perf where needed |
| Charts (drawing/scripting) | Custom canvas + AST-based mini script engine (Pine-subset) | Avoid TradingView lock-in |
| Backtest/optim engine | **Rust** + **Polars** | Speed, deterministic |
| ML/AI Python sidecar | Optuna, scikit, statsmodels via PyO3 or subprocess | Only when Rust lacks |
| Anthropic SDK | **`@anthropic-ai/sdk` (TS)** in renderer, **`anthropic-sdk-python`** in sidecar for batch | Latest models, streaming, tool-use |
| DB | **DuckDB** (analytical), **SQLite** (transactional), **sqlite-vec / Qdrant** (RAG) | Embedded |
| Auth & secrets | **OS keychain** via Tauri plugin | No cloud secret risk |
| Mobile companion | **Expo (React Native) + Tamagui** | Code share with web |
| Web companion | Same React 19 codebase, deployed to Vercel | Already started — `GODMODE_App/index.html` is the spike |
| Real-time bus | Tauri events + WS reconnects | Low latency UI |
| Telemetry (opt-in) | PostHog self-hosted | User owns data |

---

## 12. Build phases

**Phase 0 — Scaffolding (1 wk).** Tauri shell, theme tokens, command palette, sidebar nav, settings page, keychain plug, OS notifications. CI on macOS + Windows.

**Phase 1 — Charts + Indicators (3 wk).** lightweight-charts integration, drawing tools, study system, ship 20 highest-value indicators including the GODMODE dashboard parity.

**Phase 2 — Accounts + Live data (3 wk).** Broker adapters: cTrader Open API first (cleanest), then MT5 via ZMQ bridge EA, then Binance/Bybit, then IBKR. MarketWatch panel. Account swap. Demo↔Live guard.

**Phase 3 — EAs panel + Journal ingestion (2 wk).** Port `GODMODE_App` to the OS, hook file watchers on CSV journals, render per-EA stats, correlation matrix.

**Phase 4 — Internal backtester + Optimizer (4 wk).** Rust engine, port GM01–GM26 specs to spec YAML + Rust strategy modules, results UI parity with MT5 Strategy Tester, optimizer.

**Phase 5 — DOM / Tape / Footprint (3 wk).** WebGL depth heatmap, tape, footprint. Requires L2 data feed wired.

**Phase 6 — AI Analyst (2 wk).** Claude pane, slash commands, tool-use with order/flatten/draw, RAG over journal.

**Phase 7 — Replay (1 wk).** Historical scrub against tick store.

**Phase 8 — Automation engine + Alerts (2 wk).** React Flow editor, playbook templates, notification fan-out.

**Phase 9 — Planner / Calendar / News (2 wk).** Flip ladder, goals, calendar with event imports, news feed integration.

**Phase 10 — Mobile companion (3 wk).** Read-only v1: positions, journal, alerts, AI recap.

**Total:** ~26 weeks for full v1 with a small team; ship incrementally — Phases 0–3 give a usable product.

---

## 13. Folder layout (target repo)

```
godmode-os/
├── apps/
│   ├── desktop/         # Tauri shell + React renderer
│   ├── mobile/          # Expo
│   └── web/             # SSR/SPA mirror of desktop
├── packages/
│   ├── ui/              # shadcn-extended component lib (themed)
│   ├── charts/          # lightweight-charts wrappers + custom WebGL
│   ├── indicators/      # All indicator implementations (TS)
│   ├── ea-specs/        # YAML specs for each GODMODE archetype
│   ├── ea-mt5/          # symlink → ../../MT5_MasterLibrary
│   ├── ea-ctrader/      # symlink → ../../cTrader_MasterLibrary
│   ├── ai/              # Claude tool defs, slash commands, RAG
│   ├── adapters/        # broker + data adapters
│   ├── backtest-engine/ # Rust crate (cargo workspace member)
│   └── shared/          # types, schemas
├── crates/
│   ├── backtest/        # Rust backtester
│   └── optimizer/       # Rust optimizer
├── infra/
│   └── ci/
└── docs/
    └── BUILD_BRIEF.md   # this file
```

---

## 14. Non-negotiable contracts

1. **Order placement is always user-confirmed** unless the user explicitly enabled a fully-autonomous playbook AND signed the on-screen disclaimer in Settings.
2. **No fabricated stats.** Every shown win-rate/PF/expectancy must trace to a real run ID. If unknown → display `—`.
3. **All times displayed in user's timezone (SAST default for Eric) and in broker time alongside.**
4. **Skip-logging is first-class.** A skipped signal is rendered with the same weight as an entry in journal pages.
5. **The OS is the source of truth for the user's account state at the moment of display.** Never extrapolate.
6. **Themes and density are user choices.** Default to dense (SierraCharts level). Provide a "comfort" toggle that loosens spacing for new users.
7. **Reversible destructive actions.** Flatten All / Disable All EAs require typing `FLATTEN` or `STOP` in a modal.
8. **Honesty banner.** A small permanent line in the footer: "Past performance ≠ future. Tested edges decay. — GODMODE."

---

## 15. Mood references — go look at these

(Brief writer instruction to Claude: open + study these before drawing the first frame.)

- **SierraCharts** — Numbers DOM screenshots; chart-pane study stack.
- **Bookmap** — heatmap landing page hero; the way size pulses.
- **TradingView Desktop** — left rail drawing tools; alert builder modal; ⌘K palette.
- **NinjaTrader 8** — Strategy Analyzer + Optimizer surface plot.
- **cTrader Desktop** — control bar, depth ladder, cBot manager.
- **MT5** — Strategy Tester results tabs; Navigator; MarketWatch.
- **DeepCharts** — footprint cluster cell colouring.
- **Linear app** — sidebar density, ⌘K, animations.
- **Raycast** — command bar UX.
- **Vercel dashboard** — empty states, stat tiles.
- **Notion Calendar (Cron)** — calendar UX.
- **Stripe Dashboard** — table density, tab transitions.
- **Figma Community searches:** "trading dashboard dark", "fintech analytics dark", "bookmap", "trading journal", "crypto exchange dashboard". Pull 30+ screens, distil what reads as "professional terminal" not "fintech SaaS pastel."
- **YouTube channels for motion cues:** Bookmap official, Trader Dale (DOM), Axia Futures (footprint), TJR (SMC overlays), ICT (ranges/overlays), MicheleSchneider, Brian Shannon (anchored VWAP UI).
- **Dribbble / X (Twitter)** searches: `from:@figma "trading"`, `"trading terminal" filter:image`, `"bookmap" filter:image`.

---

## 16. Acceptance — "is it GODMODE?"

The v1 release is GODMODE if **all** of these are true:

- [ ] Opens in <2 s cold on a 2020 M1 MacBook Air.
- [ ] Can render 4 charts × 5000 bars + 2 indicators each at 60 fps while a heatmap repaints alongside.
- [ ] Connects to at least one demo broker (cTrader sandbox) and places a real order via the OS, end-to-end, in <500 ms p95.
- [ ] Loads a `GODMODE_GMxx_*.csv` journal of 10,000 rows and renders the EA card in <300 ms.
- [ ] Runs an internal backtest of GM01 on EURUSD M15 over 5 years in <30 s.
- [ ] Claude `/explain` returns first token in <1.2 s on cached prompt.
- [ ] Zero crashes through a 4-hour LdnMain→NY session of real use.
- [ ] Every shown number is sourced (hover → "from run abc123 at 2026-…" or "from broker XYZ heartbeat 12s ago").
- [ ] Looks like SierraCharts × Linear × Bookmap. Screenshots are immediately recognisable as "not just another Electron trading app."

---

## 17. Open questions for Eric (resolve before Phase 1)

1. Primary live broker for v1 (cTrader Open API recommended; alternative IC Markets MT5)?
2. Primary L2 data source budget — Databento ($) vs broker-supplied L2 (free but narrower)?
3. Mobile platform priority — iOS only (Eric on iCloud) or both?
4. Hosting model — desktop-only or also web SaaS (multi-tenant)?
5. Any compliance scope (FSCA SA / regulated entity) — affects whether OS can take orders on behalf of others vs. self-trading only.
6. Naming: keep **GODMODE Trading OS** or rebrand under **AEGO**?

---

## 18. Inputs already in this repo to reuse

- `MT5_MasterLibrary/` — 26 EAs + Core + Dashboard indicator (MQL5). Reuse as canonical strategy source.
- `cTrader_MasterLibrary/` — 26 cBots + Core + Dashboard indicator (cAlgo C#).
- `TradingView/GODMODE_Dashboard.pine` — Pine v5 dashboard. Port the visual layer.
- `GODMODE_App/index.html` — first-cut SaaS dashboard. **This is the seed of the EAs page.** Lift the journal parser verbatim.
- `GODMODE_OFEA_MASTER_COMPENDIUM.md` — strategy archetype taxonomy, source authority.
- `TESTING.md` — backtest acceptance protocol — bake into the Backtest page.
- `build foundation/.../CLAUDE_CODE_BUILD_BRIEF.pdf` — 24-page source authority for strategies.

---

## 19. Deliverables (what Claude returns at end of design phase)

1. **Figma file** with: design tokens, component library, all 13 page layouts, dark + tape themes, motion specs.
2. **Tauri scaffold repo** at `godmode-os/` matching the folder layout in §13.
3. **One working vertical slice** — Cockpit page + Charts page + Accounts page with cTrader demo connection — buildable on macOS in one `pnpm build`.
4. **EA spec YAML** for GM01 and GM26 (one simple, one meta) as the template for the other 24.
5. **Build plan markdown** restating §12 with ticket-level breakdown.

---

**End of brief. Now go build it like the man who's flipping ten dollars to five thousand needs it to ship Monday.**
