"""Builds notebooks/03_ibm_split.ipynb. Run: python notebooks/build_ibm_split_notebook.py"""
import nbformat as nbf
from pathlib import Path
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# 03 · IBM data: time-based train/test split (Stage 2)

Purpose: set and check the train/test split for the Stage 2 model, which is trained and measured on the IBM data (D-059).

**Why split by time, not randomly:** the model learns from past invoices and scores future ones. A random split mixes the two, so the model could train on a customer's later invoices and be tested on earlier ones, and the score would look better than it really is. Time is not a model input; it only decides which invoices are for training and which for testing.

Decided split (owner, Nov 26): train on invoices dated before **July 1, 2013**, test on the last six months.

Data: IBM `WA_Fn-UseC_-Accounts-Receivable.csv` in `data/raw/ibm_ar.csv` (never committed). SHA-256 `f5d488eaa4c1cc843b478b6f1068c553c5394aab4b64d587e4b9ad811d845c19`."""),
code("""DATA_PATH = "../data/raw/ibm_ar.csv"
GRACE_DAYS = 3              # calendar days (D-056)
CUTOFF_DATE = "2013-07-01"  # train before, test from
N_FOLDS = 5                 # rolling checks with scikit-learn TimeSeriesSplit"""),
md("## 1. Load, check, label"),
code("""import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from sklearn.model_selection import TimeSeriesSplit

print("SHA-256:", hashlib.sha256(open(DATA_PATH, "rb").read()).hexdigest())
df = pd.read_csv(DATA_PATH, dtype={"invoiceNumber": str, "customerID": str, "countryCode": str})
for c in ["InvoiceDate", "DueDate", "SettledDate", "PaperlessDate"]:
    df[c] = pd.to_datetime(df[c], format="%m/%d/%Y")

checks = {
    "rows": len(df),
    "duplicate invoiceNumber": int(df["invoiceNumber"].duplicated().sum()),
    "missing values": int(df.isna().sum().sum()),
    "settled before invoice": int((df["SettledDate"] < df["InvoiceDate"]).sum()),
    "amount <= 0": int((df["InvoiceAmount"] <= 0).sum()),
}
print(checks)

df["days_late"] = (df["SettledDate"] - df["DueDate"]).dt.days
df["late"] = df["days_late"] > GRACE_DAYS
df["stage2_scoring_date"] = df["DueDate"] - pd.Timedelta(days=10)
print(f"Late rate at {GRACE_DAYS} days: {df['late'].mean():.3f}")
print("Payment terms (days):", (df["DueDate"] - df["InvoiceDate"]).dt.days.value_counts().to_dict())"""),
md("## 2. The decided split"),
code("""cut = pd.Timestamp(CUTOFF_DATE)
df["set"] = np.where(df["InvoiceDate"] < cut, "train", "test")
summary = df.groupby("set").agg(
    invoices=("late", "size"), late=("late", "sum"), late_rate=("late", "mean"),
    disputed=("Disputed", lambda s: (s == "Yes").sum()),
    first=("InvoiceDate", "min"), last=("InvoiceDate", "max")).loc[["train", "test"]]
summary["late_rate"] = summary["late_rate"].round(3)
summary"""),
md("""**What to check:** the test set needs enough late invoices to measure recall and AUC with some stability. About 100 or more is a reasonable floor."""),
md("""## 3. Rolling check with scikit-learn `TimeSeriesSplit`

One cut can be lucky. `TimeSeriesSplit` makes several cuts in time order: each fold trains on everything before a point and tests on the block right after it. If the late rate and the dispute pattern hold across folds, the patterns are stable over time. The same folds can later be used to check the models."""),
code("""ordered = df.sort_values("InvoiceDate").reset_index(drop=True)
tss = TimeSeriesSplit(n_splits=N_FOLDS)
rows = []
for k, (tr, te) in enumerate(tss.split(ordered), start=1):
    a, b = ordered.iloc[tr], ordered.iloc[te]
    rows.append({
        "fold": k,
        "train_until": a["InvoiceDate"].max().date(),
        "test_from": b["InvoiceDate"].min().date(),
        "test_to": b["InvoiceDate"].max().date(),
        "train_n": len(a), "test_n": len(b),
        "test_late_rate": round(b["late"].mean(), 3),
        "late_if_disputed": round(b.loc[b["Disputed"] == "Yes", "late"].mean(), 3),
        "late_if_not": round(b.loc[b["Disputed"] == "No", "late"].mean(), 3),
    })
folds = pd.DataFrame(rows)
folds"""),
md("""**What to notice:** in every fold, disputed invoices are late far more often than undisputed ones. That's the real pattern the Stage 2 notes are built on (dispute notes come from the real Disputed flag; the model never sees the flag itself)."""),
md("## 4. Fairness groups: country code"),
code("""country = df.groupby("countryCode")["late"].agg(invoices="size", late_rate="mean").round(3)
country"""),
md("## 5. Charts"),
code("""sns.set_theme(style="white", font_scale=0.95)
BLUE, GREY, RED = "#2a6fdb", "#9aa3ad", "#d1495b"
fig, ax = plt.subplots(1, 3, figsize=(16, 4.4), dpi=150)

m = df.assign(month=df["InvoiceDate"].dt.to_period("M").dt.to_timestamp()).groupby(["month", "set"]).size().unstack(fill_value=0)
ax[0].bar(m.index, m.get("train", 0), width=25, color=BLUE, label="Train")
ax[0].bar(m.index, m.get("test", 0), width=25, color=RED, label="Test")
ax[0].axvline(cut, ls="--", c="k", lw=1)
ax[0].set_title("1. Split by invoice date at July 1, 2013", loc="left", fontweight="bold")
ax[0].set_ylabel("Invoices per month"); ax[0].legend(frameon=False, loc="upper left", ncol=2); ax[0].set_ylim(0, 150)
ax[0].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
ax[0].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

f = folds.melt(id_vars="fold", value_vars=["late_if_disputed", "late_if_not"], var_name="group", value_name="rate")
f["group"] = f["group"].map({"late_if_disputed": "Disputed", "late_if_not": "Not disputed"})
sns.barplot(data=f, x="fold", y=f["rate"] * 100, hue="group", palette=[RED, BLUE], saturation=1, ax=ax[1])
ax[1].set_title("2. Disputes predict lateness in every fold", loc="left", fontweight="bold")
ax[1].set_xlabel("TimeSeriesSplit fold (later folds = later invoices)"); ax[1].set_ylabel(f"Late rate, {GRACE_DAYS}-day grace (%)")
ax[1].legend(frameon=False, title=None, loc="upper right", bbox_to_anchor=(1, 1.0), ncol=2)
ax[1].set_ylim(0, 80)

c = country.reset_index().sort_values("late_rate", ascending=False)
sns.barplot(data=c, y="countryCode", x=c["late_rate"] * 100, color=BLUE, saturation=1, ax=ax[2])
for i, (v, n) in enumerate(zip(c["late_rate"] * 100, c["invoices"])):
    ax[2].text(v + 0.5, i, f"{v:.0f}% (n={n})", va="center", fontsize=9)
ax[2].axvline(df["late"].mean() * 100, ls="--", c="k", lw=1)
ax[2].set_title("3. Late rate by country code", loc="left", fontweight="bold")
ax[2].set_xlabel(f"Late rate, {GRACE_DAYS}-day grace (%)"); ax[2].set_ylabel("Country code")
ax[2].set_xlim(0, c["late_rate"].max() * 130)

sns.despine(fig); fig.tight_layout()
fig.savefig("../docs/img/ibm_split.png")
plt.show()"""),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
nbf.write(nb, Path(__file__).with_name("03_ibm_split.ipynb")); print("wrote")
