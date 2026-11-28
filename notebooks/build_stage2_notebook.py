"""Builds notebooks/07_stage2_models.ipynb. Run: python notebooks/build_stage2_notebook.py"""
import nbformat as nbf
from pathlib import Path
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# 07 · Stage 2 on IBM: what could the notes add?

Three models on the **same IBM invoices**, scored 10 days before the due date, **only for invoices still unpaid on that day** (D-103):

| Model | Inputs | Use |
|---|---|---|
| **Model A** | Amount, paperless, country, payment history (frozen at the invoice date) | Yardstick: no notes (D-071) |
| **Model B (Stage 2)** | Model A inputs + note signals S1 to S7 | The app (D-064) |
| **Ceiling** | Model A inputs + the real Disputed flag | Evaluation only (D-073) |

**Why a curve, not one number (D-104).** The notes are synthetic, so how much they help depends on an assumption: what share of disputes is already written down by the Stage 2 day. Section 3 varies that share from 0% to 100% and shows Model B's result at each. The app uses 70% (A-008). Even so, the reader here is the rules-based stand-in. The Claude Haiku reader on Bedrock is the real test of note reading.

Training period only (before July 1, 2013); the test set is kept for the Evaluator. Needs the raw IBM file; notebook 05 is not required."""),
code("""import sys, warnings; sys.path.insert(0, ".."); warnings.filterwarnings("ignore", message="Using the public demo salt")
import json, joblib, os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import mlflow
from src.data.load import load_b, CUT_B, SHA_B
from src.data.notes_generate import generate_notes
from src.data.masking import load_rules, mask_notes
from src.features.notes import extract, aggregate
from src.model import train as T
from src.model import tracking

b = load_b("../data/raw/ibm_ar.csv")
CFG = load_rules("../config/masking.yaml")
INPUTS = T.ibm_inputs()

def build(noted_share, seed=42):
    raw, contacts = generate_notes(b, seed=seed, late_noted_share=1 - noted_share)
    masked = mask_notes(raw, contacts, CFG)
    feats = aggregate(masked, extract(masked), b)
    d = T.stage2_population(T.ibm_frame(b, feats))
    return d[d["set"] == "train"]

train = build(0.7)
print(f"Stage 2 training population (unpaid on the Stage 2 date): {len(train):,} invoices, late rate {train['late'].mean():.3f}")"""),
md("## 1. Rolling validation at the default assumption (70% of disputes noted by the Stage 2 day)"),
code("""parts, lasts = [], []
for name, (num, cat) in INPUTS.items():
    kinds = ("baseline", "logistic", "xgboost") if name == "model_a" else ("logistic", "xgboost")
    r, last = T.rolling_validation(train, n_splits=4, kinds=kinds, numeric=num, categorical=cat, label=name)
    parts.append(r)
    lasts.append(last if not lasts else last[[c for c in last.columns if c.startswith(name + "_")]])
results = pd.concat(parts)
last_valid = pd.concat(lasts, axis=1)
results.groupby(["inputs", "model"])[["auc", "pr_auc", "top20_capture", "mean_pred", "actual_rate"]].mean().round(3)"""),
code("""lr = results[results["model"] == "logistic"].groupby("inputs")["auc"].mean()
print(f"Logistic regression, mean AUC: Model A {lr['model_a']:.3f}, Model B {lr['model_b']:.3f}, ceiling {lr['ceiling']:.3f}")
print(f"At 70% noted, the notes recover {(lr['model_b'] - lr['model_a']) / (lr['ceiling'] - lr['model_a']):.0%} of the ceiling's gain")"""),
md("## 2. Fairness by country code, Model B, last fold (D-102)"),
code("""f = T.group_rates(last_valid, "model_b_logistic", "country_code")
f["flag_vs_own_late"] = f["flag_rate"] / f["late_rate"]
f["check"] = np.where((f["false_alarm_ratio"] > 1.25) & (f["flag_vs_own_late"] > 1.25), "REVIEW", "ok")
f.round(3)"""),
md("""## 3. The what-if curve: gain from notes against the share of disputes noted by the Stage 2 day

For each share, the notes are regenerated with the same seed, masked, read, and Model B is re-validated. Model A and the ceiling don't use notes, so they stay flat."""),
code("""SEEDS = [42, 7, 123]     # averaged over three note generations: the dataset is small, so one seed is noisy
rows = []
for share in [0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 1.0]:
    for seed in SEEDS:
        tr = build(share, seed=seed)
        num, cat = INPUTS["model_b"]
        r, _ = T.rolling_validation(tr, n_splits=4, kinds=("logistic",), numeric=num, categorical=cat, label="model_b")
        rows.append({"noted_share": share, "seed": seed, "model_b_auc": r["auc"].mean(), "model_b_pr_auc": r["pr_auc"].mean()})
runs_curve = pd.DataFrame(rows)
curve = runs_curve.groupby("noted_share")[["model_b_auc", "model_b_pr_auc"]].mean().reset_index()
curve["auc_min"] = runs_curve.groupby("noted_share")["model_b_auc"].min().values
curve["auc_max"] = runs_curve.groupby("noted_share")["model_b_auc"].max().values
curve["share_of_ceiling_gain"] = (curve["model_b_auc"] - lr["model_a"]) / (lr["ceiling"] - lr["model_a"])
curve.round(3)"""),
md("## 4. Chart"),
code("""sns.set_theme(style="white", font_scale=0.95)
fig, ax = plt.subplots(1, 2, figsize=(14, 4.6), dpi=150)
x = curve["noted_share"] * 100
ax[0].fill_between(x, curve["auc_min"], curve["auc_max"], color="#2a6fdb", alpha=0.15, lw=0, label="Range over 3 note generations")
ax[0].plot(x, curve["model_b_auc"], marker="o", color="#2a6fdb", lw=2.5, label="Model B (with notes), average")
ax[0].axhline(lr["model_a"], color="#9aa3ad", lw=2, ls="--", label=f"Model A, no notes ({lr['model_a']:.2f})")
ax[0].axhline(lr["ceiling"], color="#1b2a4a", lw=2, ls="--", label=f"Ceiling, true dispute flag ({lr['ceiling']:.2f})")
ax[0].set_ylim(0.70, 0.845)
ax[0].axvline(70, color="k", lw=1, ls=":"); ax[0].text(71, 0.703, "app default (70%)", fontsize=8)
ax[0].set_xlabel("Share of disputes written down by the Stage 2 day (%)"); ax[0].set_ylabel("AUC (rolling validation)")
ax[0].set_title("1. What notes add depends on how early disputes are logged", loc="left", fontweight="bold")
ax[0].legend(frameon=False, loc="upper left", fontsize=8.5)
y = last_valid["late"].to_numpy()
COL = {"model_a": "#9aa3ad", "model_b": "#2a6fdb", "ceiling": "#1b2a4a"}
NAME = {"model_a": "Model A (no notes)", "model_b": "Model B (notes, 70% noted)", "ceiling": "Ceiling (true dispute flag)"}
for m in ["model_a", "model_b", "ceiling"]:
    order = np.argsort(-last_valid[f"{m}_logistic"].to_numpy(), kind="stable")
    ax[1].plot(np.arange(1, len(y) + 1) / len(y) * 100, np.cumsum(y[order]) / y.sum() * 100, color=COL[m], lw=2, label=NAME[m])
ax[1].plot([0, 100], [0, 100], ls=":", c="k", lw=1, label="Random")
ax[1].set_title("2. Late invoices caught vs invoices worked (fold 4)", loc="left", fontweight="bold")
ax[1].set_xlabel("Share of invoices worked, riskiest first (%)"); ax[1].set_ylabel("Share of late invoices caught (%)")
ax[1].legend(frameon=False, loc="lower right", fontsize=9)
fig.text(0.01, 0.005, "Logistic regression; IBM invoices still unpaid on the Stage 2 date, training period. Notes are synthetic, read by the rules-based stand-in.", fontsize=9)
sns.despine(fig); fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig("../docs/img/stage2_notes_curve.png"); plt.show()"""),
md("## 5. Train final models at the default assumption, save, log to MLflow"),
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
                "population": "invoices unpaid on the Stage 2 date (D-103)",
                "use": {"model_a": "yardstick", "model_b": "app (Stage 2)", "ceiling": "evaluation only"}[name],
                "notes": "synthetic, 70% of disputes noted by the Stage 2 day, rules-based reader",
                "validation": {k: round(float(v), 4) for k, v in m.items()}, "test_set": "not used"}
        json.dump(card, open(path.replace(".joblib", ".json"), "w"), indent=2)
        runs[f"{name}_{kind}"] = tracking.log_run(f"{name}_{kind}", {"rows": len(known), "noted_share": 0.7},
                                                  {f"cv_{k}": v for k, v in m.items()}, artifacts=[path], card=card)
pd.Series(runs, name="mlflow_run_id")"""),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
nbf.write(nb, Path(__file__).with_name("07_stage2_models.ipynb")); print("wrote")
