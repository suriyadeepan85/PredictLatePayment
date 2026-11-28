"""Stage 1 training and validation (specs/agents/ml_engineer.md, specs/features.md).

Only the training period is used here. The test set is scored once, by the Evaluator.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.features.history import build_history

SEED = 42
NUMERIC_STAGE1 = ["log_amount", "terms_days", "hist_n_paid", "hist_late_share", "hist_avg_days_late",
                  "hist_days_since_last_late", "hist_std_days_late", "hist_last_late"]
CATEGORICAL_STAGE1 = ["payment_terms", "business_code", "hist_group"]
# Chosen on folds 1-4 of the rolling validation (Nov 27): depth 3 to 6 all within 0.01 AUC; this one was best.
XGB_PARAMS = dict(n_estimators=400, learning_rate=0.05, max_depth=5, subsample=0.8,
                  colsample_bytree=0.8, min_child_weight=20, reg_lambda=5, tree_method="hist",
                  random_state=SEED, n_jobs=4, eval_metric="aucpr")


def stage1_frame(a):
    """Add Stage 1 features (specs/features.md section 3) to the output of load_a."""
    df = a.copy()
    df["log_amount"] = np.log1p(df["amount"])
    return df.join(build_history(df, asof_col="invoice_date"))


def known_by(df, cutoff):
    """Rows whose outcome was known before the cut-off (paid before it). Used for training only."""
    return df[df["clear_date"] < cutoff]


def top_share_capture(y, score, share=0.2):
    """Share of all late invoices that fall in the top `share` of scores. Ties at the cut-off are
    shared in proportion (the expected value under random tie-breaking), so row order never matters."""
    y = np.asarray(y, float); s = np.asarray(score, float)
    k = share * len(y)
    thr = np.sort(s)[::-1][int(np.ceil(k)) - 1]
    above = s > thr; tied = s == thr
    take = (k - above.sum()) / max(tied.sum(), 1)
    return (y[above].sum() + take * y[tied].sum()) / max(y.sum(), 1)


def metrics(y, score):
    y = np.asarray(y, float); score = np.asarray(score, float)
    return {"auc": roc_auc_score(y, score), "pr_auc": average_precision_score(y, score),
            "top20_capture": top_share_capture(y, score),
            "brier": float(np.mean((score - y) ** 2)), "mean_pred": float(score.mean()), "actual_rate": float(y.mean())}


def baseline_score(df, fill):
    """'Late last time' rule. Customers with no history get the training late rate."""
    return df["hist_last_late"].fillna(fill).to_numpy()


def make_lr(numeric=NUMERIC_STAGE1, categorical=CATEGORICAL_STAGE1):
    pre = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)),
                          ("scale", StandardScaler())]), numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20), categorical),
    ])
    # No class weighting: weighting inflated probabilities about 2x (review R-03), and cash at risk needs real probabilities.
    return Pipeline([("pre", pre), ("model", LogisticRegression(max_iter=2000, C=1.0))])


def xgb_matrix(df, numeric=NUMERIC_STAGE1, categorical=CATEGORICAL_STAGE1, categories=None):
    X = df[numeric + categorical].copy()
    for c in categorical:
        cats = categories[c] if categories else sorted(X[c].astype(str).unique())
        X[c] = pd.Categorical(X[c].astype(str), categories=cats)
    return X


def make_xgb(y):
    # No scale_pos_weight, for calibrated probabilities (review R-03).
    return XGBClassifier(**XGB_PARAMS, enable_categorical=True)


def fit_predict(kind, tr, va, numeric=NUMERIC_STAGE1, categorical=CATEGORICAL_STAGE1):
    """Fit one model on tr and score va. Returns (model, scores, extra)."""
    y = tr["late"].to_numpy(int)
    if kind == "baseline":
        fill = y.mean()
        return None, baseline_score(va, fill), {"fill": fill}
    if kind == "logistic":
        m = make_lr(numeric, categorical).fit(tr[numeric + categorical], y)
        return m, m.predict_proba(va[numeric + categorical])[:, 1], {}
    if kind == "xgboost":
        cats = {c: sorted(tr[c].astype(str).unique()) for c in categorical}
        m = make_xgb(y).fit(xgb_matrix(tr, numeric, categorical, cats), y)
        return m, m.predict_proba(xgb_matrix(va, numeric, categorical, cats))[:, 1], {"categories": cats}
    raise ValueError(kind)


def rolling_validation(train_df, n_splits=5, kinds=("baseline", "logistic", "xgboost"),
                       numeric=NUMERIC_STAGE1, categorical=CATEGORICAL_STAGE1, label=None):
    """TimeSeriesSplit inside the training period. Each fold trains only on invoices paid
    before the fold's first validation invoice date."""
    d = train_df.sort_values("invoice_date").reset_index(drop=True)
    rows, preds = [], []
    for k, (tr_i, va_i) in enumerate(TimeSeriesSplit(n_splits=n_splits).split(d), start=1):
        va = d.iloc[va_i]
        cut = va["invoice_date"].min()
        tr = known_by(d.iloc[tr_i], cut)
        for kind in kinds:
            _, s, _ = fit_predict(kind, tr, va, numeric, categorical)
            rows.append({"fold": k, "model": kind, "inputs": label, "train_n": len(tr), "valid_n": len(va),
                         "valid_from": cut.date(), **metrics(va["late"], s)})
            if k == n_splits:
                preds.append(pd.Series(s, index=va.index, name=f"{label}_{kind}" if label else kind))
    last_valid = d.iloc[va_i].join(pd.concat(preds, axis=1))
    return pd.DataFrame(rows), last_valid


def group_rates(df, score_col, group_col, flag_share=0.2):
    """Flag the top `flag_share` by score; report rates by group (D-022)."""
    f = df[score_col].rank(method="first", ascending=False) <= flag_share * len(df)   # exactly the top share
    y = df["late"] == 1
    def agg(g):
        fy, yy = f.loc[g.index], y.loc[g.index]
        return pd.Series({"invoices": len(g), "late_rate": yy.mean(), "flag_rate": fy.mean(),
                          "false_alarm_rate": (fy & ~yy).sum() / max((~yy).sum(), 1),
                          "miss_rate": (~fy & yy).sum() / max(yy.sum(), 1)})
    overall = agg(df).rename("ALL")
    out = df.groupby(group_col).apply(agg)
    out.loc["ALL"] = overall
    out["false_alarm_ratio"] = out["false_alarm_rate"] / overall["false_alarm_rate"]
    return out


# ---- Dataset B (IBM): Model A, Model B (Stage 2), ceiling (D-064, D-071, D-073; specs/features.md) ----
HIST_NUMERIC = ["hist_n_paid", "hist_late_share", "hist_avg_days_late", "hist_days_since_last_late",
                "hist_std_days_late", "hist_last_late"]
IBM_INPUTS = {
    "model_a": (["log_amount", "paperless"] + HIST_NUMERIC, ["country_code", "hist_group"]),
}


def ibm_inputs():
    from src.features.notes import SIGNAL_NUMERIC, SIGNAL_CATEGORICAL
    num_a, cat_a = IBM_INPUTS["model_a"]
    return {"model_a": (num_a, cat_a),
            "model_b": (num_a + SIGNAL_NUMERIC, cat_a + SIGNAL_CATEGORICAL),
            "ceiling": (num_a + ["disputed"], cat_a)}


def ibm_frame(b, note_features):
    """IBM invoices with Stage 1-style inputs (history frozen at the invoice date) plus note signals."""
    df = b.copy()
    df["log_amount"] = np.log1p(df["amount"])
    df = df.join(build_history(df, asof_col="invoice_date"))
    return df.merge(note_features, on="invoice_id", how="left")
