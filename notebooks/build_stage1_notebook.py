"""Builds notebooks/06_stage1_model.ipynb. Run: python notebooks/build_stage1_notebook.py"""
import nbformat as nbf
from pathlib import Path
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# 06 · Stage 1 model: baseline, logistic regression, XGBoost

Predicts, on the invoice date, whether an invoice will be paid more than 3 calendar days late (Dataset A, 50k invoices).

**What this notebook does and doesn't do**
- Uses **only the training period** (invoices before October 1, 2019). The test set is scored once, later, by the Evaluator (`specs/agents/evaluator.md`).
- Compares three models with scikit-learn's `TimeSeriesSplit`: the "late last time" rule, logistic regression, XGBoost.
- Each fold trains only on invoices **paid before** the fold's first validation date, as in real life.
- Logs every run to MLflow, then trains the final models and saves them for the app and the Evaluator.

All logic is in `src/model/train.py`, which the SageMaker Pipeline will also run."""),
code("""import sys; sys.path.insert(0, "..")
import json, os, joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from src.data.load import load_a, CUT_A, SHA_A
from src.model import train as T
from src.model import tracking

PATH_A = "../data/raw/customer_invoices.csv"
os.makedirs("../models", exist_ok=True)
tracking.setup(root="..")"""),
md("## 1. Data and features (specs/features.md, approved G2)"),
code("""a = T.stage1_frame(load_a(PATH_A))
train = a[a["set"] == "train"].copy()
known = T.known_by(train, CUT_A)
print(f"Training invoices: {len(train):,}   paid before Oct 1, 2019 (usable as labels): {len(known):,}")
print(f"Left out because they were paid on or after Oct 1 (outcome not yet known then): {len(train) - len(known):,}")
print(f"Late rate in usable training invoices: {known['late'].mean():.3f}")"""),
md("""## 2. Rolling validation inside the training period

Five time-ordered folds. Each trains on everything before a point (only invoices already paid) and validates on the next block."""),
code("""results, last_valid = T.rolling_validation(train)
summary = results.groupby("model")[["auc", "pr_auc", "top20_capture", "brier", "mean_pred", "actual_rate"]].mean().round(3)
summary"""),
code("""results.pivot(index="fold", columns="model", values="auc").round(3)"""),
md("""**How to read it**
- **AUC:** how well the model ranks late invoices above on-time ones. 0.5 is a coin toss.
- **PR-AUC:** precision across all cut-offs. It matters because only about 15% of invoices are late; the baseline rate is about 0.15.
- **Top-20% capture:** if the team works only the riskiest 20% of invoices, the share of all late invoices they reach. A random pick reaches 20%.

Fold 1 trains on very few invoices, so the later folds are the more realistic ones."""),
md("## 3. Charts"),
code("""sns.set_theme(style="white", font_scale=0.95)
COL = {"baseline": "#9aa3ad", "logistic": "#7fb3f0", "xgboost": "#2a6fdb"}
NAMES = {"baseline": "Late last time (rule)", "logistic": "Logistic regression", "xgboost": "XGBoost"}
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6), dpi=150)

for m in ["baseline", "logistic", "xgboost"]:
    r = results[results["model"] == m]
    ax[0].plot(r["fold"], r["auc"], marker="o", color=COL[m], lw=2, label=NAMES[m])
ax[0].set_title("1. AUC by fold (later folds = more history)", loc="left", fontweight="bold")
ax[0].set_xticks(range(1, 6)); ax[0].set_xlabel("TimeSeriesSplit fold"); ax[0].set_ylabel("AUC"); ax[0].set_ylim(0.5, 1); ax[0].legend(frameon=False, loc="lower right")

y = last_valid["late"].to_numpy()
for m in ["baseline", "logistic", "xgboost"]:
    order = np.argsort(-last_valid[m].to_numpy(), kind="stable")
    caught = np.cumsum(y[order]) / y.sum()
    ax[1].plot(np.arange(1, len(y) + 1) / len(y) * 100, caught * 100, color=COL[m], lw=2, label=NAMES[m])
ax[1].plot([0, 100], [0, 100], ls=":", c="k", lw=1, label="Random")
ax[1].axvline(20, ls="--", c="k", lw=1)
ax[1].set_title("2. Late invoices caught vs invoices worked (fold 5)", loc="left", fontweight="bold")
ax[1].set_xlabel("Share of invoices worked, riskiest first (%)"); ax[1].set_ylabel("Share of late invoices caught (%)")
ax[1].legend(frameon=False, loc="lower right")

cap = results[results["fold"] == 5].set_index("model")["top20_capture"].reindex(["baseline", "logistic", "xgboost"]) * 100
ax[2].bar([NAMES[m] for m in cap.index], cap.values, color=[COL[m] for m in cap.index])
for i, v in enumerate(cap.values):
    ax[2].text(i, v + 1.5, f"{v:.0f}%", ha="center", fontweight="bold")
ax[2].axhline(20, ls=":", c="k", lw=1)
ax[2].set_title("3. Working the top 20% catches... (fold 5)", loc="left", fontweight="bold")
ax[2].set_ylabel("Share of late invoices caught (%)"); ax[2].set_ylim(0, 100)
ax[2].tick_params(axis="x", labelsize=9)
sns.despine(fig); fig.tight_layout()
fig.savefig("../docs/img/stage1_validation.png")
plt.show()"""),
md("""## 4. Fairness check on the last validation fold (D-022)

Flag the riskiest 20%, then compare each group's **false-alarm rate** (on-time invoices wrongly flagged) to the overall rate. Rule: no group above **1.25 times** the overall rate, unless that group really is late more often (its late rate is above the overall rate too)."""),
code("""def fairness(model, group):
    g = T.group_rates(last_valid, model, group)
    g["check"] = np.where((g["false_alarm_ratio"] > 1.25) & (g["late_rate"] <= g.loc["ALL", "late_rate"]), "REVIEW", "ok")
    return g.round(3)

fairness("xgboost", "business_code")"""),
code("""fairness("xgboost", "hist_group")"""),
code("""fairness("logistic", "business_code")"""),
md("""## 5. Train the final models and log everything to MLflow

Final models are trained on all training invoices paid before October 1, 2019. The validation results above are what gets logged as their expected performance. The test set is still untouched."""),
code("""final = {}
for kind in ["logistic", "xgboost"]:
    model, _, extra = T.fit_predict(kind, known, known.head(1))
    path = f"../models/stage1_{kind}.joblib"
    joblib.dump({"model": model, "numeric": T.NUMERIC_STAGE1, "categorical": T.CATEGORICAL_STAGE1, **extra}, path)
    m = results[results["model"] == kind][["auc", "pr_auc", "top20_capture"]].mean()
    card = {"model": f"stage1_{kind}", "data_sha256": SHA_A, "trained_on": "Dataset A invoices before 2019-10-01, paid before 2019-10-01",
            "rows": len(known), "late_rate": float(known["late"].mean()), "inputs": T.NUMERIC_STAGE1 + T.CATEGORICAL_STAGE1,
            "validation": {k: round(float(v), 4) for k, v in m.items()}, "test_set": "not used"}
    json.dump(card, open(path.replace(".joblib", ".json"), "w"), indent=2)
    params = T.XGB_PARAMS if kind == "xgboost" else {"C": 1.0, "class_weight": "none", "min_frequency": 20}
    run_id = tracking.log_run(f"stage1_{kind}", {**params, "rows": len(known)},
                              {f"cv_{k}": v for k, v in m.items()}, artifacts=[path], card=card)
    final[kind] = run_id
base = results[results["model"] == "baseline"][["auc", "pr_auc", "top20_capture"]].mean()
final["baseline"] = tracking.log_run("stage1_baseline", {"rule": "late last time"}, {f"cv_{k}": v for k, v in base.items()})
final"""),
md("""## 6. What the models rely on (XGBoost importance, by total gain)

Per-invoice reasons in plain words come from SHAP in the app; this is the overall picture."""),
code("""xgb = joblib.load("../models/stage1_xgboost.joblib")["model"]
imp = pd.Series(xgb.get_booster().get_score(importance_type="total_gain")).sort_values(ascending=False)
(imp / imp.sum()).round(3).rename("share_of_gain").to_frame()"""),
md("""To browse every run: in the repo folder, run `mlflow ui --backend-store-uri sqlite:///mlflow.db` and open http://127.0.0.1:5000."""),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
nbf.write(nb, Path(__file__).with_name("06_stage1_model.ipynb")); print("wrote")
