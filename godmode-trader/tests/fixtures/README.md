# Test fixtures (synthetic)

Every file here is made by `make_fixtures.py` from fixed seeds:

    python3 tests/fixtures/make_fixtures.py

The bars are seeded random walks in the exact shape of Yahoo's v8 chart JSON,
on each market's real hours (the FX week, CME Globex with its daily break,
NYSE, crypto 24/7), across both 2026 DST changes. On Monday 2026-11-16 each
chart carries a hand-made setup with known numbers (EURUSD and GBPUSD London
breakouts long and short, a COMEX gold breakdown, a US cash S&P breakout, a
UTC-day bitcoin breakdown), so the tests can check them to the tick.

The calendar (Forex Factory export shape), COT (CFTC public reporting rows)
and news (Yahoo RSS) files are synthetic too. None of it is a claim about what
any market really did, or about any real event or headline.

The live tools were not run against the real endpoints from the environment
these fixtures were built in: check the first live run of each tool.
