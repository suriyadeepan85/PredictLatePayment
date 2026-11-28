import numpy as np
import pandas as pd
from src.features.history import build_history


def _toy():
    d = pd.to_datetime
    return pd.DataFrame({
        "customer_id": ["c1"] * 4 + ["c2"],
        "invoice_date": d(["2020-01-01", "2020-01-10", "2020-02-01", "2020-03-01", "2020-01-05"]),
        "clear_date": d(["2020-01-20", "2020-02-15", "2020-02-01", None, "2020-01-06"]),
        "days_late": [10.0, 200.0, -5.0, np.nan, 0.0],
        "late": [1.0, 1.0, 0.0, np.nan, 0.0],
    })


def test_only_invoices_paid_before_cutoff():
    h = build_history(_toy())
    assert h.loc[0, "hist_n_paid"] == 0          # nothing paid before Jan 1
    assert h.loc[1, "hist_n_paid"] == 0          # first invoice paid Jan 20, after Jan 10
    assert h.loc[2, "hist_n_paid"] == 1          # paid Feb 1 itself: not counted (strictly before)
    assert h.loc[3, "hist_n_paid"] == 3


def test_values_and_cap():
    h = build_history(_toy())
    r = h.loc[3]
    assert r["hist_late_share"] == 2 / 3
    assert r["hist_avg_days_late"] == (10 + 90 - 5) / 3      # 200 capped at 90
    assert r["hist_last_late"] == 1.0                         # last paid (Feb 15) was late
    assert r["hist_days_since_last_late"] == 15               # Feb 15 to Mar 1
    assert r["hist_group"] == "limited"


def test_no_history_is_missing_not_zero():
    h = build_history(_toy())
    assert np.isnan(h.loc[0, "hist_late_share"]) and h.loc[0, "hist_group"] == "none"


def test_matches_brute_force_on_real_shape():
    rng = np.random.default_rng(0)
    n = 300
    inv = pd.Timestamp("2020-01-01") + pd.to_timedelta(rng.integers(0, 200, n), "D")
    clear = inv + pd.to_timedelta(rng.integers(0, 60, n), "D")
    df = pd.DataFrame({"customer_id": rng.choice(list("abcde"), n), "invoice_date": inv,
                       "clear_date": clear})
    df["days_late"] = rng.integers(-10, 40, n).astype(float)
    df["late"] = (df["days_late"] > 3).astype(float)
    h = build_history(df)
    for i in rng.choice(n, 40, replace=False):
        prior = df[(df.customer_id == df.customer_id[i]) & (df.clear_date < df.invoice_date[i])]
        assert h.loc[i, "hist_n_paid"] == len(prior)
        if len(prior):
            assert np.isclose(h.loc[i, "hist_late_share"], prior.late.mean())


def test_brute_force_all_measures():
    rng = np.random.default_rng(3)
    n = 250
    inv = pd.Timestamp("2020-01-01") + pd.to_timedelta(rng.integers(0, 150, n), "D")
    df = pd.DataFrame({"customer_id": rng.choice(list("abc"), n), "invoice_date": inv,
                       "clear_date": inv + pd.to_timedelta(rng.integers(0, 60, n), "D")})
    df["days_late"] = rng.integers(-120, 150, n).astype(float)
    df["late"] = (df["days_late"] > 3).astype(float)
    h = build_history(df)
    for i in rng.choice(n, 40, replace=False):
        p = df[(df.customer_id == df.customer_id[i]) & (df.clear_date < df.invoice_date[i])].sort_values(["clear_date", "invoice_date"], kind="mergesort")
        if len(p) == 0:
            continue
        dl = p.days_late.clip(-90, 90)
        assert np.isclose(h.loc[i, "hist_avg_days_late"], dl.mean())
        if len(p) >= 2:
            assert np.isclose(h.loc[i, "hist_std_days_late"], dl.std(ddof=1))
        lates = p[p.late == 1]
        exp = (df.invoice_date[i] - lates.clear_date.max()).days if len(lates) else np.nan
        assert (np.isnan(exp) and np.isnan(h.loc[i, "hist_days_since_last_late"])) or h.loc[i, "hist_days_since_last_late"] == exp
        assert h.loc[i, "hist_last_late"] == p.late.iloc[-1]


def test_top_share_capture_ties_are_order_free():
    from src.model.train import top_share_capture
    y = np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0]); s = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    assert np.isclose(top_share_capture(y, s), top_share_capture(y[::-1], s[::-1]))
    assert np.isclose(top_share_capture(y, s), 0.5)        # 2 of 4 tied slots taken, half the lates expected
