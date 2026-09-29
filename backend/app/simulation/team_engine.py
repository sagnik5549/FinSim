"""
Characters and employees.

Every character is fictional and represented by an illustrated avatar on the
frontend. Their skills have concrete gameplay effects:

  research_director / senior_analyst  -> research accuracy and red-flag detection
  trader                              -> lower market impact on execution
  risk_manager                        -> exception approvals, early near-limit alerts
  economist                           -> better macro forecasts in the calendar
  compliance                          -> softer penalties for documentation lapses
"""
from __future__ import annotations

import numpy as np

from app.simulation.state import Character, GameState

CORE_TEAM = [
    ("ceo", "Vikram Sethi", "Chief Executive Officer", "ceo", {"leadership": 88, "patience": 45},
     "Demanding and results-driven. Rewards conviction, punishes surprises."),
    ("cfo", "Ananya Rao", "Chief Financial Officer", "cfo", {"finance": 84, "patience": 70},
     "Precise and numbers-first. Cares about drawdowns more than headlines."),
    ("risk_manager", "Farhan Qureshi", "Chief Risk Officer", "risk", {"risk": 80, "negotiation": 55},
     "Cautious, principled. Remembers who ignored his warnings."),
    ("research_director", "Meera Iyer", "Research Director", "research", {"research": 78, "valuation": 74},
     "Curious and contrarian. Loves a mispriced balance sheet."),
    ("senior_analyst", "Kabir Anand", "Senior Analyst", "analyst", {"research": 68, "quant": 72},
     "Fast, quantitative, occasionally overconfident."),
    ("trader", "Rohan D'Souza", "Head Trader", "trader", {"execution": 70, "market_knowledge": 76},
     "Knows the tape. Splits big orders to limit market impact."),
    ("economist", "Dr. Leela Krishnan", "Chief Economist", "economist", {"macro": 74, "forecasting": 70},
     "Measured and data-driven. Rarely wrong for long."),
    ("compliance", "Suresh Pillai", "Compliance Officer", "compliance", {"compliance": 82, "negotiation": 50},
     "By-the-book. Insists every large trade is documented."),
    ("hr", "Nandini Bose", "HR Manager", "hr", {"people": 80, "negotiation": 65},
     "Warm but firm. Believes rested people make better decisions."),
]

CANDIDATE_FIRST = ["Aarav", "Ishita", "Dev", "Priya", "Arjun", "Sana", "Vihaan", "Tara", "Neel", "Zoya", "Kiran", "Rhea"]
CANDIDATE_LAST = ["Kapoor", "Menon", "Shah", "Gupta", "Reddy", "Bhatt", "Chawla", "Nair", "Joshi", "Das", "Varma", "Sen"]
CANDIDATE_ROLES = [
    ("Junior Analyst", "analyst", ["research", "quant"]),
    ("Quant Analyst", "analyst", ["quant", "research"]),
    ("Risk Analyst", "risk", ["risk_awareness", "quant"]),
    ("Execution Trader", "trader", ["execution", "market_knowledge"]),
    ("Portfolio Manager", "analyst", ["market_knowledge", "risk_awareness"]),
]


def create_team(rng: np.random.Generator) -> dict[str, Character]:
    team = {}
    for cid, name, role, avatar, skills, personality in CORE_TEAM:
        jittered = {k: int(np.clip(v + rng.normal(0, 5), 20, 99)) for k, v in skills.items()}
        team[cid] = Character(
            id=cid, name=name, role=role, avatar=avatar, skills=jittered,
            trust=float(np.clip(rng.normal(60, 6), 35, 85)), loyalty=float(np.clip(rng.normal(65, 8), 30, 95)),
            stress=float(np.clip(rng.normal(25, 6), 5, 60)), performance=float(np.clip(rng.normal(65, 8), 30, 95)),
            personality=personality, core=True,
        )
    return team


def candidates(state: GameState) -> list[dict]:
    """Deterministic recruitment pool for the current quarter (hiring unlocks at level 2)."""
    rng = np.random.default_rng(state.seed * 7 + state.career.quarter_index)
    out = []
    for i in range(6):
        title, avatar, focus = CANDIDATE_ROLES[int(rng.integers(0, len(CANDIDATE_ROLES)))]
        skills = {k: int(np.clip(rng.normal(58, 12), 25, 95)) for k in
                  ("research", "quant", "risk_awareness", "market_knowledge", "negotiation", "execution")}
        for f in focus:
            skills[f] = int(np.clip(skills[f] + 18, 25, 99))
        exp_years = int(rng.integers(1, 15))
        salary = round(18 + sum(skills.values()) / 6 * 0.9 + exp_years * 3.5, 1)
        out.append({
            "id": f"cand-{state.career.quarter_index}-{i}",
            "name": f"{CANDIDATE_FIRST[int(rng.integers(0, 12))]} {CANDIDATE_LAST[int(rng.integers(0, 12))]}",
            "role": title, "avatar": avatar, "skills": skills, "experience": exp_years,
            "loyalty": int(np.clip(rng.normal(60, 12), 20, 95)), "salary_lakh": salary,
        })
    return out


def research_skill(state: GameState) -> float:
    rd = state.team.get("research_director")
    sa = state.team.get("senior_analyst")
    vals = [c.skills.get("research", 50) for c in (rd, sa) if c]
    hired = [c.skills.get("research", 0) for c in state.team.values() if not c.core and "research" in c.skills]
    best = max(vals + hired) if (vals or hired) else 50
    avg = sum(vals) / len(vals) if vals else 50
    return (0.6 * best + 0.4 * avg) / 100


def adjust(state: GameState, cid: str, trust: float = 0.0, stress: float = 0.0, performance: float = 0.0) -> None:
    c = state.team.get(cid)
    if not c:
        return
    c.trust = float(np.clip(c.trust + trust, 0, 100))
    c.stress = float(np.clip(c.stress + stress, 0, 100))
    c.performance = float(np.clip(c.performance + performance, 0, 100))


def daily_update(state: GameState, drawdown: float, open_breaches: int) -> None:
    """Stress rises with drawdowns and unresolved breaches; relaxes otherwise."""
    for c in state.team.values():
        target = 20 + drawdown * 250 + open_breaches * 8
        if c.id in ("risk_manager", "cfo"):
            target += drawdown * 150
        c.stress = float(np.clip(c.stress + 0.25 * (target - c.stress), 0, 100))
        c.performance = float(np.clip(c.performance + 0.05 * (70 - c.stress) * 0.1, 20, 99))
