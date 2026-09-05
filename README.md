# FinSim — Investment Banker Mode

> **Your decisions move the money. The market decides your fate.**  
> A browser-based institutional investment strategy and career simulation game set within Indian financial markets.

---

## Project Status

### 🚧 WORK IN PROGRESS / ACTIVE DEVELOPMENT

> **Notice:** FinSim is in active, iterative development. The current codebase provides a functional Level 1 vertical slice representing an evolving, playable simulation prototype. Simulation mathematics, market events, UI systems, and game mechanics are under active refinement and subject to continuous architectural improvements. This project is **not** production-ready.

---

## Overview

**FinSim — Investment Banker Mode** is a web-based financial career strategy simulation game. Rather than operating as a passive analytics dashboard or a static mockup, FinSim immerses the player in the high-stakes role of **Head of Investments** at **Apex Capital**, a institutional investment firm.

Upon appointment, the player is entrusted with **₹100 Crore** (₹1,000,000,000 INR) in institutional capital and tasked with a strict quarterly mandate: navigate volatile market regimes, construct an equity portfolio, manage systemic and idiosyncratic risk, and hit a hurdle target of **₹112 Crore (+12.0% absolute return)** within **90 simulated business days**.

### Why a Simulation Game, Not a Financial Dashboard?
Unlike conventional financial dashboards that display historical market data or provide live portfolio telemetry, FinSim is designed as an interactive management game:
- **Authoritative Simulation Loop:** Time advances in simulated hourly or daily increments rather than waiting for real-world market hours.
- **Dynamic Market Drivers:** Stock prices follow a stochastic Geometric Brownian Motion (GBM) model driven by sector correlation, macro regimes, and event shocks.
- **Narrative Career Stakes:** Decisions directly impact player reputation, promotion XP, and board reviews by Apex Capital's executive committee.
- **Risk Consequences:** Breaching regulatory or internal risk limits triggers formal warnings that degrade reputation and can lead to termination at the quarterly review.

---

## Core Gameplay Concept

The game is structured around a focused management loop:

```
[Start Career at Apex Capital]
              ↓
  [Receive ₹100 Cr Mandate]
              ↓
   ┌──→ [Observe Market Tape & Indices]
   │          ↓
   │    [Analyze Equities & Fundamentals]
   │          ↓
   │    [Route BUY / SELL Orders]
   │          ↓
   │    [Advance Simulation Time (1h, Day, Close)]
   │          ↓
   │    [Process Price Movements & Event Shocks]
   │          ↓
   │    [Receive Intelligence & News Wire]
   │          ↓
   └─── [Monitor Drawdown & Risk Violations]
              ↓
 [Reach Day 90: Formal CEO Quarterly Review]
              ↓
 [Promoted / Target Met / Warning / Terminated]
```

### Intended Gameplay Flow
1. **Take the Desk:** Initialize a new career profile or resume a saved game state stored in PostgreSQL.
2. **Capital Allocation:** Deploy starting capital across 20 equities spanning 8 economic sectors.
3. **Market Observation:** Track simulated benchmarks (NIFTY 50, SENSEX, BANK NIFTY, INDIA VIX, USD/INR, GOLD, NASDAQ, S&P 500).
4. **Order Execution:** Place buy or sell orders with transaction fee calculations and cash validations.
5. **Time Progression:** Advance time by 1 hour, 2 hours, 4 hours, to market close, or to the next business day. Skip weekends when markets are closed.
6. **Information Processing:** Review breaking news wire items generated from underlying macroeconomic and corporate events.
7. **Risk Governance:** Maintain single-stock and sector concentration within bounds to prevent risk warnings.
8. **Quarterly Review:** Submit portfolio performance to the Apex Capital Board at Day 90 for evaluation based on return, drawdown, and reputation.

---

## Current Features

The features listed below are **fully implemented and functional in the repository today**:

### Backend Simulation & Services
- **Multi-Asset Market Engine:** Geometric Brownian Motion (GBM) price engine with drift, stochastic volatility, beta correlation, and sector co-movement factors.
- **Simulated Equity Universe:** 20 fictional Indian corporations with unique fundamentals (growth rate, profit margin, debt ratio, valuation multiple, beta, volatility, sentiment).
- **Simulated Benchmarks:** Continuous simulation of 8 market indicators: NIFTY 50, SENSEX, BANK NIFTY, INDIA VIX, USD/INR, GOLD, NASDAQ, and S&P 500.
- **Market Regimes:** Dynamic regime transitions (`BULL`, `STABLE`, `VOLATILE`, `BEAR`, `CRISIS`).
- **Deterministic Time Engine:** Stateful simulation calendar tracking game date, hour (09:00–17:00), day of week, career day, and market status (`PRE_MARKET`, `OPEN`, `CLOSED`, `WEEKEND`).
- **Flexible Time Controls:** Dedicated logic for advancing 1 hour, multi-hour spans, advancing to market close, advancing to next business day, and skipping weekends.
- **Portfolio Engine:** Authoritative calculation of cash, invested value, total portfolio value (in INR and ₹ Crore), daily P&L, cumulative P&L, unrealized/realized gains, and max drawdown.
- **Trade Execution Service:** Validated order desk supporting market BUY and SELL operations, cash sufficiency checks, position quantity verification, 0.1% brokerage fee modeling, and transaction history logging.
- **Event & News Engines:** Scheduled and stochastic corporate/macro events that trigger price impacts and generate narrative financial news wire items.
- **Risk Engine:** Portfolio monitoring for single-stock exposure, sector concentration, cash drag, and drawdown limits with risk warning generation.
- **Career & Evaluation Engine:** Player XP, clearance level, reputation tracking (0–100%), and formal quarterly review verdict generation (`PROMOTED`, `TARGET_ACHIEVED`, `WARNING`, `FAILED`, `TERMINATED`).
- **RESTful API:** FastAPI endpoints covering game lifecycle, time advancement, market quotes, order routing, portfolio queries, news feed, and career telemetry.

### Frontend Application (Terminal UI)
- **Bloomberg-Inspired Dark Terminal Interface:** Built with Tailwind CSS custom tokens, monospace typography (JetBrains Mono & Inter), and high-contrast financial palettes.
- **Apex Capital Lobby Screen:** Onboarding dossier, mandate brief, player name configuration, and saved games list with one-click resume.
- **Live Header Strip:** Persistent clearance level, role, XP progress bar, reputation score, market status badge, real-time clock, and core financial statistics.
- **Continuous Market Ticker:** Horizontal ticker tape streaming simulated benchmark index levels and percentage changes.
- **Simulation Control Bar:** Fast-forward time controls (+1H, +2H, +4H, To Close, Next Day, Skip Weekend) with loading state indicators.
- **Multi-View Workspace:**
  - **Dashboard:** Portfolio stat cards, top gainers/losers, active allocation snapshot, and recent news wire cards.
  - **Market Universe:** 20-stock screener table with symbol search, sector filtering, live pricing, beta, valuation multiples, and instant trade shortcuts.
  - **Portfolio Manager:** Detailed holdings breakdown with share quantity, cost basis, current market price, value in ₹ Cr, unrealized return, and liquidation controls.
  - **Order Desk (Trading):** Interactive order entry ticket with stock selector, BUY/SELL toggles, share quantity presets (25%, 50%, Max Affordable, Sell All), and fee estimations.
  - **Financial Intelligence Wire:** Categorized news broadcasts with priority tags (`BREAKING`, `HIGH`, `NORMAL`) and affected symbol tags.
  - **Career Dossier:** Detailed mandate tracking (₹100 Cr starting capital, ₹112 Cr hurdle target, days remaining), level progression, and formal review triggers.
  - **Risk & Analytics:** Volatility, max drawdown, cash ratio, and compliance warnings.
- **Interactive Modals:**
  - **Stock Detail Modal:** Deep-dive fundamental breakdown (growth, profitability, debt, sentiment, valuation) with embedded trade actions.
  - **Order Modal:** Focused position-sizing pop-up.
  - **Quarterly Evaluation Modal:** CEO review letter, return evaluation vs. hurdle, and reputation/XP rewards.

---

## Planned / Upcoming Features

The following features represent planned enhancements defined in the project architecture that are **not yet implemented**:

- 📋 **Interactive Candlestick Charting:** Embedding interactive historical OHLCV candlestick and volume charts via `lightweight-charts` into the stock detail modal.
- 📋 **Sector Breakdown Visualizations:** Visualizing sector concentration and drawdown curves using `recharts` graphs.
- 📋 **Machine Learning-Driven Game Director:** Adaptive difficulty engine that monitors player risk behavior and injects tailored narrative scenarios.
- 📋 **Derivative Financial Instruments:** Support for Futures & Options (F&O) contracts, index hedging, and commodity exposure.
- 📋 **Advanced Order Types:** Stop-loss orders, limit orders, and target profit triggers executed automatically across simulation ticks.
- 📋 **Multi-Quarter Career Progression:** Expanding beyond Q1 into subsequent career stages (Managing Director, Partner, Founder of Apex Capital spinoff).
- 📋 **Team Management Mechanics:** Hiring, directing, and mentoring junior analysts and sector specialists.
- 📋 **Historical State Backtesting & Leaderboards:** Comparing simulation performance runs against deterministic seeds.

---

## Technology Stack

The project relies strictly on the following technologies:

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | React | `^18.3.1` | Core UI component architecture |
| **Frontend Language** | TypeScript | `^5.4.5` | Type-safe client development |
| **Build Tool** | Vite | `^5.3.1` | Fast development server & production bundler |
| **Styling** | Tailwind CSS | `^3.4.4` | Terminal theme and utility styles |
| **Icons** | Lucide React | `^0.395.0` | UI icons |
| **HTTP Client** | Axios | `^1.7.2` | REST API communication |
| **Charting (Installed)**| Lightweight Charts | `^4.2.0` | TradingView candlestick charting (planned integration) |
| **Visualization (Installed)** | Recharts | `^2.12.7` | Analytics charts (planned integration) |
| **Backend Framework** | FastAPI | `0.111.0` | High-performance Python web API |
| **ASGI Server** | Uvicorn | `0.29.0` | Async server implementation |
| **Backend Language** | Python | `3.11-slim` | Simulation engine & backend runtime |
| **ORM** | SQLAlchemy | `2.0.30` | Database abstraction & relational models |
| **Database Migrations**| Alembic | `1.13.1` | Relational schema migration management |
| **Database Driver** | Psycopg2-binary | `2.9.9` | PostgreSQL client driver |
| **Data Validation** | Pydantic | `2.7.1` | Request/response schema validation |
| **Math / Simulation** | NumPy | `1.26.4` | Stochastic price generation & statistical math |
| **Database** | PostgreSQL | `15-alpine` | Persistent authoritative state storage |
| **Containerization** | Docker / Compose | Compose v2 | Multi-container orchestration |

---

## System Architecture

FinSim follows an authoritative backend architecture where all simulation logic, price changes, trade verifications, and career outcomes are computed on the server and persisted in PostgreSQL.

```
┌─────────────────────────────────────────────────────────┐
│              Browser / Client Interface                 │
│      React 18 + TypeScript + Vite + Tailwind CSS        │
│    (Lobby, Terminal Shell, Screener, Order Desk, News)  │
└────────────────────────────┬────────────────────────────┘
                             │ HTTP / JSON
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                      │
│            Routers (/api/game, /api/trade...)           │
│                           │                             │
│                  GameService Layer                      │
│                           │                             │
│          ┌────────────────┴───────────────┐             │
│          ▼                                ▼             │
│  Simulation Engines              Data Schemas (Pydantic)│
│  • TimeEngine                    • GameStateResponse    │
│  • MarketEngine                  • TradeResult          │
│  • EventEngine                   • StockCandlesResponse │
│  • NewsEngine                    • FinancialsInfo       │
│  • PortfolioEngine                                      │
│  • RiskEngine                                           │
│  • CareerEngine                                         │
│  • GameDirector                                         │
└────────────────────────────┬────────────────────────────┘
                             │ SQLAlchemy ORM
                             ▼
┌─────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                   │
│   games · stocks · holdings · transactions · stock_ticks │
│   market_ticks · news_items · game_events · telemetry   │
└─────────────────────────────────────────────────────────┘
```

### Layer Roles
1. **Frontend (Vite / React):** Client application that renders state, handles player inputs, routes navigation, and dispatches mutation requests to the backend. In development, Vite proxies `/api` requests directly to the backend container.
2. **Backend (FastAPI):** Exposes typed REST endpoints, enforces CORS policies, validates request payloads with Pydantic, and coordinates operations via `GameService`.
3. **Simulation Engines:** Pure Python modules managing mathematical models for asset pricing (GBM), chronological calendar advancement, event injection, risk scoring, and career milestones.
4. **Authoritative Persistence (PostgreSQL):** All financial balances, active positions, price tick histories, and transactions are stored in relational tables to guarantee deterministic resume capability across browser refreshes.

---

## Project File Structure

Below is the **actual repository file structure**:

```
FinSim/
├── backend/
│   ├── alembic/
│   │   └── env.py                    # Alembic migration environment configuration
│   ├── app/
│   │   ├── api/                      # FastAPI endpoint routers
│   │   │   ├── __init__.py
│   │   │   ├── career.py             # Career progression & review endpoints
│   │   │   ├── game.py               # Game initialization & time controls
│   │   │   ├── market.py             # Market snapshots & candlestick data
│   │   │   ├── news.py               # Financial intelligence & news feed
│   │   │   ├── performance.py        # Analytics & telemetry endpoints
│   │   │   ├── portfolio.py          # Portfolio holdings & valuation endpoints
│   │   │   └── trade.py              # BUY and SELL order execution
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   └── db_models.py          # Tables: games, stocks, holdings, txns...
│   │   ├── schemas/                  # Pydantic schemas for request/response validation
│   │   │   ├── __init__.py
│   │   │   └── game_schemas.py       # GameState, TradeResult, FinancialsInfo...
│   │   ├── services/                 # Business logic & orchestrators
│   │   │   ├── __init__.py
│   │   │   └── game_service.py       # Central orchestrator integrating all engines
│   │   ├── simulation/               # Core mathematical & simulation engines
│   │   │   ├── __init__.py
│   │   │   ├── career_engine.py      # XP, reputation, and board review logic
│   │   │   ├── constants.py          # Stock universe, indices, starting capital constants
│   │   │   ├── event_engine.py       # Macro and corporate event scheduling
│   │   │   ├── game_director.py      # Simulation difficulty & event weighting
│   │   │   ├── market_engine.py      # Geometric Brownian Motion price simulation
│   │   │   ├── news_engine.py        # Narrative news generation from events
│   │   │   ├── portfolio_engine.py   # Portfolio valuation, P&L, drawdown math
│   │   │   ├── risk_engine.py        # Concentration limits & risk warnings
│   │   │   └── time_engine.py        # Trading clock, calendar, and market hours
│   │   ├── __init__.py
│   │   ├── config.py                 # Pydantic environment configuration
│   │   ├── database.py               # Database engine & sessionmaker setup
│   │   └── main.py                   # FastAPI application entry point & CORS
│   ├── alembic.ini                   # Alembic configuration file
│   ├── Dockerfile                    # Python 3.11 backend container definition
│   └── requirements.txt              # Python package dependencies
├── frontend/
│   ├── src/
│   │   ├── hooks/
│   │   │   └── useGameState.ts       # React state hook for polling & time mutations
│   │   ├── services/
│   │   │   └── api.ts                # Axios client for all backend endpoints
│   │   ├── types/
│   │   │   └── game.ts               # TypeScript interfaces mirroring backend schemas
│   │   ├── App.tsx                   # Main FinSim application component & views
│   │   ├── index.css                 # Terminal design system, typography, and utility classes
│   │   └── main.tsx                  # React 18 application entry point mounting to #root
│   ├── Dockerfile                    # Node 20 frontend container definition
│   ├── index.html                    # Single-page application HTML template
│   ├── package.json                  # Node dependencies and build scripts
│   ├── postcss.config.js             # PostCSS plugins configuration
│   ├── tailwind.config.js            # Tailwind CSS theme and palette configuration
│   ├── tsconfig.json                 # TypeScript compiler options
│   ├── tsconfig.node.json            # Node-specific TypeScript config
│   └── vite.config.ts                # Vite configuration with /api backend proxy
├── .gitignore                        # Git exclusion rules
├── docker-compose.yml                # Docker Compose multi-service definition
├── Investment_Banker_Mode_Master_Prompt.md # Master architectural build specification
└── README.md                         # Project documentation
```

---

## Backend Architecture

The backend is built around FastAPI and a modular simulation core:

1. **`app/main.py`:** Initializes the FastAPI app, configures CORS for local development, creates database tables via `Base.metadata.create_all`, and registers all modular routers under `/api/*`.
2. **`app/api/`:** Separate routers handle distinct domains:
   - `game.py`: Lifecycle management (`/new`, `/state/{id}`, `/advance-hour`, `/advance-hours`, `/advance-to-close`, `/advance-next-business-day`, `/skip-weekend`, `/quarterly-review`, `/list`).
   - `trade.py`: Position order routing (`/buy`, `/sell`).
   - `market.py`: Stock screener data and OHLCV candle histories (`/{game_id}`, `/{game_id}/{symbol}/candles`).
   - `portfolio.py`: Current holdings and summary statistics (`/{game_id}`).
   - `news.py`: Intelligence wire events (`/{game_id}`).
   - `career.py`: Clearance level, XP, and leave balances (`/{game_id}`).
   - `performance.py`: Risk scores and historical transaction logs (`/{game_id}`).
3. **`app/services/game_service.py`:** The authoritative coordinator. Every mutation (e.g., advancing time or executing a trade) loads the authoritative `Game` record, invokes the relevant simulation engine, recalculates portfolio analytics, persists updates to PostgreSQL, and returns a unified `GameStateResponse`.
4. **`app/simulation/`:** Independent simulation modules:
   - `market_engine.py`: Computes price drift based on sector trends, regime shifts, and news shocks using deterministic seeded random generators.
   - `time_engine.py`: Advances simulation time respecting Indian market hours (09:15 open, 15:30 close) and weekday schedules.
   - `portfolio_engine.py`: Tracks cash balances, cost basis, unrealized/realized gains, and portfolio drawdown.
   - `risk_engine.py`: Scans active positions against risk parameters (e.g., maximum 25% single-stock exposure, 40% sector cap).

---

## Frontend Architecture

The frontend is a single-page React 18 application developed with TypeScript and Vite:

- **Entry Point (`src/main.tsx`):** Bootstraps the application, imports the global design system stylesheet (`index.css`), and mounts `<App />` into the DOM root.
- **Application Shell (`src/App.tsx`):** Coordinates client-side routing between the onboarding lobby and the active trading terminal. Manages modals (`StockDetailModal`, `TradeModal`, `QuarterlyReviewModal`) and delegates tab views.
- **State Management (`src/hooks/useGameState.ts`):** Custom React hook managing active game state, time advancement triggers, refresh lifecycles, and asynchronous error boundaries.
- **API Client (`src/services/api.ts`):** Centralized, typed Axios client interacting with all backend endpoints via the Vite dev proxy (`/api` → `http://backend:8000`).
- **Type Definitions (`src/types/game.ts`):** TypeScript interfaces mirroring backend Pydantic schemas (`GameState`, `TimeInfo`, `StockInfo`, `HoldingInfo`, `RiskInfo`, `TradeResult`, `QuarterlyReview`).
- **Design System (`src/index.css`):** Comprehensive Bloomberg/terminal-inspired CSS defining dark color variables (`#080b10` background, `#0d1117` panels, `#00d4ff` accents, gain/loss indicators), custom scrollbars, data table layouts, and badge utilities.

---

## Database

Persistence is handled by PostgreSQL 15 via SQLAlchemy ORM. The relational schema includes the following tables:

| Table | Purpose |
| :--- | :--- |
| **`games`** | Primary game record: player name, seed, current simulation date/hour, cash, peak value, career level, XP, reputation, market regime. |
| **`stocks`** | Fictional company definitions per game: symbol, sector, prices, beta, volatility, fundamentals, and dynamic sentiment. |
| **`holdings`** | Active equity positions: quantity held, average cost basis, and total capital deployed. |
| **`transactions`** | Comprehensive audit log of every BUY/SELL execution: share count, price, fees, and realized profit/loss. |
| **`stock_ticks`** | Historical hourly OHLCV candle records for all 20 stocks per game tick. |
| **`market_ticks`** | Benchmark index snapshots (NIFTY, SENSEX, VIX, etc.) per simulation tick. |
| **`news_items`** | Generated financial news wire records linked to simulation days and corporate tickers. |
| **`game_events`** | Scheduled macroeconomic and corporate events with severity, duration, and price impact parameters. |
| **`telemetry`** | Periodic performance snapshots recording return, risk score, position count, and trade volume. |

---

## Running the Project

The entire stack is containerized with Docker Compose. Docker Desktop must be installed and running.

### 1. Clone the Repository
```bash
git clone <repository-url>
cd FinSim
```

### 2. Launch with Docker Compose
```bash
docker compose up --build
```

### 3. Access Services
Once all containers have initialized:
- **Frontend Web Terminal:** [http://localhost:5173](http://localhost:5173)
- **FastAPI Backend:** [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## Docker Setup

The `docker-compose.yml` orchestrates three isolated services communicating over an internal Docker network:

```
┌────────────────────────────────────────────────────────┐
│                   Docker Network                       │
│                                                        │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────┐  │
│  │ finsim_frontend│ │ finsim_backend │ │ finsim_db  │  │
│  │ (Node 20/Vite) │ │ (Python 3.11)  │ │ (Postgres) │  │
│  │   Port: 5173   │ │   Port: 8000   │ │ Port: 5432 │  │
│  └───────┬────────┘ └───────▲────────┘ └─────▲──────┘  │
│          │ /api proxy       │                │         │
│          └──────────────────┴────────────────┘         │
└────────────────────────────────────────────────────────┘
```

- **`db` (`finsim_db`):** `postgres:15-alpine` container storing authoritative game data in a persistent volume (`postgres_data`). Port `5432` is exposed for inspection.
- **`backend` (`finsim_backend`):** Python 3.11 container running FastAPI under Uvicorn with hot-reload enabled. Depends on the database health check. Port `8000` is exposed.
- **`frontend` (`finsim_frontend`):** Node 20 container running the Vite development server with hot-module replacement (HMR). Port `5173` is exposed.

---

## Development Workflow

### Making Code Changes
- **Frontend Changes:** Edits inside `frontend/src/` automatically trigger Vite HMR in the browser without container restarts.
- **Backend Changes:** Edits inside `backend/app/` automatically trigger Uvicorn server reloads.

### Rebuilding Containers
If you add dependencies to `backend/requirements.txt` or `frontend/package.json`:
```bash
docker compose up --build
```

### Inspecting Logs
```bash
# View combined logs
docker compose logs -f

# View backend logs only
docker compose logs -f backend

# View frontend logs only
docker compose logs -f frontend
```

### Validating Frontend Production Build
To run the TypeScript compiler and Vite production build inside the running container:
```bash
docker exec finsim_frontend npm run build
```

### Stopping the Application
```bash
# Stop containers without losing database data
docker compose down

# Stop containers and wipe PostgreSQL database volume
docker compose down -v
```

---

## Game Design & Vision

The long-term vision for **FinSim** is to build a premier browser-based simulation that blends institutional portfolio management with narrative career progression.

Key design principles guiding future development:
- **Depth Over Surface:** Realistic mechanics where macro regimes, central bank policy, corporate earnings, and sector contagion interact dynamically rather than through simple random number generators.
- **Player Psychology & Risk:** Modeling the trade-off between aggressive capital growth and regulatory survival. High returns mean nothing if max drawdown breaches trigger board termination.
- **Cinematic Financial Experience:** A sleek, focused terminal interface that makes managing simulated capital feel authentic, urgent, and rewarding.

---

## Roadmap

| Milestone | Status | Details |
| :--- | :---: | :--- |
| **Level 1 Architecture & Scaffolding** | ✅ Implemented | Docker Compose environment, FastAPI structure, PostgreSQL models |
| **Core Simulation Engines** | ✅ Implemented | Time advancement, GBM price model, portfolio P&L, risk warnings |
| **Trade Execution Desk** | ✅ Implemented | Buy/Sell orders, fee deduction, cash and position validations |
| **React Terminal Interface** | ✅ Implemented | Lobby onboarding, TopBar, ticker tape, screener, portfolio view |
| **Quarterly Review Evaluation** | ✅ Implemented | Formal evaluation logic, CEO verdict, XP and reputation rewards |
| **Interactive Candlestick Charts** | 🚧 In Progress | Integrating `lightweight-charts` for multi-day OHLCV visualization |
| **Sector Allocation & Risk Visuals** | 🚧 In Progress | Recharts graphs for portfolio concentration and drawdown history |
| **Adaptive Game Director** | 📋 Planned | Player behavior analysis adjusting scenario probabilities |
| **Derivative Instruments (F&O)** | 📋 Planned | Index futures, options hedging, and volatility trading |
| **Multi-Quarter Career Progression** | 📋 Planned | Levels 2–5 with expanding capital mandates and team management |

---

## Future Direction

Planned architectural and gameplay expansions include:
- **Richer Market Simulation:** Advanced stochastic volatility models (Heston model) and multi-factor sector covariance matrices.
- **Deep Event Trees:** Branching corporate narrative events (mergers, regulatory investigations, hostile takeovers) where player choices alter market outcomes.
- **Specialized Financial Products:** Corporate bonds, sovereign debt instruments, and currency forward contracts.
- **Expanded Scenarios:** Historical crisis sandboxes (e.g., 2008 liquidity crunch, 2020 pandemic crash) allowing players to test strategies under extreme market stress.

---

## Disclaimer

> **Important:** FinSim is a financial strategy simulation game created strictly for educational, entertainment, and simulation purposes. All companies, market indicators, stock prices, news items, and financial events depicted in the simulation are fictional or simulated. FinSim does **not** provide investment advice, financial planning, or securities recommendations of any kind.

---

## License

License: Not yet specified.
