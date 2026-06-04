# GODMODE_OFEA — TradingView (Pine Script v6)

Third platform port of GODMODE_OFEA. **Brief §19 rule 1 forbids Pine** —
this build exists only because the operator explicitly overrode that rule.
Read the deviations section before relying on this build for capital.

## Files

| File | Purpose |
|---|---|
| `GODMODE_OFEA.pine` | Indicator mode. Operator-facing live tool: dashboard, alerts, drawings, MODE_MANUAL by default. |
| `GODMODE_OFEA_strategy.pine` | Strategy mode. Wraps the same gate logic in `strategy.entry()` for TradingView's built-in backtester (§14 acceptance). |
| `lib_orderflow.pine` | Pine library exporting §11 primitives (`bar_delta`, `cvd_daily`, `absorption_stars`, `bullish_divergence`, `bearish_divergence`, `sast_session`, `htf_bias`, `pace_of_tape`). Publish once, import from any script. |

## What Pine cannot do — §26 honest deviations from the brief

Brief §19 rule 1 reads: *"Do not use TradingView, Pine Script, or webhooks."*
You override that, fine — but understand what changes:

| Brief feature | MT5/cTrader | TradingView Pine |
|---|---|---|
| Tick-level aggressor (MqlTick.flags / TickType) | ✓ native | ✗ approximated via close-position-in-range |
| File-system CSV journal (§13) | ✓ native | ✗ `log.info()` sink only — copy/paste from Pine Log pane |
| Multi-broker order routing | ✓ native | ✗ alerts → webhook (3Commas/AutoView/broker's native) |
| Sierra Chart file bridge (§25) | ✓ via SierraChartBridge | ✗ no file I/O — use manual-level inputs instead |
| Bookmap file bridge (§25) | ✓ via BookmapBridge | ✗ same — no file I/O |
| Google Sheets HTTP pull (§25) | ✓ via GoogleSheetsLevels | ✗ no HTTP — 4 hand-typed `input.price()` slots |
| Iceberg with depth tracking (§25) | ✓ true microstructure | ✗ no depth on Pine — price-pattern proxy only |
| Setup #23 Unfinished Auction | ✓ footprint-grade | ✗ price-pattern proxy |
| Setup #24 Poor High/Low | ✓ tick-precision | ✗ bar-precision proxy |
| Setups #01–22 + #25 | ✓ all 22 ported | ✓ subset of 11 wired with priority order |
| 5-gate confluence stack | ✓ canonical | ✓ same logic, gate-by-gate dashboard |
| N-A..N-L cascade | ✓ 12 tags | ✓ 8 alert() tags + N-V (Pace) + N-Y (Manual Level) |
| §3 dashboard | ✓ OBJ_LABEL panel | ✓ `table.new()` top-right panel |
| Hard risk cap 2% (§12 rule 2) | ✓ hardcoded clamp | ✓ `minval=0, maxval=2.0` on input |
| 5% daily DD halt | ✓ flatten + halt | ✓ strategy mode only — advisory in indicator mode |

## How to load each file in TradingView

### `GODMODE_OFEA.pine` (live indicator)

1. Open the TradingView chart for the symbol you want (e.g. EURUSD).
2. Top toolbar → **Pine Editor** (open the editor pane).
3. Click into the editor, **Ctrl+A** to select all, **Delete**.
4. Open `GODMODE_OFEA.pine` from this repo, copy entire contents.
5. Paste into the Pine Editor.
6. Click **Save** (top-right) → name it `GODMODE_OFEA`.
7. Click **Add to chart**.
8. Configure inputs in the settings dialog that pops up:
   - `Operating Mode` = **MANUAL** for first 30 days
   - `Trade LDN Main` = true, `Trade NY Main` = true
   - All other defaults stay
9. Dashboard appears top-right of chart. Alerts fire automatically when
   gates light up.

### `GODMODE_OFEA_strategy.pine` (backtester)

Same Pine Editor flow but save it as a separate script. When added to chart,
TradingView shows the **Strategy Tester** panel at the bottom with:

- Net profit
- Profit factor (brief §14 target ≥ 1.5)
- Max drawdown
- Win rate
- Sharpe / Sortino
- List of all trades

Brief §14 acceptance: ≥ 6 months EURUSD M5 with PF ≥ 1.5, Recovery ≥ 2.0,
DD ≤ 12%.

### `lib_orderflow.pine` (library)

Libraries are special in Pine — they have to be **published** before they
can be imported.

1. Paste `lib_orderflow.pine` into the Pine Editor.
2. Click **Publish library** (top-right dropdown, not "Add to chart").
3. Choose **Private** if you don't want others using it.
4. After publishing, you can import in any other Pine script:
   ```pinescript
   //@version=6
   indicator("My OF Tool")
   import yourtradingviewname/lib_orderflow/1 as of
   plot(of.cvd_daily())
   plot(of.pace_of_tape(60))
   ```

If you don't want to publish: just copy the function bodies inline into
your script. No import needed.

## Setting up alerts (the N-A..N-I cascade)

After adding the indicator to a chart:

1. Top toolbar → **Alert** (bell icon)
2. Condition: select **GODMODE_OFEA → Any alert() function call**
3. Set alert name (e.g. "GODMODE EURUSD M5")
4. Notification options:
   - **Pop-up** → desktop notification
   - **Email** → tradingview emails you
   - **Webhook URL** → for automation; paste a 3Commas / AutoView / broker's
     webhook URL here. Each N-tag fires its own `alert()` so the webhook
     body distinguishes N-A from N-I etc.
   - **Mobile app** → push notification to phone

Brief §18 user story: when N-I fires ("A+ READY"), the operator gets a push
notification with the setup details and decides to take or skip. The chart
already shows the A+ arrow.

## TradingView-side automation (MODE_AUTO substitute)

Pine cannot place orders directly. To automate:

1. Open an account with a broker that supports webhook signals
   (e.g. AlpacaMarkets, Capitalise.ai, 3Commas, AutoView, OANDA via
   middleware).
2. In your alert config, set the **Webhook URL** to your broker/middleware.
3. In the **Message** field, paste a JSON template that your service
   expects. Example for 3Commas:
   ```json
   {"action": "{{strategy.order.action}}", "symbol": "{{ticker}}", "price": {{close}}, "size": "1%"}
   ```
   Adapt to your service's docs.
4. When N-I fires, the alert hits the webhook, the service places the
   order. **You** are responsible for the brokerage chain — TradingView
   just emits the signal.

## Backtester run (Strategy Tester)

1. Add `GODMODE_OFEA_strategy.pine` to a chart.
2. Set timeframe to M5 (or whatever you'll trade).
3. Click **Strategy Tester** panel at the bottom.
4. The **Performance Summary** tab shows the brief §14 acceptance numbers.
5. **List of Trades** tab is your journal — export to CSV via the three-
   dot menu top-right of the panel for analysis.

Brief §14 thresholds:
- 6 months EURUSD M5 minimum
- PF ≥ 1.5
- Win rate ≥ 65% on filtered trades (note: §21 caveats apply — chase
  expectancy, not win rate)
- Max DD ≤ 12%
- Recovery Factor ≥ 2.0

## Mac-specific notes

Pine runs entirely in your TradingView browser tab — there is no native
desktop install required for Mac. **This is why Pine is the easy answer
for Mac users:** no Windows VM, no .algo compilation, no Parallels. Just
log in to TradingView, paste, save, add to chart.

That said: Pine's order-flow accuracy is materially weaker than MT5/cTrader
because of the tick-data limitation. If you can run MT5 on Mac (native
client exists), you get better signal quality. If you can build a .algo
on a Windows VM, cTrader gives you the best signal quality. Pine is the
"least friction, lowest signal quality" option.

## §22 marginal-gain stack in Pine

The eight refinements from brief §22 in Pine:

| Refinement | Pine implementation |
|---|---|
| M1 Liquidity sweep | Wired in `det_LiqSwp()` setup detector |
| M2 Two-touch rule | Add a per-level touch counter — sketch in code comments |
| M3 ATR regime filter | One-liner check on `ta.atr(14) / request.security(syminfo.tickerid, "D", ta.atr(14))[1]` |
| M4 Tiered news blackout | TradingView has no native news feed — wire to external alert from earnings calendar |
| M5 Dual-CVD | `request.security("DXY", timeframe.period, cvd_daily())` cross-comparison |
| M6 Sub-window tiering | Already wired in dashboard logic via `sastMinute()` ranges |
| M7 Slippage gate | Not measurable in Pine — leave OFF |
| M8 Adaptive setup tiering | Use TradingView's "Strategy Tester → Performance → by-Symbol" output manually |

## Brief mapping table

| Brief § | Pine implementation |
|---|---|
| §1 Trading thesis | Header comment of `GODMODE_OFEA.pine` |
| §2 5-gate stack | `g0_kill ... g8_score` in main file |
| §3 Dashboard | `table.new()` block, 14 rows |
| §4 Notification cascade | `alert()` calls keyed N-A..N-Y |
| §5 Execution flow | Bar-close evaluation (Pine's `barstate.isconfirmed`) |
| §6 25 setups | Subset of 11 wired with priority chain |
| §7 Inputs | `input.*` calls at top, byte-parity names |
| §8 Modular structure | Pine has no `#include` — all in one file or via `lib_orderflow.pine` import |
| §9 Visuals | `plot()`, `plotshape()`, `bgcolor()` |
| §10 State management | `var` declarations + `barstate` |
| §11 Algorithms | Inline + exported in `lib_orderflow.pine` |
| §12 Risk + kill switches | Strategy file only (indicator is advisory) |
| §13 Journal | `log.info()` sink |
| §14 Testing | TradingView Strategy Tester |
| §15 Code quality | Pine v6 has limited modularity — single-file is conventional |
| §17 Build order | N/A (Pine is interpreted) |
| §18 User story | N-I alert is the acceptance trigger |
| §19 Hard prohibitions | Rule 1 (no TV) explicitly overridden by operator |
| §20–§24 Standing order | Apply same operator discipline: MANUAL first 30 days, etc. |
| §25 External data | Reduced to 4 `input.price()` manual-level slots + Pace-of-Tape proxy |
| §26 (NEW) Pine deviations | This README + header comment block |
