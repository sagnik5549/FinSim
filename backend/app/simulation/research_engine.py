"""
Research desk — turns time into (noisy) information.

A QUICK look costs 1 working hour; a DEEP DIVE costs 3. Deep dives estimate
fair value more precisely, assess the next results and can uncover red flags
(e.g. an informed seller behind a block deal). Accuracy depends on the team.
"""
from __future__ import annotations

import math
from datetime import timedelta

import numpy as np

from app.simulation import team_engine
from app.simulation.state import GameState, ResearchReport

RESEARCH_HOURS = {"QUICK": 1, "DEEP": 3}

RED_FLAG_TEXT = {
    "EARNINGS_WARNING": "Channel checks show inventory piling up at distributors — guidance risk.",
    "REGULATORY_INVESTIGATION": "Unusual regulatory correspondence mentioned in recent filings.",
    "MANAGEMENT_SCANDAL": "Related-party transactions have grown sharply; governance concerns.",
    "PRODUCT_FAILURE": "Customer complaint volumes are spiking on consumer forums.",
}


def run_research(state: GameState, rng: np.random.Generator, symbol: str, depth: str) -> ResearchReport:
    s = state.stocks[symbol]
    skill = team_engine.research_skill(state)
    analyst = state.team["research_director"].name if depth == "DEEP" else state.team["senior_analyst"].name
    sigma = (0.11 if depth == "QUICK" else 0.05) * (1.35 - skill)
    est = s.fair_value * math.exp(rng.normal(0, sigma))
    upside = est / s.price - 1
    rating = "BUY" if upside > 0.07 else "SELL" if upside < -0.07 else "HOLD"
    confidence = float(np.clip(0.45 + skill * 0.4 + (0.12 if depth == "DEEP" else 0) - abs(rng.normal(0, 0.05)), 0.3, 0.95))

    notes: list[str] = []
    pe = s.price / s.eps
    notes.append(f"P/E {pe:.1f}x · growth {s.growth * 100:.0f}% · ROE proxy {s.profitability * 100:.0f}% · "
                 f"debt/assets {s.debt * 100:.0f}%.")
    if s.momentum > 0.004:
        notes.append("Price momentum is strong; the stock has been bid up recently.")
    elif s.momentum < -0.004:
        notes.append("The stock is in a short-term downtrend.")
    if s.institutional_pressure > 0.2:
        notes.append("Flow data suggests institutions are accumulating.")
    elif s.institutional_pressure < -0.2:
        notes.append("Flow data suggests institutions are distributing.")
    if s.debt > 0.55:
        notes.append("Leverage is high — vulnerable to rate hikes and credit events.")
    if s.valuation > 0.75:
        notes.append("Valuation is rich; disappointments would be punished.")

    earnings_view = None
    upcoming = [x for x in state.scheduled if x.kind == "EARNINGS" and x.symbol == symbol and not x.processed]
    if upcoming and (depth == "DEEP" or (upcoming[0].time - state.now) < timedelta(days=10)):
        est_q = s.earnings_quality + rng.normal(0, 0.55 * (1.25 - skill) * (0.7 if depth == "DEEP" else 1.2))
        view = "BEAT" if est_q > 0.2 else "MISS" if est_q < -0.2 else "IN LINE"
        earnings_view = f"Results on {upcoming[0].time.strftime('%d %b %H:%M')}: we lean {view}."

    red_flags: list[str] = []
    if depth == "DEEP":
        horizon = state.now + timedelta(days=14)
        for sch in state.scheduled:
            if sch.symbol == symbol and not sch.processed and sch.kind == "HIDDEN" and sch.time <= horizon:
                if rng.random() < 0.4 + 0.45 * skill:
                    red_flags.append(RED_FLAG_TEXT.get(sch.payload.get("type"), "Something doesn't add up in recent disclosures."))
        for sch in state.scheduled:
            if sch.symbol == symbol and not sch.processed and sch.kind == "CHAIN":
                if sch.payload.get("chain") == "ACQUISITION" and s.debt > 0.45:
                    red_flags.append("Acquisition financing looks stretched; credit agencies may react.")
                elif sch.payload.get("chain") == "REGULATORY":
                    red_flags.append("The regulatory probe is unresolved — binary outcome ahead.")
        for opp in state.opportunities:
            if opp.symbol == symbol and opp.status == "OPEN" and opp.informed_seller and rng.random() < 0.35 + 0.5 * skill:
                red_flags.append("The block seller appears unusually eager — they may know something.")
        red_flags = list(dict.fromkeys(red_flags))

    report = ResearchReport(
        id=state.next_id("RES"), symbol=symbol, time=state.now, depth=depth, analyst=analyst,
        est_fair_value=round(est, 2), price_at=s.price, rating=rating, confidence=round(confidence, 2),
        earnings_view=earnings_view, red_flags=red_flags, notes=notes,
    )
    state.research.append(report)
    state.research = state.research[-60:]
    state.stats.research_count += 1
    return report
