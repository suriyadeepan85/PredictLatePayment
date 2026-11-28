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
    """Share of all late invoices that fall in the top `share` of scores."""
    y = np.asarray(y); order = np.argsort(-np.asarray(score), kind="stable")
    k = int(np.ceil(share * len(y)))
    return y[order[:k]].sum() / max(y.sum(), 1)


def metrics(y, score):
    return {"auc": roc_auc_score(y, score), "pr_auc": average_precision_score(y, score),
            "top20_capture": top_share_capture(y, score)}


def baseline_score(df, fill):
    """'Late last time' rule. Customers with no history get the training late rate."""
    return df["hist_last_late"].fillna(fill).to_numpy()


def make_lr(numeric=NUMERIC_STAGE1, categorical=CATEGORICAL_STAGE1):
    pre = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)),
                          ("scale", StandardScaler())]), numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20), categorical),
    ])
    return Pipeline([("pre", pre), ("model", LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0))])


def xgb_matrix(df, numeric=NUMERIC_STAGE1, categorical=CATEGORICAL_STAGE1, categories=None):
    X = df[numeric + categorical].copy()
    for c in categorical:
        cats = categories[c] if categories else sorted(X[c].astype(str).unique())
        X[c] = pd.Categorical(X[c].astype(str), categories=cats)
    return X


def make_xgb(y):
    pos = float(np.sum(y)); neg = float(len(y) - pos)
    return XGBClassifier(**XGB_PARAMS, scale_pos_weight=neg / max(pos, 1), enable_categorical=True)


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


def rolling_validation(train_df, n_splits=5, kinds=("baseline", "logistic", "xgboost")):
    """TimeSeriesSplit inside the training period. Each fold trains only on invoices paid
    before the fold's first validation invoice date."""
    d = train_df.sort_values("invoice_date").reset_index(drop=True)
    rows, preds = [], []
    for k, (tr_i, va_i) in enumerate(TimeSeriesSplit(n_splits=n_splits).split(d), start=1):
        va = d.iloc[va_i]
        cut = va["invoice_date"].min()
        tr = known_by(d.iloc[tr_i], cut)
        for kind in kinds:
            _, s, _ = fit_predict(kind, tr, va)
            rows.append({"fold": k, "model": kind, "train_n": len(tr), "valid_n": len(va),
                         "valid_from": cut.date(), **metrics(va["late"], s)})
            if k == n_splits:
                preds.append(pd.Series(s, index=va.index, name=kind))
    last_valid = d.iloc[va_i].join(pd.concat(preds, axis=1))
    return pd.DataFrame(rows), last_valid


def group_rates(df, score_col, group_col, flag_share=0.2):
    """Flag the top `flag_share` by score; report rates by group (D-022)."""
    thr = df[score_col].quantile(1 - flag_share)
    f = df[score_col] >= thr
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
