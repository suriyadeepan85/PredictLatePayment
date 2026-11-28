"""Customer payment-history features as of a cut-off date (data contract section 7, specs/features.md).

Only the same customer's invoices PAID BEFORE the cut-off count. The current invoice
never counts towards its own history (its clear date is on or after its invoice date).
"""
import numpy as np
import pandas as pd

DAYS_LATE_CAP = 90          # section 7 rule 7
GROUP_BINS = [-1, 0, 4, np.inf]
GROUP_LABELS = ["none", "limited", "enough"]   # D-061

FEATURES = ["hist_n_paid", "hist_late_share", "hist_avg_days_late",
            "hist_days_since_last_late", "hist_std_days_late", "hist_group",
            "hist_last_late"]


def build_history(df, asof_col="invoice_date"):
    """Return a DataFrame indexed like df with the history features.

    df needs: customer_id, clear_date (NaT if unpaid), days_late, late, and asof_col.
    """
    out = pd.DataFrame(index=df.index, columns=FEATURES, dtype=float)
    paid = df[df["clear_date"].notna()]
    for cust, rows in df.groupby("customer_id", sort=False):
        # Deterministic order for ties: clear date, then invoice date, then original row order.
        p = paid[paid["customer_id"] == cust].sort_values(["clear_date", "invoice_date"], kind="mergesort")
        asof = rows[asof_col].values
        if p.empty:
            out.loc[rows.index, "hist_n_paid"] = 0
            continue
        clear = p["clear_date"].values
        dl = p["days_late"].clip(-DAYS_LATE_CAP, DAYS_LATE_CAP).to_numpy(float)
        lt = p["late"].to_numpy(float)
        cnt = np.arange(1, len(p) + 1)
        cum_late, cum_dl, cum_sq = np.cumsum(lt), np.cumsum(dl), np.cumsum(dl ** 2)
        late_dates = np.where(lt == 1, clear.astype("datetime64[D]").astype("int64"), -10**9)
        last_late = np.maximum.accumulate(late_dates)
        k = np.searchsorted(clear, asof, side="left")     # invoices with clear_date < asof
        has = k > 0
        i = np.maximum(k - 1, 0)
        n = np.where(has, cnt[i], 0)
        mean = np.where(has, cum_dl[i] / np.maximum(n, 1), np.nan)
        var = np.where(n >= 2, (cum_sq[i] - n * mean ** 2) / np.maximum(n - 1, 1), np.nan)
        asof_days = asof.astype("datetime64[D]").astype("int64")
        since = np.where(has & (last_late[i] > -10**9), asof_days - last_late[i], np.nan)
        block = pd.DataFrame({
            "hist_n_paid": n,
            "hist_late_share": np.where(has, cum_late[i] / np.maximum(n, 1), np.nan),
            "hist_avg_days_late": mean,
            "hist_days_since_last_late": since,
            "hist_std_days_late": np.sqrt(np.clip(var, 0, None)),
            "hist_last_late": np.where(has, lt[i], np.nan),
        }, index=rows.index)
        out.loc[rows.index, block.columns] = block.values
    out["hist_n_paid"] = out["hist_n_paid"].astype(int)
    out["hist_group"] = pd.cut(out["hist_n_paid"], GROUP_BINS, labels=GROUP_LABELS).astype(str)
    return out
