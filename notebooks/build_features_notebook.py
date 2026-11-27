"""Builds notebooks/04_features.ipynb. Run: python notebooks/build_features_notebook.py"""
import nbformat as nbf
from pathlib import Path
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# 04 · Features (gate G2)

The features are the facts the model looks at for each invoice. This notebook builds them, puts a number on each, and checks they use nothing from the future.

Three groups (`specs/features.md`):
1. **About the invoice:** amount, payment terms, business unit (or country), payment-term code.
2. **About the customer's history,** counting only invoices **paid before** the invoice date: six measures.
3. **From the notes** (Stage 2 only): the seven signals in `specs/note_features.md`. Built in notebook 05.

All the logic lives in `src/`, so this notebook, the app and the tests share the same code. **Only the training set is used to look at relationships here.** The test set is kept for the Evaluator."""),
code("""import sys; sys.path.insert(0, "..")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_auc_score
from src.data.load import load_a, load_b, GRACE_DAYS
from src.features.history import build_history, FEATURES

PATH_A = "../data/raw/customer_invoices.csv"
PATH_B = "../data/raw/ibm_ar.csv\""""),
md("## 1. Load the clean data (contract v1.4)"),
code("""a = load_a(PATH_A)
print("Quality log:", a.attrs["quality_log"])
print(a["set"].value_counts().to_dict())
a.groupby("set")["late"].agg(["size", "mean"]).round(3)"""),
md("""## 2. Invoice features

| Feature | How it's calculated |
|---|---|
| `log_amount` | log(1 + open amount). Amounts are very skewed, so the log keeps a few huge invoices from dominating |
| `terms_days` | Due date minus baseline date |
| `payment_terms` | Payment-term code; codes with fewer than 20 invoices become OTHER (rule Q12) |
| `business_code` | Business unit; rare ones become OTHER. Also the fairness group |"""),
code("""a["log_amount"] = np.log1p(a["amount"])
train = a["set"] == "train"
a.loc[train, ["log_amount", "terms_days"]].describe().round(2)"""),
md("""## 3. The six history measures

For each invoice, take the same customer's invoices **paid before its invoice date**, then:

| # | Feature | Number | If there is no history |
|---|---|---|---|
| 1 | `hist_n_paid` | Count of those invoices | 0 |
| 2 | `hist_late_share` | Late ones ÷ count (3 of 10 → 0.3) | Missing, not 0 |
| 3 | `hist_avg_days_late` | Mean days paid after the due date, each capped at ±90 | Missing |
| 4 | `hist_days_since_last_late` | Days from their last late payment to this invoice date | Missing (also when never late) |
| 5 | `hist_std_days_late` | Spread of days late: steady payers low, erratic ones high | Missing if fewer than 2 |
| 6 | `hist_group` | none (0), limited (1-4), enough (5+) (D-061) | none |
| + | `hist_last_late` | Was their most recent paid invoice late? Also the "late last time" baseline rule | Missing |

Missing is kept as missing. XGBoost learns a separate path for "no history", which is different from "a perfect record"."""),
code("""h = build_history(a, asof_col="invoice_date")
a = a.join(h)
coverage = a.groupby("set")[FEATURES].apply(lambda g: g.notna().mean()).T.round(3)
coverage.columns.name = "share with a value"
coverage"""),
md("""**What to notice:** about 1 in 10 training invoices has no history, but only about 1 in 100 test and replay invoices. The model must still handle "no history", but it will matter much less in the test period."""),
md("""## 4. How each measure relates to lateness (training set only)"""),
code("""t = a[train].copy()
def bucket(s, bins, labels, missing="No history"):
    c = pd.cut(s, bins, labels=labels)
    return c.cat.add_categories([missing]).fillna(missing).astype(str)

t["b1"] = bucket(t["hist_n_paid"], [-1, 0, 4, 9, 24, np.inf], ["0", "1-4", "5-9", "10-24", "25+"])
t["b2"] = bucket(t["hist_late_share"], [-0.01, 0, 0.2, 0.5, 1], ["0", "0-20%", "20-50%", "50%+"])
t["b3"] = bucket(t["hist_avg_days_late"], [-91, -5, 0, 3, 10, 91], ["early 5+", "early 0-5", "0-3 late", "3-10 late", "10+ late"])
t["b4"] = bucket(t["hist_days_since_last_late"], [-1, 30, 90, 365, np.inf], ["<30", "30-90", "90-365", "365+"], missing="Never late / none")
q = t["hist_std_days_late"].quantile([0, 1/3, 2/3, 1]).to_numpy(copy=True); q[0] -= 1e-9
t["b5"] = bucket(t["hist_std_days_late"], q, ["steady", "middle", "erratic"], missing="Fewer than 2")
t["b6"] = t["hist_group"]

sns.set_theme(style="white", font_scale=0.9)
BLUE, GREY = "#2a6fdb", "#9aa3ad"
titles = ["1. Invoices paid so far", "2. Share paid late", "3. Average days late",
          "4. Days since last late payment", "5. Consistency (spread of days late)", "6. History group"]
orders = [["0", "1-4", "5-9", "10-24", "25+"],
          ["No history", "0", "0-20%", "20-50%", "50%+"],
          ["No history", "early 5+", "early 0-5", "0-3 late", "3-10 late", "10+ late"],
          ["Never late / none", "<30", "30-90", "90-365", "365+"],
          ["Fewer than 2", "steady", "middle", "erratic"],
          ["none", "limited", "enough"]]
fig, axes = plt.subplots(2, 3, figsize=(16, 8), dpi=150)
overall = t["late"].mean() * 100
for ax, col, title, order in zip(axes.flat, ["b1", "b2", "b3", "b4", "b5", "b6"], titles, orders):
    g = t.groupby(col)["late"].agg(["mean", "size"]).reindex(order).dropna()
    colors = [GREY if k in ("No history", "Never late / none", "Fewer than 2") else BLUE for k in g.index]
    ax.bar(range(len(g)), g["mean"] * 100, color=colors)
    for i, (m, n) in enumerate(zip(g["mean"] * 100, g["size"])):
        ax.text(i, m + 1, f"{m:.0f}%\\nn={int(n):,}", ha="center", fontsize=8)
    ax.axhline(overall, ls="--", c="k", lw=1)
    ax.set_xticks(range(len(g))); ax.set_xticklabels(g.index, fontsize=8)
    ax.set_title(title, loc="left", fontweight="bold"); ax.set_ylim(0, max(g["mean"] * 100) * 1.3)
    ax.set_ylabel(f"Late rate, {GRACE_DAYS}-day grace (%)")
fig.text(0.01, 0.005, f"Training invoices only (n={len(t):,}). Dashed line: overall late rate {overall:.1f}%. Grey: no value for this measure.", fontsize=9)
sns.despine(fig); fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig("../docs/img/features_history.png")
plt.show()"""),
md("""## 5. One number per feature: how well it ranks late invoices on its own

AUC on the training set: 0.5 means no better than a coin toss, 1.0 means perfect ranking. Missing values are filled here only so each feature can be scored alone (−1, or 10,000 days for \"never late\"); the model itself keeps them missing."""),
code("""cands = ["hist_late_share", "hist_avg_days_late", "hist_last_late", "hist_std_days_late",
         "hist_days_since_last_late", "hist_n_paid", "log_amount", "terms_days"]
rows = []
for c in cands:
    x = t[c].fillna(10_000 if c == "hist_days_since_last_late" else -1)
    auc = roc_auc_score(t["late"], x)
    rows.append({"feature": c, "auc_alone": round(max(auc, 1 - auc), 3),
                 "direction": "higher = later" if auc >= 0.5 else "higher = earlier"})
pd.DataFrame(rows).sort_values("auc_alone", ascending=False).reset_index(drop=True)"""),
md("""**What to notice:** the history measures carry most of the signal on their own. "Late last time" alone is the baseline the model has to beat (D-021)."""),
md("## 6. Leakage checks"),
code("""# 1. No outcome column is a feature
outcomes = {"clear_date", "days_late", "late"}
inputs_stage1 = ["log_amount", "terms_days", "payment_terms", "business_code"] + FEATURES
assert not outcomes & set(inputs_stage1)

# 2. Brute-force check on a random sample: history uses only invoices paid before the invoice date
rng = np.random.default_rng(1)
for i in rng.choice(a.index, 200, replace=False):
    r = a.loc[i]
    prior = a[(a["customer_id"] == r["customer_id"]) & (a["clear_date"] < r["invoice_date"])]
    assert r["hist_n_paid"] == len(prior), i

# 3. An invoice never counts towards its own history
own_paid_before_itself = (a["clear_date"] < a["invoice_date"]).sum()
print("Invoices paid before their own invoice date:", own_paid_before_itself, "(must be 0)")
print("All leakage checks passed")"""),
md("""## 7. IBM (Dataset B): inputs for Model A, Model B and the ceiling

History is **frozen at the invoice date** (D-064), so the only new information at the Stage 2 date comes from the notes. All IBM invoices have 30-day terms, so `terms_days` is dropped there (constant)."""),
code("""b = load_b(PATH_B)
b["log_amount"] = np.log1p(b["amount"])
b = b.join(build_history(b, asof_col="invoice_date"))
tb = b[b["set"] == "train"]
print(b["set"].value_counts().to_dict(), "| terms:", b["terms_days"].unique())
tb.groupby("hist_group")["late"].agg(invoices="size", late_rate="mean").round(3)"""),
code("""inputs = pd.DataFrame([
    ["Stage 1", "A", "log_amount, terms_days, payment_terms, business_code, 7 history features", "App"],
    ["Model A", "B", "log_amount, paperless, country_code, 7 history features", "Yardstick"],
    ["Model B (Stage 2)", "B", "Model A inputs + note signals S1 to S7", "App"],
    ["Ceiling", "B", "Model A inputs + disputed", "Evaluation only"],
], columns=["model", "data", "inputs", "use"])
inputs"""),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
nbf.write(nb, Path(__file__).with_name("04_features.ipynb")); print("wrote")
