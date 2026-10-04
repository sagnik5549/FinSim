# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-04

First public release, playable at https://fin-sim-investments.vercel.app.

### Added

- **The game:** Level 1 "Head of Investments" career. You start with ₹100 Cr, a +12% quarterly target, a
  10% drawdown limit and 90 days, and a board review decides whether you are promoted, warned or fired.
- **Simulation engine:** an hour-by-hour market (twelve 5-minute ticks per hour) driven by a hidden market
  regime, sector and macro factors, fair-value mean reversion, momentum and fund flows.
- **The market:** 20 fictional listed companies and 8 simulated tickers.
- **Events:** company, macro and market events, with branching multi-day story chains plus a scheduled
  calendar of CPI, GDP, rate decisions and quarterly results.
- **Trading:** fees, transaction tax and liquidity-based market impact. Time-limited block deals, some
  from sellers who know bad news is coming.
- **Research desk:** quick looks and deep dives with noisy fair-value estimates, earnings calls and
  red-flag scans, plus written theses that are scored at review.
- **Risk and compliance:** 15% single-stock, 40% sector and 10% drawdown limits with blocking warnings
  (reduce, request an exception, or ignore), compliance strikes, and a 20% termination line.
- **Career:** a 7-level ladder, reputation, XP, a warning ladder, achievements and a five-factor
  quarterly review.
- **Your team:** nine characters whose skills affect accuracy, execution and exceptions, with trust and
  stress that react to your choices.
- **Time:** weekends and paid leave (60 days a year), and a live mode at 1×, 2× and 4× speed.
- **Saving:** autosave after every action and named save slots.
- **Terminal UI:** React and TypeScript with live candlestick charts and indicators, nine screens, and
  illustrated characters.
- **Adaptive director:** a player-behaviour classifier and a director with fixed bounds. The live site
  uses the rule-based fallback.
- **Field manual:** a 21-page illustrated player's guide, `docs/IB-Mode-How-To-Play.pdf`.
- **Deployment:** the frontend is hosted on Vercel and the backend runs as a serverless FastAPI function
  on Neon Postgres. Each action locks its game row so serverless instances can't overwrite each other.
- **Tests:** 40 backend tests (pytest) and 10 frontend tests (Vitest).

[1.0.0]: https://github.com/sagnik5549/FinSim/releases/tag/v1.0.0
