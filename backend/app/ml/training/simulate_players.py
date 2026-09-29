"""
Headless bot players -> labelled behaviour dataset + strategy balance report.

Four archetypes play full quarters through the real GameEngine (same rules,
same validation as a human). Every few days we snapshot the behaviour features
and label them with the bot's archetype. The same runs double as a fairness
check: different styles should produce different risk/return profiles with no
single dominant strategy.

    python -m app.ml.training.simulate_players --seeds 12 --out app/ml/training/data/behavior.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.ml.features import FEATURE_NAMES
from app.simulation import portfolio_engine as pe
from app.simulation import risk_engine as re_
from app.simulation.game_engine import ActionError, GameEngine
from app.simulation.time_engine import market_status

ARCHETYPES = ["CONSERVATIVE", "BALANCED", "AGGRESSIVE", "SPECULATIVE"]
DEFENSIVE = {"FMCG", "Healthcare", "Telecom", "Defence"}


class Bot:
    def __init__(self, style: str, rng: np.random.Generator):
        self.style = style
        self.rng = rng
        # Overlapping per-player parameters: styles differ in distribution, not in a single fixed signature.
        ranges = {"CONSERVATIVE": (0.35, 0.75), "BALANCED": (0.55, 0.92), "AGGRESSIVE": (0.78, 0.99), "SPECULATIVE": (0.6, 0.95)}
        self.invest = float(rng.uniform(*ranges[style]))
        self.comply = float({"CONSERVATIVE": rng.uniform(0.8, 1.0), "BALANCED": rng.uniform(0.6, 1.0),
                             "AGGRESSIVE": rng.uniform(0.3, 0.9), "SPECULATIVE": rng.uniform(0.0, 0.6)}[style])
        self.n_names = int({"CONSERVATIVE": rng.integers(7, 13), "BALANCED": rng.integers(6, 13),
                            "AGGRESSIVE": rng.integers(5, 9), "SPECULATIVE": rng.integers(2, 6)}[style])

    # -- popups ------------------------------------------------------------
    def handle_popups(self, eng: GameEngine) -> None:
        s = eng.state
        for _ in range(6):
            blocking = [p for p in s.popups if p.blocking]
            if not blocking:
                return
            p = blocking[0]
            if p.type == "RISK_WARNING":
                opts = p.payload["options"]
                r = self.rng.random()
                if r < self.comply:
                    choice = "REDUCE_EXPOSURE"
                elif r < self.comply + (1 - self.comply) / 2 and "REQUEST_EXCEPTION" in opts:
                    choice = "REQUEST_EXCEPTION"
                else:
                    choice = "IGNORE"
                try:
                    eng.resolve_risk(p.payload["warning_id"], choice)
                except ActionError:
                    eng.resolve_risk(p.payload["warning_id"], "IGNORE")
            else:
                eng.ack_popup(p.id)

    # -- helpers -----------------------------------------------------------
    def _buy_value(self, eng: GameEngine, sym: str, value: float) -> None:
        s = eng.state
        qty = int(min(value, s.portfolio.cash * 0.995) / (s.stocks[sym].price * 1.01))
        if qty > 0:
            try:
                eng.trade("BUY", sym, qty)
            except ActionError:
                pass
            self.handle_popups(eng)

    def _sell_all(self, eng: GameEngine, sym: str) -> None:
        h = eng.state.portfolio.holdings.get(sym)
        if h:
            try:
                eng.trade("SELL", sym, h.qty)
            except ActionError:
                pass
            self.handle_popups(eng)

    # -- decision per trading day -----------------------------------------
    def act(self, eng: GameEngine, day: int) -> None:
        s = eng.state
        if market_status(s.now) != "OPEN" or s.career.status != "ACTIVE":
            return
        nav = pe.nav(s)
        stocks = list(s.stocks.values())
        if self.style == "CONSERVATIVE":
            if day == 0:
                picks = sorted([x for x in stocks if x.sector in DEFENSIVE], key=lambda x: x.beta)[:max(3, self.n_names - 3)]
                picks += sorted([x for x in stocks if x.sector not in DEFENSIVE], key=lambda x: x.beta)[:3]
                for x in picks:
                    self._buy_value(eng, x.symbol, nav * self.invest / len(picks))
            elif day % 15 == 7 and self.rng.random() < 0.5:
                sym = str(self.rng.choice([x.symbol for x in stocks if x.sector in DEFENSIVE]))
                eng.research(sym, "QUICK") if s.now.hour <= 15 else None
                self.handle_popups(eng)
        elif self.style == "BALANCED":
            if day == 0:
                for x in self.rng.choice(stocks, self.n_names, replace=False):
                    self._buy_value(eng, x.symbol, nav * self.invest / self.n_names)
            elif day % 5 == 0:
                if s.now.hour <= 14 and self.rng.random() < 0.6:
                    x = self.rng.choice(stocks)
                    try:
                        rep = eng.research(x.symbol, "QUICK")["report"]
                        self.handle_popups(eng)
                        if rep["rating"] == "BUY" and s.portfolio.cash > nav * 0.1:
                            eng.record_thesis(x.symbol, "BULLISH", "Research suggests upside.")
                            self._buy_value(eng, x.symbol, nav * 0.05)
                        elif rep["rating"] == "SELL":
                            self._sell_all(eng, x.symbol)
                    except ActionError:
                        pass
        elif self.style == "AGGRESSIVE":
            # Fully invested in high-beta growth names near the single-stock limit; cut losers, replace them.
            ranked = sorted(stocks, key=lambda x: x.beta + 2 * x.growth, reverse=True)
            if day == 0:
                for x in ranked[:self.n_names]:
                    self._buy_value(eng, x.symbol, nav * self.invest / self.n_names)
            elif day % 2 == 0:
                for sym, h in list(s.portfolio.holdings.items()):
                    if s.stocks[sym].price < h.avg_cost * 0.92:
                        self._sell_all(eng, sym)
                spare = [x for x in ranked if x.symbol not in s.portfolio.holdings]
                while s.portfolio.cash > pe.nav(s) * (1.05 - self.invest) and spare:
                    self._buy_value(eng, spare.pop(0).symbol, pe.nav(s) * self.invest / self.n_names)
        else:  # SPECULATIVE
            recent = [n for n in s.news[-6:] if n.category == "COMPANY" and n.symbols]
            for n in recent:
                sym = n.symbols[0]
                if n.tone == "POSITIVE" and s.portfolio.cash > nav * (1 - self.invest):
                    self._buy_value(eng, sym, nav * float(self.rng.uniform(0.1, 0.3)))
                elif n.tone == "NEGATIVE":
                    self._sell_all(eng, sym)
            for o in s.opportunities:
                if o.status == "OPEN" and s.portfolio.cash > o.qty * o.price:
                    try:
                        eng.accept_opportunity(o.id)
                    except ActionError:
                        pass
                    self.handle_popups(eng)
            if day == 0:
                for x in self.rng.choice(stocks, self.n_names, replace=False):
                    self._buy_value(eng, x.symbol, nav * self.invest / self.n_names)


def play(style: str, seed: int, checkpoint_every: int = 4) -> tuple[list[dict], dict]:
    eng = GameEngine.new_game(f"bot-{style}-{seed}", seed=seed)
    bot = Bot(style, np.random.default_rng(seed * 31 + ARCHETYPES.index(style)))
    rows: list[dict] = []
    day = 0
    s = eng.state
    while s.career.status == "ACTIVE" and day < 120:
        bot.handle_popups(eng)
        # intraday: bots act once in the morning and (speculative) again after lunch
        bot.act(eng, day)
        bot.handle_popups(eng)
        if s.career.status != "ACTIVE":
            break
        if style == "SPECULATIVE" and market_status(s.now) == "OPEN":
            try:
                eng.advance("hours", 4)
            except ActionError:
                pass
            bot.handle_popups(eng)
            bot.act(eng, day + 1000)
            bot.handle_popups(eng)
        try:
            eng.advance("next_day")
        except ActionError:
            bot.handle_popups(eng)
            continue
        day += 1
        if day % checkpoint_every == 0 and day >= 6:
            from app.ml.features import extract
            f = extract(s)
            rows.append({**f, "label": style, "seed": seed, "day": day})
    review = s.career.last_review or {}
    result = {"style": style, "seed": seed, "return": review.get("return_pct", pe.nav(s) / 1e9 - 1),
              "max_drawdown": s.portfolio.max_drawdown, "outcome": review.get("outcome", s.career.status),
              "trades": s.stats.trades, "risk_score": re_.assess(s).score}
    return rows, result


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--start-seed", type=int, default=1000)
    ap.add_argument("--out", default=str(Path(__file__).parent / "data" / "behavior.csv"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    all_rows, results = [], []
    t0 = time.time()
    for i in range(args.seeds):
        seed = args.start_seed + i
        for style in ARCHETYPES:
            rows, res = play(style, seed)
            all_rows += rows
            results.append(res)
        print(f"seed {seed} done ({time.time() - t0:.0f}s)", file=sys.stderr)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FEATURE_NAMES + ["label", "seed", "day"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nwrote {len(all_rows)} rows -> {out}")
    print("\nSTRATEGY BALANCE (same seeds for every style)")
    print(f"{'style':14s} {'mean ret':>9s} {'sd':>7s} {'P(>=12%)':>9s} {'mean MDD':>9s} {'promoted':>9s} {'terminated':>11s}")
    by = defaultdict(list)
    for r in results:
        by[r["style"]].append(r)
    for style in ARCHETYPES:
        rs = by[style]
        rets = [r["return"] for r in rs]
        print(f"{style:14s} {statistics.mean(rets):+9.2%} {statistics.pstdev(rets):7.2%} "
              f"{sum(x >= 0.12 for x in rets) / len(rets):9.0%} {statistics.mean(r['max_drawdown'] for r in rs):9.2%} "
              f"{sum(r['outcome'] == 'PROMOTED' for r in rs):9d} {sum(r['outcome'] == 'TERMINATED' for r in rs):11d}")


if __name__ == "__main__":
    main()
