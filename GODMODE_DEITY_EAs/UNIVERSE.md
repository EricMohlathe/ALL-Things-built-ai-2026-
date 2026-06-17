# GODMODE Validated Universe — full D1 edge roster

**160 validated symbol-setup slots** across forex / metals / energy / ags / indices /
bonds / crypto / ETFs. Aggregate **~4.33 trades/day** if all run concurrently —
every trade a cost-adjusted, out-of-sample-positive edge (PF>=1.4, >=25 trades, net+ full AND OOS).

Each slot trades ~weekly; the PORTFOLIO trades several times daily. That is the honest path to
3-6 trades/day — breadth of validated edges, NOT intraday frequency (which fails after costs).

The `GODMODE_UniversalController` (MT5+cTrader) ships a broker-deployable subset (~96 common
instruments, ~2.58/day) as its default roster. Append the rows below that YOUR broker carries
(ETFs, grains, bonds) to push toward the full ~4.33/day. Re-validate each in the Strategy Tester.

| # | setup | market | PF | WR% | trades | OOS PF | exits |
|--|--|--|--|--|--|--|--|
| 1 | gm22_amd | GOLD | 9.90 | 94 | 35 | 99.00 | {'stop_atr': 3, 'tp_atr': 1} |
| 2 | gm14_spring | SILVER | 6.18 | 72 | 53 | 10.59 | {} |
| 3 | gm22_amd | EFA | 5.15 | 70 | 30 | 2.80 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 4 | rsi2 | 6J | 4.73 | 76 | 45 | 2.88 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 5 | gm16_sos | SPY | 4.19 | 78 | 49 | 5.31 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 6 | gm22_amd | USO | 3.77 | 62 | 26 | 38.54 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 7 | gm22_amd | GDX | 3.70 | 72 | 39 | 19.80 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 8 | gm11_stackbull | GOLD | 3.38 | 76 | 58 | 6.48 | {'stop_atr': 3, 'tp_atr': 1} |
| 9 | gm11_stackbull | DOGEUSDT | 3.17 | 72 | 47 | 3.69 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 10 | gm16_sos | NKD=F | 3.15 | 72 | 58 | 2.99 | {'stop_atr': 3, 'tp_atr': 1} |
| 11 | gm14_spring | NATGAS | 3.07 | 78 | 58 | 3.35 | {'stop_atr': 3, 'tp_atr': 1} |
| 12 | gm16_sos | XLK | 2.95 | 83 | 47 | 2.49 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 13 | gm16_sos | NQ | 2.90 | 64 | 59 | 2.31 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 14 | gm16_sos | ES | 2.87 | 84 | 61 | 1.81 | {'stop_atr': 3, 'tp_atr': 1} |
| 15 | gm22_amd | YM | 2.83 | 79 | 58 | 5.20 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 16 | gm22_amd | OIL | 2.74 | 81 | 53 | 3.12 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 17 | gm22_amd | CL=F | 2.74 | 81 | 53 | 3.12 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 18 | gm18_liqsweep | PLATINUM | 2.72 | 78 | 59 | 1.45 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 19 | gm22_amd | XLF | 2.67 | 62 | 45 | 1.86 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 20 | gm22_amd | SILVER | 2.64 | 77 | 30 | 5.03 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 21 | gm14_spring | CHFJPY | 2.58 | 71 | 58 | 2.85 | {} |
| 22 | gm14_spring | EURJPY | 2.55 | 75 | 59 | 1.87 | {} |
| 23 | gm14_spring | YM | 2.48 | 81 | 58 | 2.01 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 24 | gm16_sos | SOLUSDT | 2.48 | 49 | 43 | 1.29 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 25 | gm16_sos | DOGEUSDT | 2.47 | 55 | 51 | 2.27 | {} |
| 26 | gm16_sos | QQQ | 2.46 | 57 | 49 | 1.45 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 27 | gm11_stackbull | COPPER | 2.46 | 77 | 64 | 3.59 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 28 | gm22_amd | ZL=F | 2.44 | 75 | 56 | 2.04 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 29 | gm16_sos | LE=F | 2.44 | 77 | 61 | 2.68 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 30 | gm16_sos | GLD | 2.43 | 60 | 52 | 3.65 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 31 | gm18_liqsweep | XLE | 2.43 | 77 | 111 | 3.97 | {'stop_atr': 3, 'tp_atr': 1} |
| 32 | gm16_sos | HO=F | 2.42 | 52 | 54 | 2.70 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 33 | gm14_spring | XLF | 2.41 | 55 | 56 | 2.35 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 34 | gm14_spring | NKD=F | 2.40 | 68 | 57 | 3.59 | {} |
| 35 | gm16_sos | YM | 2.39 | 58 | 67 | 1.85 | {} |
| 36 | gm16_sos | EEM | 2.39 | 59 | 34 | 3.22 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 37 | gm22_amd | ZO=F | 2.37 | 67 | 42 | 11.44 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 38 | gm14_spring | USDZAR | 2.37 | 66 | 64 | 1.58 | {} |
| 39 | gm15_upthrust | EURCHF | 2.36 | 68 | 56 | 3.26 | {'stop_atr': 3, 'tp_atr': 1} |
| 40 | gm16_sos | XLF | 2.33 | 56 | 54 | 3.24 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 41 | archon_orb | AUDCHF | 2.33 | 67 | 85 | 2.27 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 42 | rsi2 | QQQ | 2.33 | 74 | 77 | 3.61 | {} |
| 43 | gm14_spring | GOLD | 2.29 | 76 | 49 | 2.78 | {'stop_atr': 3, 'tp_atr': 1} |
| 44 | gm18_liqsweep | CC=F | 2.26 | 52 | 92 | 2.74 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 45 | gm22_amd | NKD=F | 2.23 | 65 | 60 | 5.87 | {} |
| 46 | gm22_amd | HE=F | 2.22 | 71 | 42 | 1.87 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 47 | gm14_spring | SLV | 2.21 | 54 | 54 | 11.62 | {} |
| 48 | gm22_amd | EEM | 2.21 | 65 | 26 | 47.35 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 49 | gm15_upthrust | CADCHF | 2.18 | 66 | 62 | 1.73 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 50 | gm14_spring | GLD | 2.17 | 62 | 53 | 4.17 | {} |
| 51 | gm11_stackbull | GLD | 2.14 | 52 | 87 | 4.04 | {} |
| 52 | gm11_stackbull | SPY | 2.14 | 50 | 90 | 2.66 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 53 | rsi2 | ES | 2.14 | 78 | 78 | 9.89 | {} |
| 54 | gm15_upthrust | ZN | 2.08 | 73 | 59 | 1.66 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 55 | rsi2 | NKD=F | 2.08 | 78 | 67 | 5.61 | {} |
| 56 | gm14_spring | DIA | 2.08 | 78 | 51 | 1.90 | {} |
| 57 | rsi2 | NQ | 2.06 | 72 | 75 | 4.10 | {} |
| 58 | gm11_stackbull | PLATINUM | 2.04 | 63 | 38 | 2.26 | {'stop_atr': 3, 'tp_atr': 1} |
| 59 | gm11_stackbull | NKD=F | 2.04 | 52 | 87 | 4.17 | {} |
| 60 | gm15_upthrust | TLT | 2.03 | 77 | 47 | 2.08 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 61 | rsi2 | SPY | 2.02 | 77 | 78 | 6.45 | {} |
| 62 | rsi2 | NATGAS | 2.02 | 74 | 42 | 1.58 | {'stop_atr': 3, 'tp_atr': 1} |
| 63 | gm14_spring | NZDJPY | 1.99 | 50 | 62 | 1.94 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 64 | gm14_spring | GBPJPY | 1.99 | 72 | 54 | 1.79 | {} |
| 65 | gm11_stackbull | DIA | 1.97 | 48 | 82 | 1.79 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 66 | gm15_upthrust | GBPCHF | 1.97 | 63 | 60 | 2.06 | {} |
| 67 | archon_tsmom | XLE | 1.95 | 52 | 25 | 3.47 | {'stop_atr': 3, 'tp_atr': 6} |
| 68 | rsi2 | XLK | 1.94 | 66 | 68 | 2.25 | {} |
| 69 | gm16_sos | BNBUSDT | 1.92 | 50 | 68 | 1.36 | {} |
| 70 | archon_orb | DOGEUSDT | 1.89 | 55 | 98 | 1.72 | {} |
| 71 | gm15_upthrust | PLATINUM | 1.89 | 69 | 29 | 2.28 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 72 | gm11_stackbull | ETHUSDT | 1.89 | 49 | 77 | 1.86 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 73 | gm11_stackbull | XLF | 1.89 | 74 | 88 | 1.86 | {'stop_atr': 3, 'tp_atr': 1} |
| 74 | archon_orb | HO=F | 1.88 | 49 | 96 | 1.45 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 75 | archon_tsmom | WHEAT | 1.88 | 49 | 99 | 2.62 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 76 | gm18_liqsweep | USDZAR | 1.88 | 65 | 104 | 2.73 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 77 | rsi2 | YM | 1.87 | 74 | 82 | 1.53 | {} |
| 78 | archon_tsmom | USDSEK | 1.86 | 68 | 80 | 2.23 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 79 | gm16_sos | BRENT | 1.86 | 53 | 49 | 1.41 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 80 | gm16_sos | ETHUSDT | 1.85 | 55 | 66 | 1.33 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 81 | archon_tsmom | NQ | 1.83 | 41 | 97 | 1.68 | {} |
| 82 | gm16_sos | SILVER | 1.83 | 57 | 49 | 2.91 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 83 | gm15_upthrust | ZB | 1.82 | 63 | 59 | 1.45 | {} |
| 84 | gm14_spring | CC=F | 1.82 | 52 | 62 | 1.55 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 85 | rsi2 | IWM | 1.82 | 61 | 62 | 2.99 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 86 | archon_tsmom | AUDCHF | 1.82 | 67 | 87 | 2.55 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 87 | gm24_poorhl | NQ | 1.82 | 46 | 56 | 1.57 | {'stop_atr': 3, 'tp_atr': 6} |
| 88 | gm14_spring | GBPNZD | 1.80 | 51 | 57 | 1.89 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 89 | gm22_amd | LTCUSDT | 1.80 | 70 | 46 | 4.14 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 90 | gm11_stackbull | LINKUSDT | 1.79 | 48 | 27 | 1.53 | {} |
| 91 | gm11_stackbull | XLE | 1.77 | 47 | 85 | 1.19 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 92 | gm16_sos | XRPUSDT | 1.75 | 43 | 53 | 1.91 | {} |
| 93 | gm24_poorhl | TLT | 1.73 | 70 | 131 | 1.68 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 94 | archon_tsmom | OIL | 1.72 | 36 | 70 | 1.12 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 95 | archon_tsmom | CL=F | 1.72 | 36 | 70 | 1.12 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 96 | gm14_spring | ES | 1.72 | 78 | 50 | 1.24 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 97 | archon_tsmom | USDSGD | 1.71 | 43 | 77 | 2.74 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 98 | gm11_stackbull | XRPUSDT | 1.70 | 62 | 53 | 32.22 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 99 | rsi2 | DIA | 1.69 | 67 | 82 | 1.41 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 100 | archon_tsmom | CHFJPY | 1.69 | 72 | 78 | 1.80 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 101 | gm11_stackbull | NQ | 1.68 | 51 | 90 | 2.50 | {'stop_atr': 3, 'tp_atr': 6} |
| 102 | gm11_stackbull | GDX | 1.68 | 79 | 75 | 1.59 | {'stop_atr': 3, 'tp_atr': 1} |
| 103 | gm16_sos | ZS=F | 1.67 | 48 | 48 | 1.96 | {} |
| 104 | gm14_spring | NQ | 1.67 | 78 | 50 | 1.18 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 105 | gm16_sos | SUGAR | 1.66 | 45 | 53 | 1.70 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 106 | gm15_upthrust | AUDCHF | 1.66 | 64 | 61 | 2.87 | {} |
| 107 | gm24_poorhl | 6B | 1.65 | 47 | 43 | 2.40 | {'stop_atr': 3, 'tp_atr': 6} |
| 108 | archon_tsmom | EURNZD | 1.65 | 50 | 86 | 2.67 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 109 | gm14_spring | EURGBP | 1.65 | 62 | 55 | 1.97 | {} |
| 110 | gm11_stackbull | CC=F | 1.64 | 55 | 69 | 1.54 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 111 | gm11_stackbull | IWM | 1.63 | 56 | 77 | 1.62 | {'stop_atr': 3, 'tp_atr': 6} |
| 112 | archon_orb | NKD=F | 1.63 | 69 | 96 | 1.39 | {'stop_atr': 3, 'tp_atr': 1} |
| 113 | gm16_sos | BTCUSDT | 1.63 | 54 | 71 | 1.46 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 114 | archon_orb | 6E | 1.62 | 50 | 90 | 3.58 | {'stop_atr': 3, 'tp_atr': 6} |
| 115 | gm22_amd | RTY | 1.61 | 49 | 51 | 1.81 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 116 | archon_orb | CHFJPY | 1.60 | 60 | 97 | 2.30 | {'stop_atr': 3, 'tp_atr': 1} |
| 117 | archon_orb | XLK | 1.60 | 52 | 88 | 1.54 | {} |
| 118 | rsi2 | ADAUSDT | 1.59 | 70 | 57 | 2.22 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 119 | archon_orb | EURJPY | 1.58 | 47 | 108 | 2.04 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 120 | archon_orb | BTCUSDT | 1.57 | 71 | 123 | 1.57 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 121 | gm24_poorhl | GOLD | 1.57 | 41 | 132 | 1.41 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 122 | archon_tsmom | CC=F | 1.56 | 49 | 92 | 1.91 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 123 | rsi2 | XLF | 1.56 | 67 | 69 | 2.92 | {} |
| 124 | archon_orb | SOLUSDT | 1.56 | 52 | 83 | 1.09 | {} |
| 125 | rsi2 | GLD | 1.55 | 61 | 61 | 1.75 | {} |
| 126 | archon_orb | CORN | 1.54 | 71 | 100 | 1.60 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 127 | gm15_upthrust | NZDUSD | 1.52 | 61 | 61 | 1.40 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 128 | archon_orb | ES | 1.52 | 51 | 87 | 1.52 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 129 | archon_tsmom | EURJPY | 1.51 | 53 | 45 | 1.37 | {'stop_atr': 3, 'tp_atr': 6} |
| 130 | gm16_sos | COPPER | 1.50 | 43 | 49 | 2.12 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 131 | archon_tsmom | USDZAR | 1.50 | 69 | 95 | 3.44 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 132 | gm16_sos | IWM | 1.50 | 75 | 55 | 2.22 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 133 | gm16_sos | OIL | 1.49 | 52 | 52 | 1.28 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 134 | gm16_sos | CL=F | 1.49 | 52 | 52 | 1.28 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 135 | gm18_liqsweep | EURNZD | 1.49 | 42 | 83 | 1.54 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 136 | archon_tsmom | CT=F | 1.49 | 46 | 118 | 1.33 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 137 | archon_orb | DOTUSDT | 1.49 | 70 | 83 | 1.46 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
| 138 | gm15_upthrust | DOTUSDT | 1.48 | 50 | 44 | 2.24 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 139 | gm24_poorhl | HE=F | 1.48 | 42 | 119 | 1.55 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 140 | archon_tsmom | QQQ | 1.48 | 75 | 56 | 1.49 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 141 | gm18_liqsweep | ZO=F | 1.48 | 46 | 106 | 2.33 | {'stop_atr': 1, 'tp_atr': 2, 'trail_atr': 1.5} |
| 142 | gm24_poorhl | YM | 1.48 | 40 | 114 | 1.34 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 143 | gm18_liqsweep | AUDUSD | 1.47 | 68 | 101 | 2.27 | {'stop_atr': 3, 'tp_atr': 1} |
| 144 | gm15_upthrust | 6J | 1.47 | 72 | 54 | 1.29 | {} |
| 145 | gm22_amd | CC=F | 1.47 | 50 | 44 | 1.53 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 146 | archon_orb | SPY | 1.47 | 44 | 88 | 1.49 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 147 | gm24_poorhl | EFA | 1.47 | 71 | 147 | 2.03 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 148 | archon_orb | BNBUSDT | 1.47 | 43 | 123 | 1.25 | {} |
| 149 | rsi2 | RTY | 1.46 | 68 | 56 | 2.05 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 150 | archon_orb | RB=F | 1.46 | 69 | 103 | 2.70 | {'stop_atr': 3, 'tp_atr': 1} |
| 151 | gm11_stackbull | EFA | 1.45 | 58 | 76 | 1.96 | {} |
| 152 | archon_orb | AVAXUSDT | 1.45 | 45 | 85 | 1.51 | {} |
| 153 | gm11_stackbull | LE=F | 1.44 | 53 | 90 | 1.21 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 154 | gm16_sos | GOLD | 1.43 | 45 | 66 | 2.63 | {'stop_atr': 2, 'tp_atr': 4, 'trail_atr': 3} |
| 155 | gm18_liqsweep | SLV | 1.43 | 72 | 116 | 1.39 | {'stop_atr': 4, 'tp_atr': 1.5} |
| 156 | gm24_poorhl | AVAXUSDT | 1.43 | 53 | 114 | 1.10 | {'stop_atr': 1.5, 'tp_atr': 3, 'trail_atr': 2} |
| 157 | gm11_stackbull | YM | 1.43 | 58 | 84 | 1.32 | {'stop_atr': 3, 'tp_atr': 6} |
| 158 | archon_orb | ETHUSDT | 1.42 | 65 | 122 | 1.22 | {'stop_atr': 3, 'tp_atr': 1} |
| 159 | gm24_poorhl | ES | 1.42 | 46 | 104 | 1.32 | {'stop_atr': 2, 'trail_atr': 2.5} |
| 160 | gm14_spring | RB=F | 1.41 | 73 | 55 | 1.31 | {'stop_atr': 2.5, 'tp_atr': 0.8} |
