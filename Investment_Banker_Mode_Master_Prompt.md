# INVESTMENT BANKER MODE --- MASTER BUILD SPECIFICATION

## Build Directive

You are an expert full-stack game developer, financial-simulation
engineer, game-systems designer, UI/UX designer, backend engineer, and
ML engineer.

Your job is to **actually build** the game described in this
specification.

Do not merely describe an architecture. Do not create a static mockup.
Do not create fake buttons. Do not create disconnected frontend screens.
Do not create a beautiful frontend with placeholder backend logic.

Build a working playable vertical slice first, run it, test it, identify
problems, and fix them before expanding.

The final product is a **financial career-management simulation game**,
not a real-world investment advisor and not a real-time stock prediction
application.

All companies, prices, market movements, events, news, employees, and
outcomes inside the game are simulated.

------------------------------------------------------------------------

# 1. GAME CONCEPT

## Title

**INVESTMENT BANKER MODE**

## Tagline

**Your decisions move the money. The market decides your fate.**

## Genre

Financial strategy / career management / market simulation / management
game.

## Core inspiration

Combine the career progression and management depth of:

-   FIFA Career Mode
-   Football Manager
-   Bloomberg Terminal
-   TradingView
-   Financial strategy simulators
-   Management simulation games

Do not copy copyrighted UI, assets, branding, or characters.

The player becomes an investment professional and manages capital for an
investment company.

The fantasy is:

> "I have been hired by an investment company. I have been given
> capital. I have a target. I have a boss. The market is moving. I need
> to make decisions. My decisions have consequences. I can be promoted.
> I can fail. Eventually I can run the entire investment organization."

------------------------------------------------------------------------

# 2. MOST IMPORTANT DESIGN PRINCIPLE

The player should feel like they are **working inside an investment
bank**, not using a stock dashboard.

The game should create pressure through:

-   Return
-   Risk
-   Time
-   Uncertainty
-   Reputation
-   Career progression
-   Client expectations
-   Employee performance

There must not be one mathematically obvious strategy.

A high-risk strategy can produce exceptional returns but threaten the
player's career.

A conservative strategy can protect capital but fail to achieve
aggressive targets.

The player must constantly balance:

**RETURN vs RISK vs TIME vs UNCERTAINTY**

------------------------------------------------------------------------

# 3. VISUAL DIRECTION

Use the supplied/generated visual reference as the primary direction for
the game's main terminal.

Target aesthetic:

**Premium dark financial terminal**

Visual inspiration:

**Bloomberg × TradingView × FIFA Career Mode × modern strategy game**

The main screen should look like a professional institutional investment
terminal.

## No human photographs

Do not use:

-   Human photographs
-   Celebrity photographs
-   Stock photography
-   Realistic corporate headshots

Characters should use:

-   Illustrated cutouts
-   Professional vector-style avatars
-   Silhouettes
-   Minimalist character illustrations
-   Role icons

Characters appear primarily during:

-   CEO conversations
-   Meetings
-   Warnings
-   Career reviews
-   Employee interactions
-   Major story events

------------------------------------------------------------------------

# 4. VISUAL QUALITY BAR

The interface should feel like a polished commercial game prototype.

Use:

-   Near-black / dark navy background
-   Subtle panel separation
-   Excellent typography
-   High information density
-   Crisp financial charts
-   Subtle borders
-   Green for gains
-   Red for losses
-   Yellow/orange for warnings
-   Blue/purple for neutral information
-   Restrained glow
-   Professional animations
-   Smooth transitions
-   Clear hierarchy

Avoid:

-   Generic Bootstrap UI
-   Generic SaaS dashboards
-   Excessive rounded cards
-   Excessive glassmorphism
-   Giant empty spaces
-   Childish graphics
-   Excessive neon
-   Random gradients
-   Stock photos
-   Placeholder-looking components
-   Unnecessary animations

The UI must communicate a lot of information without becoming confusing.

------------------------------------------------------------------------

# 5. TECHNOLOGY STACK

Use this architecture unless there is a compelling technical reason to
improve it.

## Frontend

-   React
-   TypeScript
-   Vite
-   Tailwind CSS

## Backend

-   Python
-   FastAPI

## Database

-   PostgreSQL

## Simulation

-   Python
-   NumPy
-   Pandas

## ML

-   scikit-learn
-   XGBoost
-   SHAP

## Testing

-   Pytest
-   Vitest or equivalent frontend testing

## Containerization

-   Docker
-   Docker Compose

## Charts

Use a high-quality charting library suitable for:

-   Candlestick charts
-   Volume
-   Technical indicators
-   Portfolio curves
-   Performance charts

Do not use Streamlit as the primary game frontend.

This must be a real web application.

------------------------------------------------------------------------

# 6. HIGH-LEVEL ARCHITECTURE

Use a clean separation:

``` text
                         PLAYER
                           ↓
                      REACT UI
                           ↓
                        FASTAPI
                           ↓
                      GAME ENGINE
                           ↓
       ┌───────────────────┼───────────────────┐
       ↓                   ↓                   ↓
 MARKET ENGINE        EVENT ENGINE       CAREER ENGINE
       ↓                   ↓                   ↓
 RISK ENGINE         ECONOMY ENGINE      PLAYER ENGINE
       └───────────────────┼───────────────────┘
                           ↓
                       GAME STATE
                           ↓
                    TELEMETRY / DATA
                           ↓
                  ML ADAPTIVE DIRECTOR
```

The backend is authoritative.

The frontend must NOT be authoritative for:

-   Cash
-   Stock prices
-   Holdings
-   Portfolio value
-   Trade execution
-   Career progression
-   Event outcomes
-   Game time

------------------------------------------------------------------------

# 7. GAME START / ONBOARDING

The game begins with a short professional onboarding sequence.

Display:

``` text
APEX CAPITAL

Investment Management Division
```

Then:

``` text
Congratulations.

You have been appointed
Head of Investments.
```

Show an illustrated CEO character.

CEO dialogue:

> "Welcome to Apex Capital."

> "We're giving you control of our investment portfolio."

> "Your first assignment is simple."

> "Beat the quarterly target."

Then display:

``` text
ROLE
Head of Investments

STARTING CAPITAL
₹100 Cr

QUARTERLY TARGET
₹112 Cr

MAXIMUM DRAWDOWN
10%

RISK PROFILE
MEDIUM

TIME
90 DAYS
```

Button:

**START CAREER**

The transition into the main terminal should feel polished and
cinematic.

------------------------------------------------------------------------

# 8. MAIN GAME SCREEN

The primary gameplay screen should occupy almost the entire browser.

Do not create a traditional website-style landing page.

The main screen should be a full-screen financial terminal.

Recommended composition:

``` text
┌─────────────────────────────────────────────────────────────┐
│ CAREER / XP / REPUTATION / TIME / MARKET STATUS             │
├────────────┬────────────────────────────────────────────────┤
│            │ MARKET TICKERS                                 │
│            ├────────────────────────────────────────────────┤
│ NAVIGATION │                                                │
│            │              PRIMARY MARKET                     │
│ Dashboard  │              CANDLESTICK CHART                 │
│ Markets    │                                                │
│ Portfolio  │                                                │
│ Research   ├────────────────────────┬───────────────────────┤
│ Trading    │ PORTFOLIO              │ NEWS & EVENTS         │
│ News       │                         │                       │
│ Team       ├────────────────────────┤                       │
│ Career     │ HOLDINGS               │ MESSAGES              │
│ Performance│                        │                       │
│            ├────────────────────────┴───────────────────────┤
│            │ ACTIONS / TRADE / RESEARCH / TIME CONTROLS     │
└────────────┴────────────────────────────────────────────────┘
```

------------------------------------------------------------------------

# 9. TOP CAREER BAR

Display:

``` text
IB MODE

LEVEL 1

HEAD OF INVESTMENTS

XP
450 / 1000

REPUTATION
72

MONDAY
10:00

DAY
28 / 90

Q1, YEAR 1

MARKET OPEN
```

Also include:

-   Notifications
-   Settings
-   Time controls

The game clock must always be visible.

------------------------------------------------------------------------

# 10. MARKET TICKER

Create simulated indices:

-   NIFTY 50
-   SENSEX
-   BANK NIFTY
-   INDIA VIX
-   USD/INR
-   GOLD
-   NASDAQ
-   S&P 500

Each ticker shows:

-   Current value
-   Percentage movement
-   Mini sparkline

Example:

``` text
NIFTY 50
24,512.35
+0.85%
```

These are simulated game values.

Do not claim they are live real-world prices.

------------------------------------------------------------------------

# 11. MARKET ENGINE

Build a real market simulation engine.

Do NOT hardcode a sequence such as:

``` text
Day 1 +1%
Day 2 -2%
Day 3 +3%
```

The market must be generated dynamically from game state.

Every simulated stock should have:

``` text
symbol
name
sector
price
previous_price
daily_return
volume
volatility
momentum
sentiment
growth
profitability
debt
valuation
beta
market_sensitivity
institutional_pressure
event_sensitivity
```

Price movement should depend on:

-   Market regime
-   Sector movement
-   Company fundamentals
-   Sentiment
-   Volatility
-   Active events
-   Company-specific shocks
-   Macroeconomic conditions
-   Stochastic noise

The simulation should be believable rather than an attempt to perfectly
reproduce real financial markets.

------------------------------------------------------------------------

# 12. MARKET REGIMES

Implement:

-   BULL
-   STABLE
-   VOLATILE
-   BEAR
-   CRISIS

Each regime changes:

-   Return distribution
-   Volatility
-   Correlations
-   Sector behavior
-   Event probability
-   Market sentiment

The player should not simply see:

``` text
CURRENT REGIME = CRISIS
```

Instead, they should infer the regime through:

-   Charts
-   Price action
-   News
-   Volatility
-   Sector behavior
-   Research

------------------------------------------------------------------------

# 13. STOCK UNIVERSE

Create at least 20 fictional companies.

Do not depend on external financial data for the core game.

Example companies:

-   Apex Technologies
-   Vertex Systems
-   Nova Motors
-   Zenith Bank
-   Orion Finance
-   Titan Energy
-   BlueWave Pharma
-   Quantum Retail
-   Indus Infrastructure
-   Evergreen FMCG
-   Stellar Telecom
-   Helix Healthcare
-   Prime Logistics
-   Archer Defence
-   Nexus Software
-   Solaris Energy
-   Crescent Auto
-   Meridian Capital
-   Atlas Industries
-   Pioneer Consumer

Sectors:

-   Technology
-   Banking
-   Finance
-   Energy
-   Healthcare
-   Automobile
-   FMCG
-   Telecom
-   Infrastructure
-   Defence
-   Logistics

Each company must have different:

-   Growth
-   Risk
-   Volatility
-   Valuation
-   Fundamentals
-   Sector sensitivity
-   Event sensitivity

------------------------------------------------------------------------

# 14. TRADING SYSTEM

Player actions:

-   BUY
-   SELL
-   HOLD

## Buy flow

Select stock.

Enter quantity.

Show:

-   Price
-   Quantity
-   Transaction value
-   Transaction cost
-   Cash after transaction
-   Portfolio impact

Require confirmation.

Example:

``` text
BUY

Apex Technologies

Price:
₹2,450

Quantity:
1,000

Value:
₹24.5 Lakh

Estimated Fee:
₹4,900

[CONFIRM BUY]
```

## Sell flow

Show:

-   Current price
-   Quantity
-   Estimated proceeds
-   Transaction cost
-   Realized P&L

Validation:

-   Cannot buy without sufficient cash.
-   Cannot sell more shares than owned.
-   Quantity must be positive.
-   Invalid symbols must be rejected.

After execution:

``` text
TRADE EXECUTED
```

Update:

-   Cash
-   Holdings
-   Portfolio
-   P&L
-   Risk
-   Transaction history
-   Telemetry

------------------------------------------------------------------------

# 15. PORTFOLIO ENGINE

Track:

-   Starting capital
-   Cash
-   Invested capital
-   Current value
-   Profit/loss
-   Return %
-   Daily P&L
-   Realized P&L
-   Unrealized P&L
-   Maximum drawdown
-   Portfolio volatility
-   Risk score
-   Sector exposure
-   Position concentration

Example:

``` text
STARTING CAPITAL
₹100 Cr

CURRENT VALUE
₹108.75 Cr

PROFIT
+₹8.75 Cr

RETURN
+8.75%

TARGET
₹112 Cr

TARGET PROGRESS
77%
```

Create professional visualizations.

------------------------------------------------------------------------

# 16. RISK ENGINE

Risk is a first-class game mechanic.

Track:

-   Single-stock concentration
-   Sector concentration
-   Cash ratio
-   Drawdown
-   Volatility
-   Leverage
-   Correlation
-   Portfolio risk

Example:

``` text
RISK WARNING

Technology exposure:

47%

Firm policy:

40%
```

Options:

-   REDUCE EXPOSURE
-   REQUEST EXCEPTION
-   IGNORE

Risk violations must have consequences.

Do not make risk cosmetic.

------------------------------------------------------------------------

# 17. NEWS ENGINE

Create a believable financial news system.

Examples:

``` text
Nova Motors announces major expansion.

Zenith Bank reports earnings above expectations.

Central bank unexpectedly raises interest rates.

Energy prices spike following supply disruption.

Technology sector faces new regulation.

Global markets enter risk-off mode.
```

News must be generated from actual game events.

Do not create unrelated random text.

Important news must connect to actual game-state changes.

------------------------------------------------------------------------

# 18. EVENT ENGINE

Implement event types.

## Company events

-   Earnings beat
-   Earnings miss
-   CEO resignation
-   Product launch
-   Product failure
-   Major contract
-   Acquisition
-   Failed acquisition
-   Regulatory investigation
-   Factory shutdown
-   Management scandal
-   Breakthrough technology

## Macro events

-   Rate hike
-   Rate cut
-   Inflation surprise
-   GDP surprise
-   Currency shock
-   Commodity shock
-   Recession
-   Recovery

## Market events

-   Sector rally
-   Market selloff
-   Volatility spike
-   Institutional buying
-   Institutional selling
-   Liquidity crisis

Each event contains:

``` text
id
type
severity
affected_companies
affected_sectors
probability
market_impact
duration
narrative
follow_up_events
```

------------------------------------------------------------------------

# 19. EVENT CHAINS

Events can create multi-day storylines.

Example:

``` text
DAY 20

Company announces aggressive acquisition.

↓

DAY 22

Analysts question valuation.

↓

DAY 25

Debt concerns emerge.

↓

DAY 30

Credit rating downgraded.

↓

Stock falls.
```

Player decisions earlier in the chain should matter.

Create branching scenarios.

------------------------------------------------------------------------

# 20. CHARACTER SYSTEM

Characters are not playable humans.

They are advisors, managers and executives.

Represent them with stylish illustrated cutouts or professional avatars.

Characters:

-   CEO
-   CFO
-   Risk Manager
-   Research Director
-   Senior Analyst
-   Trader
-   Economist
-   Compliance Officer
-   HR Manager

Each has:

``` text
name
role
skills
trust
loyalty
stress
performance
personality
```

Use dialogue panels.

Example:

**CEO**

> "We're behind target."

> "I want another ₹3 Cr before quarter end."

**Risk Manager**

> "That would increase portfolio risk significantly."

**Research Director**

> "I've identified an opportunity worth reviewing."

------------------------------------------------------------------------

# 21. EMPLOYEE MANAGEMENT

At higher career levels allow recruitment.

Employee attributes:

-   Research
-   Quant
-   Risk awareness
-   Market knowledge
-   Negotiation
-   Experience
-   Loyalty
-   Salary

Employees must have meaningful gameplay effects.

Examples:

A high-research analyst improves research quality.

A strong risk manager reduces risk penalties.

A high-quant analyst improves quantitative scenario analysis.

------------------------------------------------------------------------

# 22. CAREER MODE

Career progression:

``` text
LEVEL 1
Investment Associate

LEVEL 2
Investment Manager

LEVEL 3
Senior Investment Manager

LEVEL 4
Portfolio Director

LEVEL 5
Head of Investments

LEVEL 6
Managing Director

LEVEL 7
Investment Firm CEO
```

## Level 1

Unlock:

-   Stocks
-   Buy
-   Sell
-   Portfolio

## Level 2

Unlock:

-   Sector allocation
-   Research team

## Level 3

Unlock:

-   Bonds
-   IPOs
-   Hedging
-   Advanced risk

## Level 4

Unlock:

-   M&A
-   Multiple portfolios
-   Institutional clients

## Level 5

Unlock:

-   Investment teams
-   Large capital
-   Board decisions

## Level 6

Unlock:

-   Multiple divisions
-   Competitor firms
-   Large deals

## Level 7

Run the entire investment organization.

Do not implement every level in the first MVP.

Build the architecture so they can be added later.

------------------------------------------------------------------------

# 23. REPUTATION SYSTEM

Track reputation from 0--100.

Reputation changes based on:

-   Returns
-   Risk management
-   Client satisfaction
-   Compliance
-   Employee management
-   Major decisions
-   Target achievement

Reputation unlocks:

-   Better jobs
-   Larger capital
-   Better employees
-   Bigger opportunities

------------------------------------------------------------------------

# 24. CLIENT SYSTEM

Later levels introduce clients.

Each client has:

-   Capital
-   Risk tolerance
-   Target return
-   Investment horizon
-   Sector restrictions
-   Investment preferences

Example:

``` text
APEX PENSION FUND

Capital:
₹500 Cr

Risk:
LOW

Target:
8%

Horizon:
5 YEARS
```

A high-risk strategy should not automatically satisfy a low-risk client.

------------------------------------------------------------------------

# 25. TIME SYSTEM --- CORE GAMEPLAY MECHANIC

TIME IS NOT JUST A CLOCK.

Time is one of the central strategic resources.

The player must manage:

-   Money
-   Risk
-   Time
-   Career

## Basic time rule

A normal business day consists of game working hours.

Default:

``` text
09:00–17:00
```

Each working hour is one game-time unit.

Example:

``` text
Monday 09:00
→ Monday 10:00
→ Monday 11:00
→ Monday 12:00
...
```

The game must maintain a real simulated calendar and clock.

Do not implement time as only:

``` text
current_day = 28
```

Maintain:

``` text
game_date
game_hour
game_minute
day_of_week
market_status
career_year
quarter
working_day
is_on_leave
```

------------------------------------------------------------------------

# 26. TIME ENGINE

Create a centralized TimeEngine.

Required functions:

``` text
advance_hour()
advance_hours(n)
advance_to_market_close()
advance_to_next_business_day()
skip_weekend()
start_leave()
end_leave()
```

Every simulation system consumes time updates through this engine.

The TimeEngine must be authoritative.

------------------------------------------------------------------------

# 27. WORK ACTION

Primary time action:

**WORK 1 HOUR**

When selected:

1.  Advance game time by one hour.
2.  Process market changes.
3.  Process scheduled events.
4.  Process news.
5.  Process employee updates.
6.  Update portfolio.
7.  Update risk.
8.  Check notifications.
9.  Check target progress.
10. Check career conditions.

Do not skip simulation logic when advancing time.

------------------------------------------------------------------------

# 28. TIME-SKIP OPTIONS

Provide:

-   WORK 1 HOUR
-   SKIP 2 HOURS
-   SKIP 4 HOURS
-   SKIP TO MARKET CLOSE
-   SKIP TO NEXT BUSINESS DAY
-   SKIP WEEKEND

The player must be able to intentionally skip time.

However, skipped time must still process all relevant simulation events.

Do not simply move the clock without processing the simulation.

------------------------------------------------------------------------

# 29. WEEKENDS

Saturday and Sunday are non-business days by default.

Example:

``` text
MONDAY     WORK
TUESDAY    WORK
WEDNESDAY  WORK
THURSDAY   WORK
FRIDAY     WORK
SATURDAY   WEEKEND
SUNDAY     WEEKEND
```

Provide:

**SKIP WEEKEND**

Weekend simulation can still process:

-   Global events
-   International market movements
-   News
-   Macro developments
-   Company announcements
-   Employee activity
-   Pending events

When the next business day begins, generate a:

**WEEKEND REPORT**

Example:

``` text
WEEKEND REPORT

GLOBAL MARKETS

Technology -2.8%
Oil +4.1%
Gold +1.2%

MAJOR NEWS

"Global technology stocks sell off."

YOUR PORTFOLIO

Friday close:
₹107.4 Cr

Monday open:
₹104.9 Cr

CHANGE:
-₹2.5 Cr

RISK:
HIGH
```

------------------------------------------------------------------------

# 30. PAID LEAVE SYSTEM

The player receives:

**60 PAID LEAVE DAYS PER CAREER YEAR**

Track:

-   Annual allowance
-   Used leave
-   Remaining leave
-   Current leave streak

Display:

``` text
PAID LEAVE

60 DAYS AVAILABLE
12 USED
48 REMAINING
```

The player can request:

-   1 day
-   3 days
-   5 days
-   Custom duration

Leave advances the game calendar.

The player is unavailable during leave.

------------------------------------------------------------------------

# 31. LEAVE CONSEQUENCES

The market does NOT stop because the player is on leave.

During leave:

-   Portfolio continues evolving
-   Events continue
-   News continues
-   Market moves continue

At early career levels, the player has limited delegation.

At higher levels, employees can manage routine responsibilities.

When the player returns, show:

``` text
WELCOME BACK

DAYS AWAY:
5

MARKET MOVE:
-3.4%

PORTFOLIO:
₹108.2 Cr → ₹104.9 Cr

NEW EVENTS:
4

TEAM ACTIONS:
3

RISK:
MEDIUM
```

Do not arbitrarily punish the player for taking leave.

Consequences must naturally emerge from the simulation.

------------------------------------------------------------------------

# 32. DELEGATION SYSTEM

As the player progresses, unlock delegation.

Example:

``` text
LEVEL 1
No dedicated portfolio manager.

LEVEL 2
Junior analyst.

LEVEL 3
Portfolio manager.

LEVEL 4
Multiple investment teams.

LEVEL 5+
Full investment division.
```

When the player is unavailable, delegated employees can perform
predefined actions according to:

-   Skills
-   Instructions
-   Risk limits
-   Portfolio policies

------------------------------------------------------------------------

# 33. SCHEDULED EVENTS

Events can have exact simulated timestamps.

Example:

``` text
09:00
Market Open

11:00
Economic Data Release

13:00
Company Earnings

15:00
CEO Meeting

16:00
Major Market Announcement

17:00
Market Close
```

If the player advances time past an event, the event must be processed.

If the player skips time, all events in the skipped interval must be
evaluated.

------------------------------------------------------------------------

# 34. TIME-BASED OPPORTUNITIES

Some opportunities should expire.

Example:

``` text
BUY OPPORTUNITY

Expires:
15:00
```

If the player spends time researching until 16:00:

``` text
OPPORTUNITY EXPIRED
```

This creates strategic time management.

The player should feel:

> "I have three hours before the market closes."

> "Should I buy now or spend another hour researching?"

------------------------------------------------------------------------

# 35. DAILY GAME LOOP

Each game day:

``` text
1. Pre-market
2. Market open
3. News/events
4. Player research
5. Player decisions
6. Trading
7. Market movement
8. Portfolio update
9. Risk update
10. Employee update
11. Notifications
12. End-of-day report
```

Then allow:

**NEXT DAY**

and optionally:

**NEXT WEEK**

for accelerated gameplay.

------------------------------------------------------------------------

# 36. DAILY REPORT

Display:

``` text
MARKET SUMMARY

NIFTY
+1.2%

PORTFOLIO
+₹0.82 Cr

BEST HOLDING
Apex Technologies +4.2%

WORST HOLDING
Nova Motors -2.8%

NEW EVENTS
3

RISK
MEDIUM

TARGET PROGRESS
68%
```

Then:

**CONTINUE**

------------------------------------------------------------------------

# 37. QUARTERLY REVIEW

At the end of 90 days, create a dramatic review.

Show:

-   CEO
-   CFO
-   Risk Manager

Use illustrated characters.

Display:

-   Starting capital
-   Ending capital
-   Return
-   Target
-   Drawdown
-   Risk
-   Best decision
-   Worst decision
-   Reputation change

Possible results:

-   PROMOTED
-   TARGET ACHIEVED
-   WARNING
-   FAILED
-   TERMINATED

Do not judge the player only by profit.

------------------------------------------------------------------------

# 38. FAILURE SYSTEM

The player can fail.

Possible causes:

-   Target missed
-   Excessive drawdown
-   Risk violations
-   Client losses
-   Compliance violations
-   Poor reputation

Progression:

``` text
WARNING
↓
FINAL WARNING
↓
TERMINATED
```

Then:

**START NEW CAREER**

Failure must feel consequential but fair.

------------------------------------------------------------------------

# 39. ML --- BEHIND THE SCENES

This is critical.

ML is NOT the visible central feature.

Do not create a simple:

> "AI predicts the stock"

button as the core mechanic.

ML acts as the hidden adaptive game director.

Architecture:

``` text
PLAYER
↓
GAME STATE
↓
PLAYER BEHAVIOR MODEL
↓
ADAPTIVE GAME DIRECTOR
↓
EVENT / DIFFICULTY / MARKET SCENARIO
↓
GAME STATE
↓
PLAYER
```

The player should simply experience a market that feels intelligent,
unpredictable and alive.

------------------------------------------------------------------------

# 40. PLAYER BEHAVIOR MODEL

Track:

-   Risk tolerance
-   Trading frequency
-   Reaction to losses
-   Position concentration
-   Cash usage
-   Reaction to news
-   Decision timing
-   Portfolio volatility
-   Target performance
-   Behavioral patterns

Classify approximately:

-   CONSERVATIVE
-   BALANCED
-   AGGRESSIVE
-   SPECULATIVE

Do not reveal this classification directly unless it becomes a
deliberate career/review feature later.

------------------------------------------------------------------------

# 41. ADAPTIVE GAME DIRECTOR

Inputs:

-   Player behavior
-   Current portfolio
-   Market regime
-   Career level
-   Reputation
-   Target progress
-   Recent performance
-   Recent events
-   Current time

Outputs:

-   Event probabilities
-   Scenario selection
-   Difficulty
-   Narrative pressure
-   Market regime transitions

IMPORTANT:

Never deliberately sabotage the player.

Do not force a stock crash simply because the player owns it.

Maintain believable probabilities.

The player must feel challenged, not cheated.

------------------------------------------------------------------------

# 42. ML DEVELOPMENT STRATEGY

Do not begin by pretending a neural network can magically run the game.

Use:

``` text
PHASE 1
Rule-based simulation

PHASE 2
Collect gameplay telemetry

PHASE 3
Generate training datasets

PHASE 4
Train ML models

PHASE 5
Evaluate models offline

PHASE 6
Deploy ML with rule-based fallback

PHASE 7
Allow ML to influence event selection and difficulty
```

The game must remain playable if the ML model is unavailable.

The ML layer must have a clean interface so models can be swapped
without rewriting the game engine.

------------------------------------------------------------------------

# 43. TELEMETRY

Record gameplay data:

``` text
game_id
player_id
day
game_time
career_level
cash
portfolio_value
portfolio_return
drawdown
risk_score
trade_count
buy_count
sell_count
largest_position
sector_exposure
market_regime
active_events
player_decisions
target_progress
reputation
leave_status
hours_worked
hours_skipped
```

This telemetry will later become training data for adaptive models.

------------------------------------------------------------------------

# 44. MARKETS SCREEN

Create a professional stock screener.

Columns:

-   Company
-   Sector
-   Price
-   Change
-   Volume
-   Volatility
-   Momentum
-   Valuation
-   Sentiment
-   Risk

Features:

-   Search
-   Sort
-   Filter
-   Sector filter
-   Open company

Clicking a company opens detailed analysis.

------------------------------------------------------------------------

# 45. STOCK DETAIL SCREEN

Show:

-   Company
-   Price
-   Daily change
-   Candlestick chart
-   Volume
-   Historical performance
-   SMA
-   EMA
-   RSI
-   MACD
-   Bollinger Bands
-   ATR
-   Fundamentals
-   Sector
-   News
-   Events
-   Risk

Technical indicators are research tools inside the game, not guaranteed
predictions.

------------------------------------------------------------------------

# 46. RESEARCH TERMINAL

Allow players to investigate companies.

Show:

-   Growth
-   Profitability
-   Debt
-   Valuation
-   Fundamentals
-   Momentum
-   Sentiment
-   Risk

Allow the player to record an internal investment thesis.

Example:

``` text
BULLISH

"Strong growth and improving fundamentals."
```

or:

``` text
BEARISH

"Valuation appears excessive."
```

The thesis can later be used when evaluating decision quality.

------------------------------------------------------------------------

# 47. PERFORMANCE SCREEN

Display:

-   Portfolio return
-   Benchmark return
-   Maximum drawdown
-   Risk score
-   Win rate
-   Average trade
-   Best trade
-   Worst trade
-   Sector attribution
-   Monthly performance
-   Quarterly performance

Also display:

``` text
TARGET
ACTUAL
DIFFERENCE
```

------------------------------------------------------------------------

# 48. CAREER SCREEN

Make this visually similar in spirit to a career-management game.

Display:

-   Current role
-   Career level
-   XP
-   Reputation
-   Objectives
-   Promotion requirements
-   Career history
-   Achievements
-   Major decisions

Example:

``` text
HEAD OF INVESTMENTS

PROMOTION REQUIREMENTS

Return > 12%
Drawdown < 10%
Reputation > 75
Target achieved
```

------------------------------------------------------------------------

# 49. NOTIFICATION SYSTEM

Create professional dynamic notifications.

Examples:

``` text
MARKET ALERT
Technology sector volatility increased.

RISK WARNING
Banking exposure exceeds policy limit.

TARGET UPDATE
You are 74% toward your quarterly target.

BREAKING NEWS
Nova Motors announces major expansion.

CEO MESSAGE
"Come to my office. We need to discuss the portfolio."
```

Notifications must be tied to actual game state.

------------------------------------------------------------------------

# 50. MAIN ACTION BAR

Provide prominent actions:

-   BUY STOCK
-   SELL STOCK
-   RESEARCH
-   PORTFOLIO
-   WORK 1 HOUR
-   SKIP HOURS
-   NEXT BUSINESS DAY
-   TAKE LEAVE

The time controls must be easy to understand.

The player should always know how much simulated time an action
consumes.

------------------------------------------------------------------------

# 51. SAVE / LOAD

Implement:

-   New Game
-   Save Game
-   Load Game
-   Restart Career

Persist:

-   Game seed
-   Career
-   Portfolio
-   Holdings
-   Cash
-   Transactions
-   Market state
-   Events
-   Employees
-   Reputation
-   XP
-   Current date
-   Current time
-   Quarter
-   Leave allowance
-   Telemetry

Refreshing the browser must not corrupt authoritative game state.

------------------------------------------------------------------------

# 52. GAME SEED

Every new career receives a unique seed.

The seed determines:

-   Initial company characteristics
-   Market path
-   Events
-   Economic cycles
-   Employee characteristics
-   Event timing

Save the seed.

This makes a game reproducible.

------------------------------------------------------------------------

# 53. PROJECT STRUCTURE

Use a clean structure similar to:

``` text
investment-banker-mode/

frontend/
    src/
        components/
            terminal/
            market/
            portfolio/
            trading/
            research/
            news/
            career/
            team/
            time/
            common/
        pages/
        hooks/
        services/
        types/
        game/

backend/
    app/
        api/
        models/
        schemas/
        services/
        simulation/
            time_engine.py
            market_engine.py
            event_engine.py
            portfolio_engine.py
            risk_engine.py
            career_engine.py
            economy_engine.py
            player_engine.py
        ml/
            features.py
            behavior_model.py
            game_director.py
            inference.py
            training/
        telemetry/
        database/

tests/

docker/

docs/
```

------------------------------------------------------------------------

# 54. API DESIGN

Implement real APIs:

``` text
GET  /api/game/state
POST /api/game/new
POST /api/game/advance-hour
POST /api/game/advance-hours
POST /api/game/advance-to-close
POST /api/game/advance-next-business-day
POST /api/game/skip-weekend

GET  /api/market
GET  /api/market/{symbol}

GET  /api/portfolio

POST /api/trade/buy
POST /api/trade/sell

GET  /api/news
GET  /api/events

GET  /api/career
GET  /api/team

GET  /api/performance

POST /api/leave/start

POST /api/game/save
POST /api/game/load
```

Do not put the simulation entirely in frontend JavaScript.

------------------------------------------------------------------------

# 55. DATABASE

Create proper models/tables for:

-   games
-   players
-   stocks
-   stock_prices
-   market_states
-   portfolios
-   holdings
-   transactions
-   events
-   news
-   employees
-   career_progress
-   career_levels
-   clients
-   game_days
-   telemetry
-   leave_records

Use proper foreign keys and indexes where appropriate.

------------------------------------------------------------------------

# 56. SECURITY AND DATA INTEGRITY

Backend is authoritative.

Validate:

-   Trade quantity
-   Cash balance
-   Holdings
-   Game state
-   Game time
-   Game day
-   Stock symbol
-   Career permissions
-   Leave allowance
-   Leave duration

Never trust frontend values.

Prevent:

-   Negative quantities
-   Buying without sufficient cash
-   Selling unavailable shares
-   Invalid symbols
-   Invalid game time
-   Invalid career actions
-   Exceeding annual leave

------------------------------------------------------------------------

# 57. FIRST VERTICAL SLICE

This is the first development milestone.

Do NOT attempt to implement every advanced feature immediately.

Build this completely:

``` text
NEW GAME
↓
CEO INTRO
↓
CAREER CREATED
↓
MAIN TERMINAL
↓
20 STOCKS
↓
MARKET SIMULATION
↓
RESEARCH
↓
BUY
↓
SELL
↓
PORTFOLIO UPDATE
↓
NEWS EVENT
↓
MARKET REACTION
↓
RISK UPDATE
↓
TIME ADVANCEMENT
↓
WEEKEND SKIP
↓
LEAVE
↓
90 DAYS
↓
QUARTERLY REVIEW
↓
PROMOTION / WARNING / FAILURE
```

Everything in this chain must actually work.

------------------------------------------------------------------------

# 58. DEMO CAREER

Create a polished default career.

``` text
COMPANY
Apex Capital

ROLE
Head of Investments

CAPITAL
₹100 Cr

TARGET
₹112 Cr

MAX DRAWDOWN
10%

RISK
MEDIUM

DURATION
90 DAYS
```

Day 1:

``` text
09:00

100% CASH
```

The player chooses how to invest.

Do not force a predetermined strategy.

------------------------------------------------------------------------

# 59. GAMEPLAY FAIRNESS

There must be no single guaranteed winning strategy.

Players should be able to succeed through different approaches:

-   Conservative
-   Balanced
-   Aggressive
-   Tactical/event-driven
-   Diversified
-   Concentrated but risk-managed

Different strategies should have different:

-   Expected returns
-   Volatility
-   Drawdown risk
-   Career implications

Do not secretly rig outcomes against a player.

------------------------------------------------------------------------

# 60. ACCEPTANCE TESTS

Before declaring the first version complete, verify:

### Game

1.  New Game creates a unique seed.
2.  Player starts with ₹100 Cr.
3.  20 stocks exist.
4.  Stock prices change after advancing time.
5.  BUY reduces cash and increases holdings.
6.  SELL increases cash and reduces holdings.
7.  Cannot buy without enough cash.
8.  Cannot sell more shares than owned.
9.  Portfolio value changes when prices change.
10. News events affect market state.
11. Risk engine responds to concentration.
12. Target progress updates.
13. Career result updates correctly.
14. Save/load works.

### Time

15. Monday 09:00 + 1 hour = Monday 10:00.
16. Skipping 4 hours processes all relevant events in those 4 hours.
17. Friday + skip weekend reaches Monday.
18. Weekend events are processed.
19. Taking leave advances the calendar correctly.
20. Leave allowance decreases correctly.
21. Leave cannot exceed remaining allowance.
22. Market and portfolio continue evolving during leave.
23. Events occurring during leave are processed.
24. Returning from leave generates a report.
25. Game time persists through save/load.

### Career

26. 90-day career ends in quarterly review.
27. Promotion/failure uses multiple metrics.
28. Reputation changes based on performance.
29. Risk violations have consequences.

### Engineering

30. Frontend cannot directly modify authoritative game state.
31. Backend validates trades.
32. No visible button is non-functional.
33. No major screen is merely a static mockup.
34. Browser refresh does not corrupt game state.
35. Backend tests pass.
36. Frontend tests pass where applicable.
37. Application starts using documented commands.

------------------------------------------------------------------------

# 61. DEVELOPMENT WORKFLOW

Follow this exact sequence.

## Step 1

Inspect the repository and environment.

## Step 2

Create project structure.

## Step 3

Set up frontend, backend and database.

## Step 4

Implement game state.

## Step 5

Implement TimeEngine.

## Step 6

Implement market simulation.

## Step 7

Implement portfolio and trading.

## Step 8

Implement event/news engine.

## Step 9

Implement risk engine.

## Step 10

Implement career/target system.

## Step 11

Build main terminal UI.

## Step 12

Connect UI to backend.

## Step 13

Create CEO/dialogue system.

## Step 14

Implement weekends and leave.

## Step 15

Implement save/load.

## Step 16

Implement telemetry.

## Step 17

Create rule-based adaptive game director.

## Step 18

Create ML interfaces.

## Step 19

Run tests.

## Step 20

Run the complete game.

## Step 21

Fix all errors.

## Step 22

Only then polish animations, charts and visual details.

------------------------------------------------------------------------

# 62. SELF-CHECK AFTER EACH MILESTONE

After each major milestone:

1.  Run the application.
2.  Inspect the UI.
3.  Test the feature.
4.  Check browser console.
5.  Check backend logs.
6.  Run relevant tests.
7.  Fix errors.
8.  Continue.

Do not assume generated code works.

------------------------------------------------------------------------

# 63. DO NOT OVERBUILD

The first goal is NOT:

> "Build a seven-level investment empire."

The first goal is:

> "Make Level 1 genuinely playable."

A smaller fully functional game is better than a huge collection of
broken screens.

Once Level 1 works, extend the same architecture.

------------------------------------------------------------------------

# 64. FUTURE EXPANSION

The architecture should support these later:

-   Multiple investment firms
-   Competing banks
-   Employee recruitment
-   Employee turnover
-   Bonds
-   IPOs
-   M&A
-   Private equity
-   Hedge funds
-   Institutional clients
-   Portfolio mandates
-   Market crashes
-   Recessions
-   Economic cycles
-   Competitor behavior
-   Corporate politics
-   Board meetings
-   Client negotiations
-   Multiple portfolios
-   International markets
-   Advanced ML game director
-   Multiplayer/leaderboards
-   Scenario editor
-   Custom difficulty
-   Career statistics

Do not implement these in the first MVP.

Create clean extension points.

------------------------------------------------------------------------

# 65. GAME ATMOSPHERE

The game should feel alive.

The player should see:

-   Ticker movements
-   Chart changes
-   News arriving
-   Messages arriving
-   Risk warnings
-   CEO requests
-   Employee recommendations
-   Time passing
-   Market open/close
-   Weekend transitions
-   Leave reports
-   Quarterly reviews

The game should create moments such as:

> "I only have two hours before the market closes."

> "The CEO wants another ₹3 Cr."

> "My largest position just dropped 7%."

> "Should I sell?"

> "The risk manager is warning me."

> "There's an earnings announcement in one hour."

> "Should I take leave or stay?"

> "I am 92% toward my target."

> "One bad decision could cost me the quarter."

------------------------------------------------------------------------

# 66. FINAL EXPERIENCE

When the game launches, the player should NOT feel:

> "I'm using a stock dashboard."

They should feel:

> "I've been hired."

> "I've been given ₹100 Cr."

> "I have 90 days."

> "I have to hit ₹112 Cr."

> "The market just moved."

> "My risk manager is warning me."

> "The CEO wants results."

> "I need to decide whether to buy."

> "Should I hold?"

> "Should I sell?"

> "Why did this stock fall?"

> "What just happened?"

> "Can I hit my target?"

> "Will I get promoted?"

> "Or will I get fired?"

That emotional loop is the product.

------------------------------------------------------------------------

# 67. FINAL IMPLEMENTATION COMMAND

START BUILDING NOW.

Do not give a long explanation of what you are going to build.

Create the project.

Implement the first complete playable vertical slice.

Use the supplied visual reference as the design direction.

Prioritize:

1.  Gameplay
2.  Functionality
3.  Simulation quality
4.  UI quality
5.  Visual polish
6.  ML extensibility

When the first vertical slice is complete, report:

-   What was implemented
-   Project structure
-   How to run it
-   Tests performed
-   Known limitations
-   What should be built next

But do NOT stop merely because documentation is complete.

The goal is a **working game**.

------------------------------------------------------------------------

# 68. NON-NEGOTIABLE RULES

1.  This is a simulation game, not financial advice.
2.  All core market data is simulated.
3.  The backend is authoritative.
4.  Time is a real gameplay resource.
5.  One normal working hour advances one game hour.
6.  Weekends exist.
7.  The player has 60 paid leave days per career year.
8.  The market continues while the player is on leave.
9.  Skipping time must process everything that occurs during the skipped
    period.
10. ML is behind the scenes and adaptive.
11. ML must have a rule-based fallback.
12. The game must never deliberately cheat the player.
13. Every visible gameplay control must work.
14. Build the vertical slice before expanding.
15. Test the game by actually running it.
16. Fix errors before declaring milestones complete.
17. Do not replace gameplay with static UI.
18. Do not replace simulation with hardcoded outcomes.
19. Do not create fake ML merely for branding.
20. The final experience must feel like an investment career, not a
    stock dashboard.

# END OF MASTER SPECIFICATION
