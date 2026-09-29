"""
Event engine — company, macro and market events, scheduled releases and
multi-day branching event chains. Every event creates news and changes market
state (price jumps, drift, sentiment, volatility, macro variables).

Event selection never looks at the player's portfolio. The adaptive director can
only scale the overall event intensity within a narrow band.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Optional

import numpy as np

from app.simulation import economy_engine
from app.simulation.constants import REGIMES, SECTOR_MACRO, SECTORS
from app.simulation.state import GameState, MarketEvent, NewsItem, ScheduledEvent, StockState
from app.simulation.time_engine import is_business_day, next_business_day

# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #
# impact: (low, high) total log-return impact; jump: fraction applied instantly.
COMPANY_EVENTS: dict[str, dict] = {
    "PRODUCT_LAUNCH": {"impact": (0.02, 0.05), "jump": 0.5, "hours": 16, "sev": 2,
                       "headlines": ["{name} unveils flagship product line", "{name} launches next-generation offering"],
                       "body": "Management expects the launch to add meaningfully to revenue over the next four quarters."},
    "PRODUCT_FAILURE": {"impact": (-0.05, -0.02), "jump": 0.6, "hours": 16, "sev": 3,
                        "headlines": ["{name} recalls products after quality complaints", "{name} product launch falls flat"],
                        "body": "Channel checks point to weak demand and possible write-downs."},
    "MAJOR_CONTRACT": {"impact": (0.03, 0.07), "jump": 0.6, "hours": 12, "sev": 3,
                       "headlines": ["{name} wins multi-year contract worth ₹{size} Cr", "{name} bags large order from government agency"],
                       "body": "The order book now covers roughly {cover} years of revenue, analysts estimate."},
    "ACQUISITION": {"impact": (-0.02, 0.02), "jump": 0.8, "hours": 8, "sev": 3, "chain": "ACQUISITION",
                    "headlines": ["{name} announces aggressive acquisition of a mid-sized rival",
                                  "{name} agrees to buy competitor in all-cash deal"],
                    "body": "The ₹{size} Cr deal would be funded largely through fresh borrowing."},
    "FAILED_ACQUISITION": {"impact": (-0.04, -0.02), "jump": 0.7, "hours": 8, "sev": 2,
                           "headlines": ["{name}'s takeover bid collapses", "{name} walks away from acquisition talks"],
                           "body": "The company cited valuation differences; a break fee is payable."},
    "CEO_RESIGNATION": {"impact": (-0.05, -0.02), "jump": 0.7, "hours": 16, "sev": 3, "chain": "SUCCESSION",
                        "headlines": ["{name} CEO resigns unexpectedly", "Leadership shock at {name} as CEO steps down"],
                        "body": "The board has appointed an interim chief while it searches for a successor."},
    "REGULATORY_INVESTIGATION": {"impact": (-0.08, -0.04), "jump": 0.6, "hours": 24, "sev": 4, "chain": "REGULATORY",
                                 "headlines": ["Regulator opens investigation into {name}",
                                               "{name} under regulatory scanner over disclosure lapses"],
                                 "body": "The company says it is cooperating fully. Penalties, if any, are not yet quantifiable."},
    "FACTORY_SHUTDOWN": {"impact": (-0.05, -0.02), "jump": 0.6, "hours": 16, "sev": 3, "chain": "SHUTDOWN",
                         "headlines": ["Fire halts production at {name}'s main plant", "{name} suspends operations at key facility"],
                         "body": "Management expects a partial restart within days but guidance is under review."},
    "MANAGEMENT_SCANDAL": {"impact": (-0.14, -0.07), "jump": 0.7, "hours": 24, "sev": 5,
                           "headlines": ["Whistleblower alleges accounting irregularities at {name}",
                                         "Governance storm engulfs {name}"],
                           "body": "Auditors have flagged related-party transactions. Several independent directors have resigned."},
    "BREAKTHROUGH_TECH": {"impact": (0.06, 0.12), "jump": 0.6, "hours": 24, "sev": 4,
                          "headlines": ["{name} announces technology breakthrough", "{name} secures landmark patent approval"],
                          "body": "Analysts say the development could reshape the company's long-term economics."},
    "BROKER_UPGRADE": {"impact": (0.015, 0.035), "jump": 0.6, "hours": 8, "sev": 1,
                       "headlines": ["Brokerage upgrades {name} to BUY", "{name} gets price-target hike from leading broker"],
                       "body": "The note cites improving margins and reasonable valuations."},
    "BROKER_DOWNGRADE": {"impact": (-0.035, -0.015), "jump": 0.6, "hours": 8, "sev": 1,
                         "headlines": ["Brokerage downgrades {name} to SELL", "{name} cut to UNDERWEIGHT on valuation worries"],
                         "body": "The analyst sees limited upside after the recent run and flags execution risk."},
    "INSTITUTIONAL_ACCUMULATION": {"impact": (0.02, 0.04), "jump": 0.2, "hours": 24, "sev": 1, "flow": 0.5,
                                   "headlines": ["Large funds quietly accumulate {name}", "Bulk deals show institutions buying {name}"],
                                   "body": "Exchange data shows persistent buying from domestic mutual funds."},
    "INSTITUTIONAL_DISTRIBUTION": {"impact": (-0.04, -0.02), "jump": 0.2, "hours": 24, "sev": 1, "flow": -0.5,
                                   "headlines": ["Foreign funds trim stake in {name}", "Block sales weigh on {name}"],
                                   "body": "Exchange data shows persistent institutional selling over several sessions."},
    "SHARE_BUYBACK": {"impact": (0.02, 0.04), "jump": 0.6, "hours": 16, "sev": 2,
                      "headlines": ["{name} announces share buyback at a premium", "{name} board approves ₹{size} Cr buyback"],
                      "body": "The buyback signals management confidence and returns surplus cash to shareholders."},
    "EARNINGS_WARNING": {"impact": (-0.07, -0.04), "jump": 0.7, "hours": 16, "sev": 3,
                         "headlines": ["{name} issues profit warning", "{name} cuts guidance ahead of results"],
                         "body": "The company blamed weaker demand and one-off costs."},
}

# Follow-ups used by chains
CHAIN_EVENTS: dict[str, dict] = {
    "ANALYST_VALUATION_CONCERN": {"impact": (-0.04, -0.02), "jump": 0.6, "hours": 8, "sev": 2,
                                  "headlines": ["Analysts question valuation of {name}'s acquisition"],
                                  "body": "Brokerages estimate the deal is dilutive to earnings for at least two years."},
    "ANALYST_BACKING": {"impact": (0.02, 0.04), "jump": 0.6, "hours": 8, "sev": 2,
                        "headlines": ["Analysts back {name}'s acquisition strategy"],
                        "body": "Synergy estimates look credible; several brokers raise targets."},
    "DEBT_CONCERNS": {"impact": (-0.05, -0.03), "jump": 0.6, "hours": 16, "sev": 3,
                      "headlines": ["Debt concerns emerge at {name} after deal"],
                      "body": "Leverage is set to rise sharply; bond spreads have widened."},
    "RATING_DOWNGRADE": {"impact": (-0.08, -0.04), "jump": 0.7, "hours": 16, "sev": 4,
                         "headlines": ["Credit rating agency downgrades {name}"],
                         "body": "The agency cited acquisition-related leverage and weak cash flows."},
    "FINANCING_SECURED": {"impact": (0.02, 0.04), "jump": 0.6, "hours": 8, "sev": 2,
                          "headlines": ["{name} secures long-term financing for acquisition"],
                          "body": "Refinancing at favourable rates eases balance-sheet worries."},
    "DEAL_COMPLETED": {"impact": (0.03, 0.05), "jump": 0.6, "hours": 16, "sev": 2,
                       "headlines": ["{name} completes acquisition ahead of schedule"],
                       "body": "Integration is on track and the combined entity reaffirms guidance."},
    "REGULATOR_CLEARS": {"impact": (0.04, 0.07), "jump": 0.7, "hours": 8, "sev": 3,
                         "headlines": ["Regulator closes probe into {name} without penalty"],
                         "body": "The overhang is removed; analysts expect a relief rally."},
    "REGULATOR_PENALTY": {"impact": (-0.06, -0.03), "jump": 0.7, "hours": 8, "sev": 3,
                          "headlines": ["Regulator fines {name}, orders business restrictions"],
                          "body": "The penalty and restrictions are expected to weigh on earnings this year."},
    "PLANT_RESTART": {"impact": (0.02, 0.04), "jump": 0.7, "hours": 8, "sev": 2,
                      "headlines": ["{name} resumes production at affected plant"],
                      "body": "Management says lost output will be recovered over the quarter."},
    "SHUTDOWN_EXTENDED": {"impact": (-0.05, -0.03), "jump": 0.6, "hours": 16, "sev": 3,
                          "headlines": ["{name} extends plant shutdown, warns on output"],
                          "body": "Repairs are taking longer than expected."},
    "NEW_CEO_WELL_RECEIVED": {"impact": (0.02, 0.04), "jump": 0.7, "hours": 8, "sev": 2,
                              "headlines": ["{name} names respected industry veteran as CEO"],
                              "body": "Investors welcome the appointment."},
    "SUCCESSION_CONCERNS": {"impact": (-0.04, -0.02), "jump": 0.6, "hours": 8, "sev": 2,
                            "headlines": ["Succession uncertainty lingers at {name}"],
                            "body": "The board has yet to find a permanent chief executive."},
}

# Macro/market events. shocks: changes to economy state; base: market-wide impact;
# macro_scale scales sector sensitivities to the shocks.
MACRO_EVENTS: dict[str, dict] = {
    "OIL_SPIKE": {"shocks": {"oil_shock": 0.9}, "base": -0.0036, "macro_scale": 0.0150, "sev": 3, "hours": 16,
                  "headlines": ["Crude prices spike after supply disruption in the Gulf"],
                  "body": "Brent jumped sharply overnight. Oil-importing economies face higher import bills."},
    "OIL_SLUMP": {"shocks": {"oil_shock": -0.8}, "base": 0.0024, "macro_scale": 0.0120, "sev": 2, "hours": 16,
                  "headlines": ["Oil slides as producers boost output"],
                  "body": "Lower crude is a tailwind for oil-importers and fuel-sensitive sectors."},
    "CURRENCY_SHOCK": {"shocks": {"inr_shock": 0.9, "global_risk": -0.2}, "base": -0.0048, "macro_scale": 0.0120,
                       "sev": 3, "hours": 16,
                       "headlines": ["Rupee slumps to record low against the dollar"],
                       "body": "Foreign outflows and a strong dollar pressure the currency. Exporters benefit."},
    "GLOBAL_SELLOFF": {"shocks": {"global_risk": -0.8}, "base": -0.0108, "macro_scale": 0.0072, "sev": 4, "hours": 16,
                       "vol": 0.5,
                       "headlines": ["Global markets enter risk-off mode", "Wall Street tumbles; Asian markets follow"],
                       "body": "Growth fears and tighter financial conditions trigger a broad selloff."},
    "GLOBAL_RALLY": {"shocks": {"global_risk": 0.6}, "base": 0.0060, "macro_scale": 0.0060, "sev": 2, "hours": 16,
                     "headlines": ["Global equities rally on soft-landing hopes"],
                     "body": "Cooling inflation data abroad revives risk appetite."},
    "RECESSION_FEARS": {"shocks": {"global_risk": -0.6, "rate_pressure": -0.3}, "base": -0.0072, "macro_scale": 0.0060,
                        "sev": 4, "hours": 24, "vol": 0.3,
                        "headlines": ["Recession fears grip markets as leading indicators weaken"],
                        "body": "Economists slash growth forecasts; cyclical sectors bear the brunt."},
    "RECOVERY_SIGNS": {"shocks": {"global_risk": 0.5}, "base": 0.0060, "macro_scale": 0.0060, "sev": 2, "hours": 24,
                       "headlines": ["Economic recovery gathers pace, surveys show"],
                       "body": "Manufacturing and services activity expand at the fastest pace in months."},
}

MARKET_EVENTS: dict[str, dict] = {
    "SECTOR_RALLY": {"impact": (0.025, 0.05), "hours": 16, "sev": 2,
                     "headlines": ["{sector} stocks rally on strong demand outlook", "Buying frenzy in {sector} names"],
                     "body": "Fund managers are rotating into {sector} ahead of the earnings season."},
    "SECTOR_REGULATION": {"impact": (-0.05, -0.025), "hours": 16, "sev": 3,
                          "headlines": ["{sector} sector faces new regulation", "Government tightens rules for {sector} companies"],
                          "body": "The draft framework could compress margins across the {sector} sector."},
    "MARKET_SELLOFF": {"impact": (-0.022, -0.01), "hours": 8, "sev": 3, "vol": 0.4,
                       "headlines": ["Sharp selloff wipes out gains on Dalal Street"],
                       "body": "Heavy selling across sectors as traders cut leveraged positions."},
    "VOLATILITY_SPIKE": {"impact": (-0.005, 0.005), "hours": 12, "sev": 2, "vol": 0.8,
                         "headlines": ["Volatility jumps as markets whipsaw"],
                         "body": "Intraday swings widen; the BHARAT VOL index climbs."},
    "INSTITUTIONAL_BUYING": {"impact": (0.012, 0.025), "hours": 24, "sev": 1, "flow": 0.3,
                             "headlines": ["Foreign investors turn net buyers for fifth straight session"],
                             "body": "Steady inflows are supporting large-cap stocks."},
    "INSTITUTIONAL_SELLING": {"impact": (-0.025, -0.012), "hours": 24, "sev": 2, "flow": -0.3,
                              "headlines": ["Foreign investors pull money out of local equities"],
                              "body": "Outflows have picked up amid a stronger dollar."},
    "LIQUIDITY_CRISIS": {"impact": (-0.05, -0.03), "hours": 24, "sev": 5, "vol": 0.8,
                         "headlines": ["Liquidity crunch hits lenders as funding markets freeze"],
                         "body": "Short-term borrowing costs spike; lenders with weak liabilities are under pressure."},
}


SHOCK_TO_SENS = {"oil_shock": "oil", "inr_shock": "inr", "global_risk": "global", "rate_pressure": "rates"}


def _fmt(tpl: str, **kw) -> str:
    try:
        return tpl.format(**kw)
    except (KeyError, IndexError):
        return tpl


class EventEngine:
    def __init__(self, state: GameState, rng: np.random.Generator):
        self.state = state
        self.rng = rng

    # ------------------------------------------------------------------ #
    # Core event creation
    # ------------------------------------------------------------------ #
    def _apply(self, ev: MarketEvent, in_session: bool, jumps: dict[str, float]) -> None:
        """Apply instant jumps (intraday) or opening gaps (outside hours) and sentiment effects."""
        for sym, total in ev.impacts.items():
            j = total * ev.jump_fraction
            if in_session:
                jumps[sym] = jumps.get(sym, 0.0) + j
            else:
                self.state.stocks[sym].pending_gap += j
            s = self.state.stocks[sym]
            s.sentiment = float(np.clip(s.sentiment + np.sign(total) * min(0.5, abs(total) * 6), -1, 1))
        self.state.events.append(ev)
        self.state.events = self.state.events[-200:]
        self.state.outbox("events").append({
            "event_id": ev.id, "t": ev.started_at.isoformat(), "type": ev.type, "category": ev.category,
            "severity": ev.severity, "title": ev.title, "impact": ev.market_impact,
            "symbols": ",".join(ev.affected_symbols[:20]), "sectors": ",".join(ev.affected_sectors),
        })

    def _news(self, ev: MarketEvent, category: str) -> NewsItem:
        tone = "POSITIVE" if ev.market_impact > 0.002 else "NEGATIVE" if ev.market_impact < -0.002 else "NEUTRAL"
        item = NewsItem(
            id=self.state.next_id("NEWS"), time=self.state.now, headline=ev.title, body=ev.narrative,
            category=category, tone=tone, severity=ev.severity, symbols=ev.affected_symbols[:6],
            sectors=ev.affected_sectors, event_id=ev.id,
        )
        self.add_news(item)
        return item

    def add_news(self, item: NewsItem) -> None:
        self.state.news.append(item)
        self.state.news = self.state.news[-250:]
        self.state.outbox("news").append({
            "news_id": item.id, "t": item.time.isoformat(), "headline": item.headline, "body": item.body,
            "category": item.category, "tone": item.tone, "severity": item.severity,
            "symbols": ",".join(item.symbols),
        })

    def _regime_scale(self, negative: bool) -> float:
        reg = self.state.market.regime
        if negative:
            return {"CRISIS": 1.3, "BEAR": 1.1, "VOLATILE": 1.05}.get(reg, 1.0)
        return {"BULL": 1.1, "CRISIS": 0.85, "BEAR": 0.95}.get(reg, 1.0)

    def company_event(self, etype: str, symbol: str, in_session: bool, jumps: dict[str, float],
                      chain_id: Optional[str] = None, stage: int = 0, templates: dict | None = None) -> MarketEvent:
        tpl = (templates or COMPANY_EVENTS).get(etype) or CHAIN_EVENTS[etype]
        s = self.state.stocks[symbol]
        lo, hi = tpl["impact"]
        base = float(self.rng.uniform(lo, hi))
        base *= (0.6 + 0.8 * s.event_sensitivity) * self._regime_scale(base < 0)
        if etype == "ACQUISITION":
            base += -0.03 * (s.debt - 0.4)
        fmt = {"name": s.name, "sector": s.sector, "size": f"{int(self.rng.integers(8, 60)) * 100:,}",
               "cover": round(float(self.rng.uniform(1.2, 3.5)), 1)}
        headline = _fmt(str(self.rng.choice(tpl["headlines"])), **fmt)
        body = _fmt(tpl["body"], **fmt)
        ev = MarketEvent(
            id=self.state.next_id("EVT"), type=etype, category="company", severity=tpl["sev"],
            title=headline, narrative=body, affected_symbols=[symbol], affected_sectors=[s.sector],
            probability=0.0, market_impact=round(base, 4), impacts={symbol: base},
            jump_fraction=tpl["jump"], duration_hours=tpl["hours"], remaining_hours=tpl["hours"],
            started_at=self.state.now, chain_id=chain_id, chain_stage=stage,
        )
        if "flow" in tpl:
            s.institutional_pressure = float(np.clip(s.institutional_pressure + tpl["flow"], -1, 1))
        # Fundamentals follow the story
        s.fair_value *= math.exp(base * 0.6)
        chain = tpl.get("chain")
        if chain and not chain_id:
            ev.chain_id = ev.id
            ev.follow_up_events = self._start_chain(chain, symbol, ev.id)
        self._apply(ev, in_session, jumps)
        self._news(ev, "COMPANY")
        return ev

    def _start_chain(self, chain: str, symbol: str, chain_id: str) -> list[str]:
        days = {"ACQUISITION": 2, "SUCCESSION": 4, "REGULATORY": 6, "SHUTDOWN": 4}[chain]
        when = self._business_days_ahead(days, hour=int(self.rng.choice([10, 13, 16])))
        self.state.scheduled.append(ScheduledEvent(
            id=self.state.next_id("SCH"), time=when, kind="CHAIN", public=False, symbol=symbol,
            title=f"{chain} follow-up", payload={"chain": chain, "stage": 2, "chain_id": chain_id}))
        self.state.scheduled.sort(key=lambda x: x.time)
        return [f"{chain}:stage2"]

    def _business_days_ahead(self, n: int, hour: int) -> datetime:
        d = self.state.now.date()
        for _ in range(n):
            d = next_business_day(d)
        return datetime.combine(d, datetime.min.time()).replace(hour=hour)

    def schedule_hidden(self, etype: str, symbol: str, days: int) -> None:
        """Hidden future company event (e.g. what an informed block-deal seller knew)."""
        when = self._business_days_ahead(days, hour=int(self.rng.choice([10, 11, 14])))
        self.state.scheduled.append(ScheduledEvent(
            id=self.state.next_id("SCH"), time=when, kind="HIDDEN", public=False, symbol=symbol,
            title=etype, payload={"type": etype}))
        self.state.scheduled.sort(key=lambda x: x.time)

    def _chain_step(self, sch: ScheduledEvent, in_session: bool, jumps: dict[str, float]) -> None:
        chain, stage, cid, sym = sch.payload["chain"], sch.payload["stage"], sch.payload["chain_id"], sch.symbol
        s = self.state.stocks[sym]
        r = self.rng.random()
        nxt: Optional[tuple[str, int, int]] = None  # (chain, stage, days)
        if chain == "ACQUISITION":
            if stage == 2:
                if r < 0.45 + 0.4 * s.debt:
                    etype, nxt = "ANALYST_VALUATION_CONCERN", ("ACQUISITION", 3, 3)
                else:
                    etype, nxt = "ANALYST_BACKING", ("ACQUISITION", 5, 6)
            elif stage == 3:
                if r < 0.35 + 0.6 * s.debt:
                    etype, nxt = "DEBT_CONCERNS", ("ACQUISITION", 4, 5)
                else:
                    etype = "FINANCING_SECURED"
            elif stage == 4:
                etype = "RATING_DOWNGRADE" if r < 0.55 + 0.4 * s.debt else "FINANCING_SECURED"
            else:
                etype = "DEAL_COMPLETED"
        elif chain == "REGULATORY":
            etype = "REGULATOR_CLEARS" if r < 0.35 + s.profitability * 1.5 else "REGULATOR_PENALTY"
        elif chain == "SHUTDOWN":
            etype = "PLANT_RESTART" if r < 0.65 else "SHUTDOWN_EXTENDED"
        else:  # SUCCESSION
            etype = "NEW_CEO_WELL_RECEIVED" if r < 0.55 else "SUCCESSION_CONCERNS"
        self.company_event(etype, sym, in_session, jumps, chain_id=cid, stage=stage, templates=CHAIN_EVENTS)
        if nxt:
            when = self._business_days_ahead(nxt[2], hour=int(self.rng.choice([10, 13, 16])))
            self.state.scheduled.append(ScheduledEvent(
                id=self.state.next_id("SCH"), time=when, kind="CHAIN", public=False, symbol=sym,
                title=f"{chain} follow-up", payload={"chain": nxt[0], "stage": nxt[1], "chain_id": cid}))
            self.state.scheduled.sort(key=lambda x: x.time)

    def macro_event(self, etype: str, in_session: bool, jumps: dict[str, float]) -> MarketEvent:
        tpl = MACRO_EVENTS[etype]
        e = self.state.market.economy
        for k, v in tpl["shocks"].items():
            setattr(e, k, float(np.clip(getattr(e, k) + v, -1.5, 1.5)))
        impacts = {}
        for sym, s in self.state.stocks.items():
            sens = SECTOR_MACRO[s.sector]
            macro = sum(sens[SHOCK_TO_SENS[k]] * v for k, v in tpl["shocks"].items())
            imp = (tpl["base"] * s.beta + tpl["macro_scale"] * macro) * float(self.rng.uniform(0.8, 1.2))
            impacts[sym] = imp
        ev = MarketEvent(
            id=self.state.next_id("EVT"), type=etype, category="macro", severity=tpl["sev"],
            title=str(self.rng.choice(tpl["headlines"])), narrative=tpl["body"],
            affected_symbols=list(impacts), affected_sectors=list(SECTORS),
            market_impact=round(tpl["base"], 4), impacts=impacts, jump_fraction=0.6,
            vol_boost=tpl.get("vol", 0.0), duration_hours=tpl["hours"], remaining_hours=tpl["hours"],
            started_at=self.state.now,
        )
        self._apply(ev, in_session, jumps)
        self._news(ev, "MACRO")
        return ev

    def market_event(self, etype: str, in_session: bool, jumps: dict[str, float], sector: Optional[str] = None) -> MarketEvent:
        tpl = MARKET_EVENTS[etype]
        lo, hi = tpl["impact"]
        base = float(self.rng.uniform(lo, hi)) * self._regime_scale(lo < 0)
        if etype in ("SECTOR_RALLY", "SECTOR_REGULATION"):
            sector = sector or str(self.rng.choice(SECTORS))
            targets = [k for k, s in self.state.stocks.items() if s.sector == sector]
            sectors = [sector]
            self.state.market.sector_sentiment[sector] = float(np.clip(
                self.state.market.sector_sentiment.get(sector, 0) + np.sign(base) * 0.4, -1, 1))
        elif etype == "LIQUIDITY_CRISIS":
            targets = list(self.state.stocks)
            sectors = list(SECTORS)
        else:
            targets = list(self.state.stocks)
            sectors = list(SECTORS)
        impacts = {}
        for k in targets:
            s = self.state.stocks[k]
            mult = s.beta if len(targets) > 3 else 1.0
            if etype == "LIQUIDITY_CRISIS" and s.sector in ("Banking", "Finance"):
                mult *= 1.8
            impacts[k] = base * mult * float(self.rng.uniform(0.75, 1.25))
            if "flow" in tpl:
                s.institutional_pressure = float(np.clip(s.institutional_pressure + tpl["flow"] * (s.beta / 1.2), -1, 1))
        ev = MarketEvent(
            id=self.state.next_id("EVT"), type=etype, category="market", severity=tpl["sev"],
            title=_fmt(str(self.rng.choice(tpl["headlines"])), sector=sector or ""),
            narrative=_fmt(tpl["body"], sector=sector or ""),
            affected_symbols=targets, affected_sectors=sectors, market_impact=round(base, 4), impacts=impacts,
            jump_fraction=0.35, vol_boost=tpl.get("vol", 0.0), duration_hours=tpl["hours"],
            remaining_hours=tpl["hours"], started_at=self.state.now,
        )
        self._apply(ev, in_session, jumps)
        self._news(ev, "MARKET")
        return ev

    # ------------------------------------------------------------------ #
    # Random generation
    # ------------------------------------------------------------------ #
    def _company_weights(self, s: StockState) -> dict[str, float]:
        sec = s.sector
        w = {
            "PRODUCT_LAUNCH": 0.8 + 3 * s.growth,
            "SHARE_BUYBACK": 0.3 + 2.5 * s.profitability,
            "PRODUCT_FAILURE": 0.5 + (1 - s.profitability * 3) * 0.4,
            "MAJOR_CONTRACT": 1.2 if sec in ("Infrastructure", "Defence", "Logistics", "Technology") else 0.3,
            "ACQUISITION": 0.35 + s.debt * 0.3,
            "FAILED_ACQUISITION": 0.12,
            "CEO_RESIGNATION": 0.25,
            "REGULATORY_INVESTIGATION": 0.6 if sec in ("Healthcare", "Finance", "Banking", "Telecom") else 0.2,
            "FACTORY_SHUTDOWN": 0.5 if sec in ("Automobile", "Healthcare", "Energy", "Infrastructure") else 0.05,
            "MANAGEMENT_SCANDAL": 0.06 + 0.12 * s.debt,
            "BREAKTHROUGH_TECH": 0.35 if sec in ("Technology", "Healthcare", "Energy", "Defence") else 0.03,
            "BROKER_UPGRADE": 1.3 + (0.6 if s.valuation < 0.4 else 0.0),
            "BROKER_DOWNGRADE": 1.1 + (0.6 if s.valuation > 0.7 else 0.0),
            "INSTITUTIONAL_ACCUMULATION": 0.8,
            "INSTITUTIONAL_DISTRIBUTION": 0.7,
        }
        return w

    def random_company_event(self, in_session: bool, jumps: dict[str, float]) -> MarketEvent:
        syms = list(self.state.stocks)
        sw = np.array([0.5 + self.state.stocks[k].event_sensitivity for k in syms])
        sym = syms[int(self.rng.choice(len(syms), p=sw / sw.sum()))]
        w = self._company_weights(self.state.stocks[sym])
        # Regime tilts the mix of good vs bad news
        tilt = {"BULL": 1.2, "STABLE": 1.0, "VOLATILE": 0.9, "BEAR": 0.8, "CRISIS": 0.6}[self.state.market.regime]
        for k in ("PRODUCT_LAUNCH", "MAJOR_CONTRACT", "BREAKTHROUGH_TECH", "BROKER_UPGRADE", "INSTITUTIONAL_ACCUMULATION",
                  "SHARE_BUYBACK"):
            w[k] *= tilt
        # Avoid stacking chains on the same stock
        if any(sc.kind == "CHAIN" and sc.symbol == sym and not sc.processed for sc in self.state.scheduled):
            for k in ("ACQUISITION", "REGULATORY_INVESTIGATION", "FACTORY_SHUTDOWN", "CEO_RESIGNATION"):
                w[k] = 0.0
        keys = list(w)
        p = np.array([w[k] for k in keys])
        etype = keys[int(self.rng.choice(len(keys), p=p / p.sum()))]
        return self.company_event(etype, sym, in_session, jumps)

    def random_market_or_macro(self, in_session: bool, jumps: dict[str, float], macro_only=False) -> MarketEvent:
        reg = self.state.market.regime
        macro_w = {"OIL_SPIKE": 0.7, "OIL_SLUMP": 0.7, "CURRENCY_SHOCK": 0.45, "GLOBAL_SELLOFF": 0.35,
                   "GLOBAL_RALLY": 0.7, "RECESSION_FEARS": 0.25, "RECOVERY_SIGNS": 0.5}
        mkt_w = {"SECTOR_RALLY": 1.3, "SECTOR_REGULATION": 0.6, "MARKET_SELLOFF": 0.5, "VOLATILITY_SPIKE": 0.5,
                 "INSTITUTIONAL_BUYING": 0.9, "INSTITUTIONAL_SELLING": 0.7, "LIQUIDITY_CRISIS": 0.0}
        if reg in ("BEAR", "CRISIS"):
            macro_w["GLOBAL_SELLOFF"] *= 2.5
            macro_w["RECESSION_FEARS"] *= 3
            mkt_w["MARKET_SELLOFF"] *= 2.5
            mkt_w["INSTITUTIONAL_SELLING"] *= 2
            mkt_w["LIQUIDITY_CRISIS"] = 0.25 if reg == "CRISIS" else 0.05
        elif reg == "BULL":
            macro_w["GLOBAL_RALLY"] *= 2
            mkt_w["INSTITUTIONAL_BUYING"] *= 2
            mkt_w["SECTOR_RALLY"] *= 1.5
        elif reg == "VOLATILE":
            mkt_w["VOLATILITY_SPIKE"] *= 3
        pool = {**{f"M:{k}": v for k, v in macro_w.items()}}
        if not macro_only:
            pool.update({f"K:{k}": v for k, v in mkt_w.items()})
        keys = list(pool)
        p = np.array([pool[k] for k in keys])
        pick = keys[int(self.rng.choice(len(keys), p=p / p.sum()))]
        kind, etype = pick.split(":")
        if kind == "M":
            return self.macro_event(etype, in_session, jumps)
        return self.market_event(etype, in_session, jumps)

    def hourly_random(self, jumps: dict[str, float]) -> list[MarketEvent]:
        """Spontaneous intraday events for one trading hour."""
        reg = REGIMES[self.state.market.regime]
        intensity = reg["event_rate"] * self.state.market.event_intensity
        out = []
        if self.rng.random() < 0.06 * intensity:
            out.append(self.random_company_event(True, jumps))
        if self.rng.random() < 0.015 * intensity:
            out.append(self.random_market_or_macro(True, jumps))
        return out

    def overnight_random(self, weekend: bool) -> list[MarketEvent]:
        """After-hours / weekend announcements. Impacts land as opening gaps."""
        reg = REGIMES[self.state.market.regime]
        intensity = reg["event_rate"] * self.state.market.event_intensity
        out: list[MarketEvent] = []
        jumps: dict[str, float] = {}
        if self.rng.random() < (0.22 if weekend else 0.30) * intensity:
            out.append(self.random_company_event(False, jumps))
        if self.rng.random() < (0.12 if weekend else 0.07) * intensity:
            out.append(self.random_market_or_macro(False, jumps, macro_only=True))
        return out

    # ------------------------------------------------------------------ #
    # Scheduled events
    # ------------------------------------------------------------------ #
    def process_scheduled(self, sch: ScheduledEvent, in_session: bool, jumps: dict[str, float]) -> dict:
        """Resolve a scheduled item. Returns a small result dict for the game engine."""
        sch.processed = True
        if sch.kind == "EARNINGS":
            return self._earnings(sch.symbol, in_session, jumps)
        if sch.kind == "ECON_DATA":
            return self._econ_release(sch, in_session, jumps)
        if sch.kind == "POLICY":
            return self._policy(in_session, jumps)
        if sch.kind == "CHAIN":
            self._chain_step(sch, in_session, jumps)
            return {"kind": "CHAIN"}
        if sch.kind == "HIDDEN":
            self.company_event(sch.payload["type"], sch.symbol, in_session, jumps)
            return {"kind": "HIDDEN"}
        return {"kind": sch.kind, "payload": sch.payload}

    def _earnings(self, sym: str, in_session: bool, jumps: dict[str, float]) -> dict:
        s = self.state.stocks[sym]
        score = 0.65 * s.earnings_quality + float(self.rng.normal(0, 0.45))
        if score > 0.25:
            outcome = "BEAT"
            impact = (0.025 + 0.05 * min(score, 1.2)) * (1.1 - 0.4 * s.valuation)
            headline = f"{s.name} reports earnings above expectations"
            body = f"Profit grew faster than the street expected; management raised full-year guidance."
        elif score < -0.25:
            outcome = "MISS"
            impact = -(0.02 + 0.045 * min(-score, 1.2)) * (0.7 + 0.5 * s.valuation)
            headline = f"{s.name} misses earnings estimates"
            body = f"Margins came in below forecasts and the outlook was cautious."
        else:
            outcome = "IN_LINE"
            impact = float(self.rng.normal(0, 0.012))
            headline = f"{s.name} results broadly in line with estimates"
            body = "No major surprises; commentary on demand was steady."
        impact *= self._regime_scale(impact < 0)
        s.eps *= 1 + s.growth / 4 + 0.04 * score
        s.fair_value *= math.exp(impact * 0.7)
        s.earnings_quality = float(np.clip(0.4 * s.earnings_quality + self.rng.normal(0, 0.45), -1, 1))
        ev = MarketEvent(
            id=self.state.next_id("EVT"), type=f"EARNINGS_{outcome}", category="company",
            severity=3 if outcome != "IN_LINE" else 1, title=headline, narrative=body,
            affected_symbols=[sym], affected_sectors=[s.sector], market_impact=round(impact, 4),
            impacts={sym: impact}, jump_fraction=0.75, vol_boost=0.5, duration_hours=8, remaining_hours=8,
            started_at=self.state.now,
        )
        self._apply(ev, in_session, jumps)
        self._news(ev, "COMPANY")
        return {"kind": "EARNINGS", "symbol": sym, "outcome": outcome, "impact": impact}

    def _econ_release(self, sch: ScheduledEvent, in_session: bool, jumps: dict[str, float]) -> dict:
        ind = sch.payload["indicator"]
        cons = sch.payload["consensus"]
        if ind == "CPI":
            actual, surprise = economy_engine.release_cpi(self.state, self.rng, cons)
            shocks = {"rates": surprise * 1.2}
            base = -0.012 * surprise
            if surprise >= 0.2:
                headline = f"Inflation surprise: CPI at {actual}% vs {cons}% expected"
                body = "Hotter-than-expected prices raise the odds of further rate hikes."
            elif surprise <= -0.2:
                headline = f"Inflation cools to {actual}%, below {cons}% forecast"
                body = "Softer prices open the door to rate cuts; rate-sensitive stocks rally."
            else:
                headline = f"CPI inflation at {actual}%, in line with forecasts"
                body = "The print does little to change the rate outlook."
        else:
            actual, surprise = economy_engine.release_gdp(self.state, self.rng, cons)
            shocks = {"global": surprise * 0.4}
            base = 0.008 * surprise
            if surprise >= 0.3:
                headline = f"GDP surprise: economy grows {actual}% vs {cons}% expected"
                body = "Strong domestic demand lifts earnings expectations for cyclicals."
            elif surprise <= -0.3:
                headline = f"Growth disappoints at {actual}%, below {cons}% forecast"
                body = "Economists cut forecasts; consumption and investment slowed."
            else:
                headline = f"GDP growth at {actual}%, close to estimates"
                body = "Growth momentum remains broadly stable."
        sch.payload["actual"] = actual
        impacts = {}
        for sym, s in self.state.stocks.items():
            sens = SECTOR_MACRO[s.sector]
            imp = base * s.beta + 0.01 * sum(sens.get(k, 0.0) * v for k, v in shocks.items())
            impacts[sym] = imp
        ev = MarketEvent(
            id=self.state.next_id("EVT"), type="INFLATION_SURPRISE" if ind == "CPI" else "GDP_SURPRISE",
            category="macro", severity=3 if abs(surprise) >= 0.2 else 1, title=headline, narrative=body,
            affected_symbols=list(impacts), affected_sectors=list(SECTORS), market_impact=round(base, 4),
            impacts=impacts, jump_fraction=0.7, duration_hours=8, remaining_hours=8, started_at=self.state.now,
        )
        self._apply(ev, in_session, jumps)
        self._news(ev, "MACRO")
        return {"kind": "ECON_DATA", "indicator": ind, "actual": actual, "consensus": cons, "surprise": surprise}

    def _policy(self, in_session: bool, jumps: dict[str, float]) -> dict:
        decision = economy_engine.policy_decision(self.state, self.rng)
        rate = self.state.market.economy.policy_rate
        if decision == "HIKE":
            headline, body, base, rs = (f"Central bank unexpectedly raises interest rates to {rate:.2f}%",
                                        "The committee cited sticky inflation. Borrowing costs will rise.", -0.012, 1.0)
        elif decision == "CUT":
            headline, body, base, rs = (f"Central bank cuts rates to {rate:.2f}% to support growth",
                                        "A surprise cut boosts rate-sensitive sectors.", 0.012, -1.0)
        else:
            headline, body, base, rs = (f"Central bank holds rates at {rate:.2f}%",
                                        "Policy stance unchanged; the governor sounded watchful on inflation.", 0.0, 0.0)
        impacts = {}
        for sym, s in self.state.stocks.items():
            impacts[sym] = base * s.beta + 0.015 * SECTOR_MACRO[s.sector]["rates"] * rs
        ev = MarketEvent(
            id=self.state.next_id("EVT"), type=f"RATE_{decision}", category="macro",
            severity=4 if decision != "HOLD" else 1, title=headline, narrative=body,
            affected_symbols=list(impacts), affected_sectors=list(SECTORS), market_impact=base,
            impacts=impacts, jump_fraction=0.7, vol_boost=0.3 if decision != "HOLD" else 0.0,
            duration_hours=8, remaining_hours=8, started_at=self.state.now,
        )
        self._apply(ev, in_session, jumps)
        self._news(ev, "MACRO")
        return {"kind": "POLICY", "decision": decision, "rate": rate}

    # ------------------------------------------------------------------ #
    # Active event effects
    # ------------------------------------------------------------------ #
    def active_effects(self) -> tuple[dict[str, float], dict[str, float], float]:
        """Per-hour drift, per-stock vol boost and market vol boost from active events; ages events."""
        drift: dict[str, float] = {}
        vboost: dict[str, float] = {}
        mkt_boost = 0.0
        for ev in self.state.events:
            if not ev.active:
                continue
            per_hour = (1 - ev.jump_fraction) / max(ev.duration_hours, 1)
            for sym, total in ev.impacts.items():
                drift[sym] = drift.get(sym, 0.0) + total * per_hour
                if ev.vol_boost:
                    vboost[sym] = max(vboost.get(sym, 0.0), ev.vol_boost)
            if ev.vol_boost and ev.category in ("macro", "market"):
                mkt_boost = max(mkt_boost, ev.vol_boost * 0.6)
            ev.remaining_hours -= 1
            if ev.remaining_hours <= 0:
                ev.active = False
        return drift, vboost, mkt_boost

    def pre_earnings_flow(self) -> None:
        """Informed positioning ahead of results: a subtle, observable pre-announcement drift."""
        now = self.state.now
        for sch in self.state.scheduled:
            if sch.kind == "EARNINGS" and not sch.processed and 0 < (sch.time - now).days <= 3:
                s = self.state.stocks[sch.symbol]
                s.institutional_pressure = float(np.clip(s.institutional_pressure + 0.12 * s.earnings_quality, -1, 1))
