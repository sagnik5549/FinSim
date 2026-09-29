"""
Train and evaluate the player-behaviour classifier offline.

    python -m app.ml.training.train_behavior [--model gbm|xgb] [--data ...]

Splits by seed (grouped) so the test set contains unseen market paths, reports
accuracy / per-class metrics / confusion matrix against the rule-based
baseline, prints feature importance (SHAP if installed, permutation otherwise)
and saves a joblib bundle that app.ml.inference picks up automatically.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from app.ml.behavior_model import LABELS, RuleBasedBehaviorModel
from app.ml.features import FEATURE_NAMES
from app.ml.inference import BEHAVIOR_ARTIFACT


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(Path(__file__).parent / "data" / "behavior.csv"))
    ap.add_argument("--model", choices=["gbm", "xgb"], default="gbm")
    ap.add_argument("--out", default=str(BEHAVIOR_ARTIFACT))
    args = ap.parse_args(argv)

    df = pd.read_csv(args.data)
    seeds = sorted(df["seed"].unique())
    test_seeds = set(seeds[:: 4])  # ~25% of market paths held out
    train, test = df[~df["seed"].isin(test_seeds)], df[df["seed"].isin(test_seeds)]
    Xtr, ytr = train[FEATURE_NAMES].values, train["label"].map(LABELS.index).values
    Xte, yte = test[FEATURE_NAMES].values, test["label"].map(LABELS.index).values
    print(f"train rows {len(train)} · test rows {len(test)} · held-out seeds {sorted(test_seeds)}")

    if args.model == "xgb":
        from xgboost import XGBClassifier  # optional dependency
        model = XGBClassifier(n_estimators=250, max_depth=4, learning_rate=0.08, subsample=0.9,
                              colsample_bytree=0.9, eval_metric="mlogloss")
        kind = "xgboost"
    else:
        model = GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.08, random_state=0)
        kind = "sklearn-gbm"
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    acc = accuracy_score(yte, pred)

    rules = RuleBasedBehaviorModel()
    rule_pred = [LABELS.index(rules.predict(dict(zip(FEATURE_NAMES, row)))[0]) for row in Xte]
    rule_acc = accuracy_score(yte, rule_pred)

    print(f"\nmodel accuracy {acc:.3f}  vs rule-based baseline {rule_acc:.3f}\n")
    print(classification_report(yte, pred, target_names=LABELS, digits=3, zero_division=0))
    print("confusion matrix (rows=true, cols=pred):")
    print(pd.DataFrame(confusion_matrix(yte, pred, labels=range(len(LABELS))), index=LABELS, columns=LABELS))

    try:
        import shap  # optional
        explainer = shap.TreeExplainer(model) if kind == "xgboost" else shap.Explainer(model.predict_proba, Xtr[:200])
        sv = explainer(Xte[:300])
        imp = np.abs(sv.values).mean(axis=tuple(i for i in range(sv.values.ndim) if i != 1))
        method = "mean |SHAP|"
    except Exception:
        r = permutation_importance(model, Xte, yte, n_repeats=8, random_state=0)
        imp, method = r.importances_mean, "permutation importance"
    print(f"\nfeature importance ({method}):")
    for name, v in sorted(zip(FEATURE_NAMES, imp), key=lambda kv: -kv[1]):
        print(f"  {name:20s} {v:.4f}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if acc < rule_acc:
        print(f"\nNOT deploying: model ({acc:.3f}) does not beat the rule baseline ({rule_acc:.3f}).")
        return
    joblib.dump({"model": model, "labels": LABELS, "features": FEATURE_NAMES, "kind": kind,
                 "metrics": {"accuracy": acc, "rule_baseline": rule_acc, "test_rows": len(test)}}, out)
    print(f"\nsaved -> {out}  (the game loads it automatically; delete it to fall back to rules)")


if __name__ == "__main__":
    main()
