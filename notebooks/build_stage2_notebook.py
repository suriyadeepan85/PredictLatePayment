"""Builds notebooks/07_stage2_models.ipynb. Run: python notebooks/build_stage2_notebook.py"""
import nbformat as nbf
from pathlib import Path
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# 07 · Stage 2 on IBM: what do the notes add?

Three models on the **same IBM invoices**, scored 10 days before the due date:

| Model | Inputs | Use |
|---|---|---|
| **Model A** | Amount, paperless, country, payment history (frozen at the invoice date) | Yardstick: no notes (D-071) |
| **Model B (Stage 2)** | Model A inputs + the note signals S1 to S7 | The app (D-064) |
| **Ceiling** | Model A inputs + the real Disputed flag | Evaluation only: perfect dispute knowledge (D-073) |

If B lands close to the ceiling, the note reading captures most of what a perfect dispute flag would give.

Training period only (invoices before July 1, 2013); the test set is kept for the Evaluator. Needs notebook 05 to have run first (it writes `data/generated/note_features.csv`).

**Caveat:** the notes are synthetic and the reader is the rules-based stand-in, so B's closeness to the ceiling is an upper bound. The Haiku reader on Bedrock is the real test."""),
code("""import sys; sys.path.insert(0, "..")
import json, joblib, os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import mlflow
from src.data.load import load_b, CUT_B, SHA_B
from src.model import train as T
from src.model import tracking

b = load_b("../data/raw/ibm_ar.csv")
nf = pd.read_csv("../data/generated/note_features.csv", dtype={"invoice_id": str})
d = T.ibm_frame(b, nf)
train = d[d["set"] == "train"]
INPUTS = T.ibm_inputs()
print(f"IBM training invoices: {len(train):,}, late rate {train['late'].mean():.3f}")"""),
md("## 1. Rolling validation (4 folds; the IBM training period is small)"),
code("""parts, lasts = [], []
for name, (num, cat) in INPUTS.items():
    kinds = ("baseline", "logistic", "xgboost") if name == "model_a" else ("logistic", "xgboost")
    r, last = T.rolling_validation(train, n_splits=4, kinds=kinds, numeric=num, categorical=cat, label=name)
    parts.append(r)
    lasts.append(last if not lasts else last[[c for c in last.columns if c.startswith(name + "_")]])
results = pd.concat(parts)
last_valid = pd.concat(lasts, axis=1)   # same rows in every run: the date-sorted last fold
summary = results.groupby(["inputs", "model"])[["auc", "pr_auc", "top20_capture"]].mean().round(3)
summary"""),
code("""results[results["model"] == "logistic"].pivot(index="fold", columns="inputs", values="auc").round(3)"""),
md("""**How to read it**
- Fold 1 trains on under 300 invoices, so folds 2 to 4 are the realistic ones.
- About 30% of IBM invoices are late, so working the top 20% can catch at most about two-thirds of them. Top-20% capture is lower here than for Stage 1 for that reason, not because the models are worse.
- On this small dataset, logistic regression matches or beats XGBoost, as it did for Stage 1."""),
code("""lr = results[results["model"] == "logistic"].groupby("inputs")["auc"].mean()
gain, room = lr["model_b"] - lr["model_a"], lr["ceiling"] - lr["model_a"]
print(f"Logistic regression, mean AUC: Model A {lr['model_a']:.3f} -> Model B {lr['model_b']:.3f} (ceiling {lr['ceiling']:.3f})")
print(f"The notes recover {gain / room:.0%} of the gain a perfect dispute flag would give")"""),
md("## 2. Chart"),
code("""sns.set_theme(style="white", font_scale=0.95)
COL = {"model_a": "#9aa3ad", "model_b": "#2a6fdb", "ceiling": "#1b2a4a"}
NAME = {"model_a": "Model A (no notes)", "model_b": "Model B (with notes)", "ceiling": "Ceiling (true dispute flag)"}
fig, ax = plt.subplots(1, 2, figsize=(14, 4.6), dpi=150)
s = results[results["model"] == "logistic"].groupby("inputs")[["auc", "pr_auc"]].mean().reindex(["model_a", "model_b", "ceiling"])
x = np.arange(2); w = 0.27
for i, m in enumerate(s.index):
    ax[0].bar(x + (i - 1) * w, s.loc[m].values, w, color=COL[m], label=NAME[m])
    for j, v in enumerate(s.loc[m].values):
        ax[0].text(x[j] + (i - 1) * w, v + 0.01, f"{v:.2f}", ha="center", fontsize=9)
ax[0].set_xticks(x); ax[0].set_xticklabels(["AUC", "PR-AUC"])
ax[0].set_title("1. Notes close most of the gap to the ceiling", loc="left", fontweight="bold")
ax[0].legend(frameon=False, loc="upper center", ncol=3, fontsize=9); ax[0].set_ylim(0, 1.15)
y = last_valid["late"].to_numpy()
for m in ["model_a", "model_b", "ceiling"]:
    order = np.argsort(-last_valid[f"{m}_logistic"].to_numpy(), kind="stable")
    ax[1].plot(np.arange(1, len(y) + 1) / len(y) * 100, np.cumsum(y[order]) / y.sum() * 100, color=COL[m], lw=2, label=NAME[m])
ax[1].plot([0, 100], [0, 100], ls=":", c="k", lw=1, label="Random")
ax[1].set_title("2. Late invoices caught vs invoices worked (fold 4)", loc="left", fontweight="bold")
ax[1].set_xlabel("Share of invoices worked, riskiest first (%)"); ax[1].set_ylabel("Share of late invoices caught (%)")
ax[1].legend(frameon=False, loc="lower right", fontsize=9)
fig.text(0.01, 0.005, "Logistic regression, IBM training period. Notes are synthetic, anchored to real dispute flags; read by the rules-based stand-in.", fontsize=9)
sns.despine(fig); fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig("../docs/img/stage2_notes_gain.png"); plt.show()"""),
md("## 3. Fairness by country code (D-072), Model B, last fold"),
code("""f = T.group_rates(last_valid, "model_b_logistic", "country_code")
f["check"] = np.where((f["false_alarm_ratio"] > 1.25) & (f["late_rate"] <= f.loc["ALL", "late_rate"]), "REVIEW", "ok")
f.round(3)"""),
md("## 4. Train final models, save, log to MLflow"),
code("""tracking.setup(root=".."); mlflow.set_experiment("late-payment-stage2-ibm")
known = T.known_by(train, CUT_B)
print(f"Usable training invoices (paid before Jul 1, 2013): {len(known):,} of {len(train):,}")
os.makedirs("../models", exist_ok=True)
runs = {}
for name, (num, cat) in INPUTS.items():
    for kind in ["logistic", "xgboost"]:
        model, _, extra = T.fit_predict(kind, known, known.head(1), num, cat)
        path = f"../models/{name}_{kind}.joblib"
        joblib.dump({"model": model, "numeric": num, "categorical": cat, **extra}, path)
        m = results[(results["inputs"] == name) & (results["model"] == kind)][["auc", "pr_auc", "top20_capture"]].mean()
        card = {"model": f"{name}_{kind}", "data_sha256": SHA_B, "rows": len(known), "inputs": num + cat,
                "use": {"model_a": "yardstick", "model_b": "app (Stage 2)", "ceiling": "evaluation only"}[name],
                "notes": "synthetic, rules-based reader", "validation": {k: round(float(v), 4) for k, v in m.items()}, "test_set": "not used"}
        json.dump(card, open(path.replace(".joblib", ".json"), "w"), indent=2)
        runs[f"{name}_{kind}"] = tracking.log_run(f"{name}_{kind}", {"rows": len(known), "inputs": len(num + cat)},
                                                  {f"cv_{k}": v for k, v in m.items()}, artifacts=[path], card=card)
pd.Series(runs, name="mlflow_run_id")"""),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
nbf.write(nb, Path(__file__).with_name("07_stage2_models.ipynb")); print("wrote")
