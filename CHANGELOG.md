# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **A market that never stops:** the clock runs in real time while the game is open, one game minute at a
  time. At 1x an 8-hour session takes 2 real hours (15 s per game minute); 2x and 4x speed it up. After the
  close the market stays shut for a short pause, then the next session opens. Only the quarterly review stops
  the clock; risk warnings, order tickets and other windows no longer pause it. Pacing is configurable with
  `LIVE_SESSION_SECONDS`, `LIVE_SPEEDS` and `LIVE_CLOSED_SECONDS` (`LIVE_CLOCK=0` turns it off).
- **Real order types:** market, limit, stop-limit (SL) and stop-market (SL-M) orders, Day or Good-till-cancelled,
  with optional target and stop-loss legs that cancel each other (bracket). Orders can be modified or cancelled
  from the new Orders screen (open orders, order history, trade book, alerts, block deals).
- **Price alerts** on any stock or index.
- **Trading charts:** 1m, 5m, 15m, 1H and 1D timeframes; candles, OHLC bars, line or area; volume, SMA, EMA,
  Bollinger Bands, VWAP, RSI and MACD; a live OHLC legend. Charts update every game minute.
- **Large chart window** (expand button on every chart, or the chart icon in the watchlist) with market depth,
  the stock's working orders and alerts beside it.
- **Mark levels on the chart:** pick "Buy at", "Sell at" or "Alert" and click a price to open a pre-filled
  limit or stop order or set an alert; drag an order or alert line to move it.
- A simulated 5-level market depth on each stock.
- New layout: a watchlist with indices, hover Buy / Sell buttons, a top navigation bar with the market clock and
  speed, a floating order pad that does not cover the market, and a status bar with live P&L.
- Light theme (Settings → Theme).
- New `/api/game/tick`, `/api/game/speed`, `/api/orders` and `/api/alerts` routes, and a `minute_prices` table
  (1-minute bars, kept for 7 days).

### Changed

- Research runs in the background: the market keeps moving and the report arrives when the analysts finish.
- The day's change stays visible after the close and rolls over when the overnight session starts.
- The time-skip buttons moved into a menu next to the clock.
- Prices animate along each minute's real high and low instead of replaying a whole hour, and only the cells
  showing a price re-render, so the terminal is much lighter.

### Fixed

- Index charts (BHARAT 50, DALAL 30, BHARAT BANK and others) opened an empty page.
- Charts refetched their full history after every action and could lose the newest candle; RSI and MACD panes
  did not scroll with the price chart.
- Several panels clipped their contents on laptop-sized screens.

### Added (accounts)

- **Accounts:** sign in with Google or with an email and password. Careers and saves belong to your account
  and follow you across devices. Sign out from Settings.
- New `/api/auth` routes (`config`, `signup`, `login`, `google`, `me`) and an `accounts` table.
- New settings: `AUTH_SECRET` (recommended; falls back to a key derived from `DATABASE_URL`), `GOOGLE_CLIENT_ID`
  and `AUTH_TOKEN_DAYS`.
- **Forgot password:** a 6-digit code is emailed, and entering it sets a new password and signs you in.
- **Account settings** (Settings → Manage account): change your name, change your email (confirmed by a code
  sent to the new address), change or add a password (confirmed by a code sent to your current email), and
  sign out of other devices.
- **Restrictions:**
  - 5 wrong passwords lock sign-in for that email for 15 minutes.
  - Codes expire after 10 minutes and allow 5 tries.
  - Code emails are limited to one a minute and 5 an hour.
  - Passwords need 8+ characters with a letter and a number.
  - A password change or reset signs out every other device.
- New settings for email: `RESEND_API_KEY`, or `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`, plus
  `MAIL_FROM`.
- New `email_codes` and `rate_limits` tables. `accounts.session_version` is added automatically on startup.

### Changed

- Every game route now needs a signed-in user and only serves games that user owns. A guest career already
  in the browser moves to the first account created there.

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
