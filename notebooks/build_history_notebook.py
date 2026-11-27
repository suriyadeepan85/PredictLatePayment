"""Builds notebooks/02_history_profile.ipynb. Run: python notebooks/build_history_notebook.py"""
import nbformat as nbf
from pathlib import Path
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# 02 · Customer history at scoring time

Purpose: decide the history groups for gate G1 (open item Q-010): **no history**, **limited**, **enough**.

For every invoice, count how many earlier invoices the same customer had **already paid before this invoice's posting date**. That's the history the model can legally use when it scores the invoice (data contract, section 5). Nothing from the invoice's own outcome or the future is used.

Same cleaning as the data contract: exact duplicates, non-RV rows and invoices due before their invoice date are removed."""),
code("""DATA_PATH = "../data/raw/customer_invoices.csv"
GRACE_DAYS = 3                 # calendar days (D-056)
CUTOFF_DATE = "2019-10-01"     # train / test split (D-013)
BINS = [-1, 0, 4, 9, 10**9]    # 0 | 1-4 | 5-9 | 10+ prior paid invoices
LABELS = ["0", "1-4", "5-9", "10+"]"""),
md("## 1. Load and clean (contract rules Q1, Q3, Q6)"),
code("""import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def yyyymmdd(s):
    return pd.to_datetime(s.astype("Int64").astype(str), format="%Y%m%d", errors="coerce")

raw = pd.read_csv(DATA_PATH, dtype={"cust_number": str})
df = raw.drop_duplicates()
df = df[df["document type"] == "RV"].copy()
df["invoice_date"] = pd.to_datetime(df["posting_date"])
df["due_date"] = yyyymmdd(df["due_in_date"])
df["clear_dt"] = pd.to_datetime(df["clear_date"])
df = df[~(df["due_date"] < df["invoice_date"])].copy()
print("Clean invoices:", len(df))"""),
md("""## 2. Count eligible prior paid invoices

For each customer, sort their payment dates. For each invoice, count the payments strictly before its posting date. This is the core of every history feature (past late rate, average days late), so it's worth getting exactly right."""),
code("""paid_dates = {c: np.sort(g["clear_dt"].values)
              for c, g in df[df["isOpen"] == 0].groupby("cust_number")}

def prior_paid(cust, as_of):
    dates = paid_dates.get(cust)
    return 0 if dates is None else int(np.searchsorted(dates, as_of, side="left"))

df["prior_paid"] = [prior_paid(c, t) for c, t in zip(df["cust_number"], df["invoice_date"].values)]
df["set"] = np.where(df["isOpen"] == 1, "replay",
             np.where(df["invoice_date"] < pd.Timestamp(CUTOFF_DATE), "train", "test"))
df["history_group"] = pd.cut(df["prior_paid"], BINS, labels=LABELS)
df["prior_paid"].describe()"""),
md("## 3. How much history does each set have?"),
code("""counts = pd.crosstab(df["history_group"], df["set"])[["train", "test", "replay"]]
shares = (counts / counts.sum()).round(3)
display(counts)
shares"""),
md("## 4. Does history relate to lateness?"),
code("""paid = df[df["isOpen"] == 0].copy()
paid["late"] = (paid["clear_dt"] - paid["due_date"]).dt.days > GRACE_DAYS
by_group = paid.groupby("history_group", observed=True)["late"].agg(invoices="size", late_rate="mean").round(3)
by_group"""),
md("## 5. Charts"),
code("""sns.set_theme(style="white", font_scale=0.95)
BLUE, GREY, RED = "#2a6fdb", "#9aa3ad", "#d1495b"
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), dpi=150)

plot = (shares * 100).reset_index().melt(id_vars="history_group", var_name="set", value_name="pct")
sns.barplot(data=plot, x="history_group", y="pct", hue="set",
            palette={"train": BLUE, "test": RED, "replay": GREY}, saturation=1, ax=ax[0])
ax[0].set_title("1. Almost every test and replay invoice has 10+ prior payments", loc="left", fontweight="bold")
ax[0].set_xlabel("Prior paid invoices at scoring time"); ax[0].set_ylabel("Share of invoices in the set (%)")
ax[0].legend(frameon=False, title=None)

lr = by_group.reset_index()
sns.barplot(data=lr, x="history_group", y=lr["late_rate"] * 100, color=BLUE, saturation=1, ax=ax[1])
for i, (v, n) in enumerate(zip(lr["late_rate"] * 100, lr["invoices"])):
    ax[1].text(i, v + 0.6, f"{v:.0f}%\\n(n={n:,})", ha="center", fontsize=9)
ax[1].set_title("2. Less history, more lateness", loc="left", fontweight="bold")
ax[1].set_xlabel("Prior paid invoices at scoring time"); ax[1].set_ylabel(f"Late rate, {GRACE_DAYS}-day grace (%)")
ax[1].set_ylim(0, lr["late_rate"].max() * 130)

sns.despine(fig); fig.tight_layout()
fig.savefig("../docs/img/history_profile.png")
plt.show()"""),
md("""## Decision for G1 (Q-010)

Proposed groups: **none = 0**, **limited = 1 to 4**, **enough = 5 or more** prior paid invoices.

Why: the late rate steps down from 0 to 1-4 to 5+, and each group has enough paid invoices (thousands) to report model performance separately, as the contract requires."""),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
nbf.write(nb, Path(__file__).with_name("02_history_profile.ipynb")); print("wrote")
