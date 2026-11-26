"""Builds notebooks/01_profile_data.ipynb. Run: python notebooks/build_profile_notebook.py"""
import nbformat as nbf
from pathlib import Path

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells = [
    md("""# 01 · Profile the Customer Invoices data

Purpose: understand the 50,000-row dataset before writing the data contract (gate G1).

Every number here should match what Claude reported. If yours differ, that's worth a conversation.

**Where to run it:** SageMaker Studio (JupyterLab, `ml.t3.medium`, stop it afterwards) or Jupyter on your laptop.

**Data:** download `dataset.csv` from Kaggle (`pradumn203/payment-date-prediction-for-invoices-dataset`) and set `DATA_PATH` below. In SageMaker, upload it into the space or read it from your own private S3 bucket. Never commit it to git.

Expected file checksum (SHA-256): `3409441a8ecc48438a0fd42421ce3230d95305f7afcefb732bf232a948b6cf88`"""),
    md("## Settings"),
    code("""DATA_PATH = "../data/raw/customer_invoices.csv"   # or "s3://your-bucket/raw/dataset.csv" (needs s3fs)
GRACE_DAYS = 3        # days after the due date before an invoice counts as late (decided: 3 days)
CUTOFF_DATE = "2019-10-01"  # paid invoices before this train the model; after it, test"""),
    md("## 1. Load and check the file"),
    code("""import hashlib
import pandas as pd
import matplotlib.pyplot as plt

if not DATA_PATH.startswith("s3://"):
    print("SHA-256:", hashlib.sha256(open(DATA_PATH, "rb").read()).hexdigest())

raw = pd.read_csv(DATA_PATH, dtype={"cust_number": str})
print("Rows, columns:", raw.shape)
raw.drop(columns=["name_customer"]).head(3).T  # names hidden on purpose"""),
    md("## 2. Columns: types, missing values, distinct values"),
    code("""summary = pd.DataFrame({
    "dtype": raw.dtypes.astype(str),
    "missing": raw.isna().sum(),
    "distinct": raw.nunique(dropna=True),
})
summary"""),
    md("""**What to notice:** `area_business` is always empty and `posting_id` is always 1, so both are dropped. `clear_date` is missing for exactly the open invoices."""),
    md("## 3. Duplicates"),
    code("""print("Exact duplicate rows:", raw.duplicated().sum())
df = raw.drop_duplicates().copy()
print("After removing them:", len(df))
print("Duplicate doc_id left:", df["doc_id"].duplicated().sum())"""),
    md("## 4. Parse the dates"),
    code("""def yyyymmdd(s):
    return pd.to_datetime(s.astype("Int64").astype(str), format="%Y%m%d", errors="coerce")

df["invoice_date"] = pd.to_datetime(df["posting_date"])
df["due_date"] = yyyymmdd(df["due_in_date"])
df["baseline_date"] = yyyymmdd(df["baseline_create_date"])
df["clear_dt"] = pd.to_datetime(df["clear_date"])
df["terms_days"] = (df["due_date"] - df["baseline_date"]).dt.days

print("Posting date equals document_create_date.1:",
      (df["invoice_date"] == yyyymmdd(df["document_create_date.1"])).mean().round(3))
df["terms_days"].describe()"""),
    md("## 5. Paid versus open"),
    code("""paid = df[df["isOpen"] == 0].copy()
open_ = df[df["isOpen"] == 1].copy()
print(f"Paid: {len(paid):,}  posted {paid.invoice_date.min().date()} to {paid.invoice_date.max().date()}")
print(f"Open: {len(open_):,}  posted {open_.invoice_date.min().date()} to {open_.invoice_date.max().date()}")
print("Open invoices with a clear date:", open_["clear_dt"].notna().sum())
print("Open invoices whose customer has paid history:", open_["cust_number"].isin(paid["cust_number"]).mean().round(3))"""),
    md("""**What to notice:** every open invoice comes after the paid ones, so the open invoices are a natural replay set for the demo. They have no outcome, so they can never measure accuracy."""),
    md("## 6. The label and the grace period"),
    code("""paid["days_late"] = (paid["clear_dt"] - paid["due_date"]).dt.days
print(paid["days_late"].describe(percentiles=[.05, .25, .5, .75, .95]))

grace = pd.DataFrame({"grace_days": [0, 3, 5, 7, 15]})
grace["late_share"] = grace["grace_days"].apply(lambda g: (paid["days_late"] > g).mean().round(3))
grace["late_count"] = grace["grace_days"].apply(lambda g: int((paid["days_late"] > g).sum()))
grace"""),
    code("""paid["days_late"].clip(-30, 60).plot.hist(bins=90, figsize=(8, 3), title="Days paid after the due date (clipped to -30..60)")
plt.axvline(GRACE_DAYS, linestyle="--")
plt.show()"""),
    md("""**What to notice:** half of the invoices that are late at 0 days are only 1 or 2 days late. That's usually payment-run timing, not something worth an analyst's call. That's why the grace period is a business decision."""),
    code("""paid["late"] = paid["days_late"] > GRACE_DAYS
print(f"Late rate with {GRACE_DAYS}-day grace: {paid['late'].mean():.3f}")"""),
    md("## 7. Customers"),
    code("""per_cust = df.groupby("cust_number").size()
print("Customers:", len(per_cust))
print("Invoices per customer:", per_cust.describe().round(1).to_dict())
print("Customers with fewer than 5 invoices:", int((per_cust < 5).sum()))
print("Most name spellings for one customer number:", df.groupby("cust_number")["name_customer"].nunique().max())"""),
    md("""## 8. Names must be masked

The customer name column includes real-looking retailer names. They must never appear on screen or in the deck. Masking uses the customer number, which is the real key."""),
    code("""top_share = df["cust_number"].value_counts(normalize=True).head(5)
print("Share of rows from the 5 largest customer numbers:")
print(top_share.round(3))

codes = {c: f"Customer {i:04d}" for i, c in enumerate(sorted(df["cust_number"].unique()), start=1)}
df["customer_label"] = df["cust_number"].map(codes)
df[["cust_number", "customer_label"]].drop_duplicates().head()"""),
    md("## 9. Groups for the fairness check"),
    code("""fair = paid.groupby(["business_code", "invoice_currency"]).agg(
    invoices=("late", "size"), late_rate=("late", "mean")).round(3)
fair"""),
    code("""paid.groupby("invoice_currency")["late"].agg(["size", "mean"]).round(3)"""),
    md("""**What to notice:** CAD invoices are paid late far more often than USD ones. That's a real difference in the data, so the fairness check tests whether the model's flags track each group's actual late rate, not whether every group is flagged equally."""),
    md("## 10. Amounts and payment terms"),
    code("""print(df["total_open_amount"].describe(percentiles=[.01, .5, .99]).round(0))
print("\\nPayment term codes:", df["cust_payment_terms"].nunique())
df["cust_payment_terms"].value_counts().head(10)"""),
    md("## 11. Time split preview"),
    code("""cut = pd.Timestamp(CUTOFF_DATE)
train = paid[paid["invoice_date"] < cut]
test = paid[paid["invoice_date"] >= cut]
pd.DataFrame({
    "invoices": [len(train), len(test), len(open_)],
    "late_rate": [train["late"].mean().round(3), test["late"].mean().round(3), None],
}, index=["train (paid, before cutoff)", "test (paid, after cutoff)", "replay (open)"])"""),
    md("""## 12. The four charts behind the data contract

One figure, four questions: how the data splits in time, what "late" looks like, what the grace period does, and which groups differ. It uses seaborn on top of matplotlib, and saves a PNG for the deck."""),
    code("""import seaborn as sns
import matplotlib.dates as mdates
from pathlib import Path

sns.set_theme(style="white", context="notebook", font_scale=0.95)
BLUE, GREY, RED = "#2a6fdb", "#9aa3ad", "#d1495b"
fig, ax = plt.subplots(2, 2, figsize=(12, 8.2), dpi=150)

# 1. Paid vs open over time, with the train/test cutoff
monthly = (df.assign(month=df["invoice_date"].dt.to_period("M").dt.to_timestamp(),
                     status=df["isOpen"].map({0: "Paid (train and test)", 1: "Open (demo replay)"}))
             .groupby(["month", "status"]).size().unstack(fill_value=0))
a = ax[0, 0]
a.bar(monthly.index, monthly["Paid (train and test)"], width=25, color=BLUE, label="Paid (train and test)")
a.bar(monthly.index, monthly["Open (demo replay)"], width=25, bottom=monthly["Paid (train and test)"], color=GREY, label="Open (demo replay)")
a.axvline(pd.Timestamp(CUTOFF_DATE), ls="--", c="k", lw=1)
a.text(pd.Timestamp(CUTOFF_DATE) + pd.Timedelta(days=7), monthly.sum(axis=1).max() * 0.95, "train | test cutoff", fontsize=9)
a.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
a.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
a.set_title("1. Open invoices all come after the paid ones", loc="left", fontweight="bold")
a.set_ylabel("Invoices per month"); a.set_xlabel(""); a.legend(frameon=False, fontsize=9, loc="upper left")

# 2. Days paid after the due date, with the grace line
a = ax[0, 1]
sns.histplot(paid["days_late"].clip(-20, 40), bins=range(-20, 42), color=BLUE, edgecolor=None, alpha=1, ax=a)
a.axvline(GRACE_DAYS + 0.5, c=RED, lw=1.5)
a.text(GRACE_DAYS + 1.5, a.get_ylim()[1] * 0.85, f"{GRACE_DAYS}-day grace:\\nlate = right of line", color=RED, fontsize=9)
a.set_title("2. Most invoices are paid within days of the due date", loc="left", fontweight="bold")
a.set_xlabel("Days paid after due date (end bars hold everything beyond -20 / 40)"); a.set_ylabel("Paid invoices")

# 3. Share counted late at each grace period
a = ax[1, 0]
grid = pd.DataFrame({"grace_days": [0, 1, 2, 3, 5, 7, 10, 15]})
grid["late_pct"] = grid["grace_days"].apply(lambda g: (paid["days_late"] > g).mean() * 100)
colors = [RED if g == GRACE_DAYS else BLUE for g in grid["grace_days"]]
sns.barplot(data=grid, x="grace_days", y="late_pct", hue="grace_days", palette=colors, legend=False, saturation=1, ax=a)
for i, v in enumerate(grid["late_pct"]):
    a.text(i, v + 0.8, f"{v:.0f}%", ha="center", fontsize=9)
a.set_title("3. The grace period decides what counts as late", loc="left", fontweight="bold")
a.set_xlabel("Grace period (days)"); a.set_ylabel("Paid invoices counted late (%)")

# 4. Late rate by business unit and currency (groups with 50+ invoices)
a = ax[1, 1]
grp = (paid.groupby(["business_code", "invoice_currency"])["late"].agg(n="size", rate="mean").reset_index()
           .query("n >= 50").sort_values("rate", ascending=False))
grp["label"] = grp["business_code"] + " / " + grp["invoice_currency"] + "\\n(n=" + grp["n"].map("{:,}".format) + ")"
grp["pct"] = grp["rate"] * 100
sns.barplot(data=grp, y="label", x="pct", hue="label",
            palette=[RED if c == "CAD" else BLUE for c in grp["invoice_currency"]], legend=False, saturation=1, ax=a)
for i, v in enumerate(grp["pct"]):
    a.text(v + 0.4, i, f"{v:.0f}%", va="center", fontsize=9)
overall = paid["late"].mean() * 100
a.axvline(overall, ls="--", c="k", lw=1)
a.text(overall + 0.4, len(grp) - 0.55, f"overall {overall:.0f}%", fontsize=9)
a.set_title("4. Late rates differ by business unit and currency", loc="left", fontweight="bold")
a.set_xlabel(f"Late rate with {GRACE_DAYS}-day grace (%)"); a.set_ylabel("")

sns.despine(fig)
fig.tight_layout()
out = Path("../docs/img"); out.mkdir(parents=True, exist_ok=True)
fig.savefig(out / f"data_profile_grace{GRACE_DAYS}.png")
plt.show()"""),
    md("""## Your checkpoint

Compare with what Claude reported (grace 3 days):

| Check | Expected |
|---|---|
| Rows after removing duplicates | 48,839 |
| Paid / open | 39,158 / 9,681 |
| Late rate at 0 / 3 / 5 / 7 days | 0.419 / 0.148 / 0.093 / 0.067 |
| Customers | 1,425 |
| CAD vs USD late rate (0 days) | about 0.75 vs 0.39 |

Then decide at gate G1: the grace period, and whether the data contract stands."""),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
out = Path(__file__).with_name("01_profile_data.ipynb")
nbf.write(nb, out)
print("wrote", out)
