"""Portfolio, trading, research, risk, news/events, career, team, performance and leave routes."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

import numpy as np
from fastapi import APIRouter, Depends, Query

from app.api.deps import game_id_header
from app.schemas.requests import (
    AcceptOpportunityRequest,
    HireRequest,
    LeaveRequest,
    QuoteRequest,
    ResearchRequest,
    ResolveRiskRequest,
    ThesisRequest,
    TradeRequest,
)
from app.services import game_service as svc
from app.services import repository as repo
from app.services import serializers as ser
from app.simulation import career_engine as ce
from app.simulation import team_engine
from app.simulation.constants import CAREER_LEVELS

portfolio = APIRouter()
trade = APIRouter()
research = APIRouter()
risk = APIRouter()
news = APIRouter()
events = APIRouter()
career = APIRouter()
team = APIRouter()
performance = APIRouter()
leave = APIRouter()
opportunities = APIRouter()


# ---------------------------------------------------------------- portfolio
@portfolio.get("")
def get_portfolio(game_id: str = Depends(game_id_header)):
    return svc.read(game_id, lambda s: {"summary": ser.portfolio_summary(s), "holdings": ser.holdings(s),
                                        "risk": ser.risk_summary(s),
                                        "transactions": [t.model_dump(mode="json") for t in reversed(s.transactions)]})


# ---------------------------------------------------------------- trading
@trade.post("/quote")
def quote(req: QuoteRequest, game_id: str = Depends(game_id_header)):
    from app.simulation.game_engine import GameEngine
    return svc.read(game_id, lambda s: GameEngine(s).quote(req.side, req.symbol.upper(), req.quantity))


@trade.post("/buy")
def buy(req: TradeRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.trade("BUY", req.symbol, req.quantity))


@trade.post("/sell")
def sell(req: TradeRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.trade("SELL", req.symbol, req.quantity))


# ---------------------------------------------------------------- opportunities
@opportunities.post("/{opp_id}/accept")
def accept(opp_id: str, req: AcceptOpportunityRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.accept_opportunity(opp_id, req.quantity))


@opportunities.post("/{opp_id}/decline")
def decline(opp_id: str, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.decline_opportunity(opp_id))


# ---------------------------------------------------------------- research
@research.post("/thesis")
def thesis(req: ThesisRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.record_thesis(req.symbol, req.stance, req.text))


@research.post("/{symbol}")
def run_research(symbol: str, req: ResearchRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.research(symbol, req.depth))


# ---------------------------------------------------------------- risk
@risk.get("")
def get_risk(game_id: str = Depends(game_id_header)):
    return svc.read(game_id, ser.risk_summary)


@risk.post("/resolve")
def resolve(req: ResolveRiskRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.resolve_risk(req.warning_id, req.action))


# ---------------------------------------------------------------- news & events
@news.get("")
def get_news(limit: int = Query(60, ge=1, le=300), symbol: str | None = None, game_id: str = Depends(game_id_header)):
    with svc.session() as db:
        rows = repo.news(db, game_id, limit, symbol.upper() if symbol else None)
        return [{"id": r.news_id, "time": r.t.isoformat(), "headline": r.headline, "body": r.body,
                 "category": r.category, "tone": r.tone, "severity": r.severity,
                 "symbols": [x for x in r.symbols.split(",") if x]} for r in rows]


@events.get("")
def get_events(game_id: str = Depends(game_id_header)):
    def build(s):
        return {
            "active": [{"id": e.id, "type": e.type, "category": e.category, "title": e.title, "severity": e.severity,
                        "narrative": e.narrative, "started_at": e.started_at.isoformat(),
                        "symbols": e.affected_symbols[:6] if e.category == "company" else [],
                        "sectors": e.affected_sectors if e.category != "macro" else [],
                        "remaining_hours": e.remaining_hours} for e in reversed(s.events) if e.active],
            "recent": [{"id": e.id, "type": e.type, "category": e.category, "title": e.title, "severity": e.severity,
                        "started_at": e.started_at.isoformat()} for e in reversed(s.events[-40:])],
            "calendar": ser.calendar(s, limit=40),
        }
    return svc.read(game_id, build)


# ---------------------------------------------------------------- career
@career.get("")
def get_career(game_id: str = Depends(game_id_header)):
    def build(s):
        c = s.career
        prog = ce.target_progress(s)
        port = ser.portfolio_summary(s)
        reqs = [
            {"label": f"Return ≥ {c.target_return * 100:.0f}%", "value": port["return_pct"], "met": port["return_pct"] >= c.target_return},
            {"label": f"Max drawdown ≤ {c.max_drawdown_limit * 100:.0f}%", "value": port["max_drawdown"],
             "met": port["max_drawdown"] <= c.max_drawdown_limit},
            {"label": "Reputation ≥ 55", "value": c.reputation, "met": c.reputation >= 55},
            {"label": "No more than 1 ignored risk breach", "value": c.ignored_violations, "met": c.ignored_violations <= 1},
            {"label": "Compliance strikes ≤ 2", "value": c.compliance_strikes, "met": c.compliance_strikes <= 2},
        ]
        return {
            **ser.career(s), "target_progress": prog, "promotion_requirements": reqs,
            "history": [h.model_dump() for h in c.history], "achievements": c.achievements,
            "decisions": list(reversed(c.decisions))[:30], "last_review": c.last_review,
            "ladder": [{"level": k, "title": v["title"], "unlocks": v["unlocks"], "target_return": v["target_return"],
                        "max_drawdown": v["max_drawdown"]} for k, v in CAREER_LEVELS.items()],
        }
    return svc.read(game_id, build)


# ---------------------------------------------------------------- team
@team.get("")
def get_team(game_id: str = Depends(game_id_header)):
    def build(s):
        return {"members": ser.team(s), "hiring_unlocked": s.career.level >= 2,
                "candidates": team_engine.candidates(s),
                "delegation": CAREER_LEVELS[s.career.level]["delegate"],
                "research_quality": round(team_engine.research_skill(s) * 100)}
    return svc.read(game_id, build)


@team.post("/hire")
def hire(req: HireRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.hire(req.candidate_id))


# ---------------------------------------------------------------- performance
@performance.get("")
def get_performance(game_id: str = Depends(game_id_header)):
    def build(s):
        p = s.portfolio
        port = ser.portfolio_summary(s)
        bench_ret = s.indices["BH50"].value / p.quarter_start_bench - 1
        q_start = s.career.quarter_start.isoformat()
        closed = [t for t in s.stats.closed_trades if t["t"] >= q_start]
        pnls = [t["pnl"] for t in closed]
        wins = [x for x in pnls if x > 0]
        daily = [d for d in p.daily if d.date >= q_start[:10]]
        dr = [d.close_nav / d.open_nav - 1 for d in daily if d.open_nav]
        # Sector attribution: realised (this quarter) + unrealised P&L by sector
        attr: dict[str, float] = defaultdict(float)
        for t in closed:
            attr[s.stocks[t["symbol"]].sector] += t["pnl"]
        for h in s.portfolio.holdings.values():
            attr[s.stocks[h.symbol].sector] += h.qty * (s.stocks[h.symbol].price - h.avg_cost)
        monthly: dict[str, dict] = {}
        for d in p.daily:
            mth = d.date[:7]
            mm = monthly.setdefault(mth, {"month": mth, "start": d.open_nav, "end": d.close_nav,
                                          "bench_start": d.bench_open, "bench_end": d.bench_close})
            mm["end"], mm["bench_end"] = d.close_nav, d.bench_close
        months = [{"month": v["month"], "return": v["end"] / v["start"] - 1,
                   "benchmark": v["bench_end"] / v["bench_start"] - 1} for v in monthly.values()]
        sharpe = (np.mean(dr) / np.std(dr) * np.sqrt(252)) if len(dr) >= 10 and np.std(dr) > 0 else None
        return {
            "portfolio_return": port["return_pct"], "benchmark_return": bench_ret, "alpha": port["return_pct"] - bench_ret,
            "max_drawdown": p.max_drawdown, "risk_score": ser.risk_summary(s)["score"], "volatility": port["volatility"],
            "sharpe": sharpe, "win_rate": len(wins) / len(pnls) if pnls else None,
            "average_trade": float(np.mean(pnls)) if pnls else None,
            "best_trade": max(closed, key=lambda t: t["pnl"]) if closed else None,
            "worst_trade": min(closed, key=lambda t: t["pnl"]) if closed else None,
            "closed_trades": len(closed), "fees_paid": p.fees_paid,
            "sector_attribution": dict(sorted(attr.items(), key=lambda kv: -kv[1])),
            "monthly": months,
            "quarterly": [h.model_dump() for h in s.career.history],
            "target": {"target": s.career.target_value, "actual": port["value"], "difference": port["value"] - s.career.target_value,
                       "target_return": s.career.target_return, "actual_return": port["return_pct"]},
            "daily": [{"date": d.date, "nav": d.close_nav, "bench": d.bench_close} for d in daily],
            "nav_series": [{"t": x.t.isoformat(), "nav": x.nav, "bench": x.bench} for x in p.hourly_nav],
        }
    return svc.read(game_id, build)


# ---------------------------------------------------------------- leave
@leave.get("")
def get_leave(game_id: str = Depends(game_id_header)):
    return svc.read(game_id, lambda s: ser.full_state(s, include_paths=False)["leave"])


@leave.post("/start")
def start_leave(req: LeaveRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.take_leave(req.days))
